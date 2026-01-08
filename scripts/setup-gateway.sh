#!/bin/bash
################################################################################
# WaybackProxy Gateway Setup Script
# Configures Raspberry Pi as a transparent proxy gateway
#
# This script:
# - Sets up DHCP server on ethernet interface
# - Configures NAT and IP forwarding
# - Redirects HTTP traffic to WaybackProxy transparently
# - Configures DNS to minimize HTTPS redirects
#
# Usage: sudo ./setup-gateway.sh [eth_interface] [wifi_interface]
# Example: sudo ./setup-gateway.sh eth0 wlan0
################################################################################

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root"
    exit 1
fi

# Configuration
ETH_INTERFACE="${1:-eth0}"
WIFI_INTERFACE="${2:-wlan0}"
GATEWAY_IP="10.88.88.1"
DHCP_RANGE_START="10.88.88.100"
DHCP_RANGE_END="10.88.88.200"
WAYBACK_PROXY_PORT="8888"

log_info "Gateway Configuration:"
log_info "  Ethernet Interface: $ETH_INTERFACE"
log_info "  WiFi Interface: $WIFI_INTERFACE"
log_info "  Gateway IP: $GATEWAY_IP"
log_info "  DHCP Range: $DHCP_RANGE_START - $DHCP_RANGE_END"
log_info "  WaybackProxy Port: $WAYBACK_PROXY_PORT"

# Verify interfaces exist
if ! ip link show "$ETH_INTERFACE" &>/dev/null; then
    log_error "Ethernet interface $ETH_INTERFACE not found"
    log_info "Available interfaces:"
    ip link show | grep -E '^[0-9]+:' | awk '{print "  - " $2}' | sed 's/:$//'
    exit 1
fi

if ! ip link show "$WIFI_INTERFACE" &>/dev/null; then
    log_warn "WiFi interface $WIFI_INTERFACE not found, will use first available interface for internet"
    # Find first interface that's not loopback or ethernet
    WIFI_INTERFACE=$(ip link show | grep -E '^[0-9]+:' | grep -v "$ETH_INTERFACE" | grep -v 'lo:' | head -1 | awk '{print $2}' | sed 's/:$//')
    if [ -z "$WIFI_INTERFACE" ]; then
        log_error "No suitable internet interface found"
        exit 1
    fi
    log_info "Using interface: $WIFI_INTERFACE"
fi

################################################################################
# Install required packages
################################################################################

log_info "Installing required packages..."
apt-get update -qq
apt-get install -y -qq dnsmasq iptables iptables-persistent

# Stop services while we configure
systemctl stop dnsmasq 2>/dev/null || true

################################################################################
# Configure static IP on ethernet interface
################################################################################

log_info "Configuring static IP on $ETH_INTERFACE..."

# Detect network manager type (NetworkManager vs dhcpcd)
if systemctl is-active --quiet NetworkManager; then
    log_info "Using NetworkManager for network configuration"
    NETWORK_MANAGER="networkmanager"

    # Create NetworkManager connection for static IP
    nmcli con delete "wayback-gateway" 2>/dev/null || true
    nmcli con add type ethernet con-name "wayback-gateway" ifname "$ETH_INTERFACE" \
        ipv4.method manual \
        ipv4.addresses "$GATEWAY_IP/24" \
        ipv4.dns "8.8.8.8,8.8.4.4" \
        connection.autoconnect yes

    nmcli con up "wayback-gateway"
    sleep 2

elif systemctl is-active --quiet dhcpcd; then
    log_info "Using dhcpcd for network configuration"
    NETWORK_MANAGER="dhcpcd"

    # Append to main dhcpcd.conf with markers for easy removal
    if ! grep -q "# WaybackProxy Gateway Start" /etc/dhcpcd.conf 2>/dev/null; then
        cat >> /etc/dhcpcd.conf <<EOF

# WaybackProxy Gateway Start
interface $ETH_INTERFACE
static ip_address=$GATEWAY_IP/24
static domain_name_servers=8.8.8.8 8.8.4.4
nohook wpa_supplicant
# WaybackProxy Gateway End
EOF
    fi

    systemctl restart dhcpcd
    sleep 3
else
    log_warn "No known network manager detected, setting IP manually"
    NETWORK_MANAGER="manual"

    # Set IP directly
    ip addr flush dev "$ETH_INTERFACE"
    ip addr add "$GATEWAY_IP/24" dev "$ETH_INTERFACE"
    ip link set "$ETH_INTERFACE" up
fi

# Save network manager type for disable script
echo "$NETWORK_MANAGER" > /etc/waybackproxy-gateway.conf

# Verify IP is set
sleep 2
if ! ip addr show "$ETH_INTERFACE" | grep -q "$GATEWAY_IP"; then
    log_error "Failed to set static IP on $ETH_INTERFACE"
    log_error "You may need to configure the static IP manually"
    exit 1
fi

log_info "✓ Static IP configured: $GATEWAY_IP"

################################################################################
# Configure dnsmasq (DHCP + DNS)
################################################################################

log_info "Configuring dnsmasq..."

# Backup original config
if [ -f /etc/dnsmasq.conf ] && [ ! -f /etc/dnsmasq.conf.backup ]; then
    cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
fi

# Create dnsmasq configuration
cat > /etc/dnsmasq.conf <<EOF
# WaybackProxy Gateway - dnsmasq configuration
# DHCP and DNS server for ethernet clients

# Listen only on ethernet interface
interface=$ETH_INTERFACE
bind-dynamic

# DHCP range
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,24h

# Gateway and DNS server (this Pi)
dhcp-option=3,$GATEWAY_IP
dhcp-option=6,$GATEWAY_IP

# Domain
domain=wayback.local

# Upstream DNS servers (Google DNS)
server=8.8.8.8
server=8.8.4.4

# Don't read /etc/resolv.conf or /etc/hosts for upstream servers
no-resolv
no-poll

# Log queries for debugging (comment out in production)
log-queries
log-dhcp

# Cache size
cache-size=1000

# Don't forward plain names (without a dot)
domain-needed

# Never forward addresses in the non-routed address spaces
bogus-priv

# Optional: Force some sites to HTTP to avoid HTTPS redirects
# Uncomment and add domains as needed
# address=/example.com/$GATEWAY_IP
EOF

log_info "✓ dnsmasq configured"

# Create systemd override to ensure dnsmasq waits for network
log_info "Configuring dnsmasq systemd service..."
mkdir -p /etc/systemd/system/dnsmasq.service.d
cat > /etc/systemd/system/dnsmasq.service.d/wait-for-network.conf <<EOF
[Unit]
After=network-online.target
Wants=network-online.target

[Service]
Restart=on-failure
RestartSec=5
EOF

systemctl daemon-reload

log_info "✓ dnsmasq service configured"

################################################################################
# Enable IP forwarding
################################################################################

log_info "Enabling IP forwarding..."

# Enable IPv4 forwarding using sysctl.d (modern approach)
cat > /etc/sysctl.d/99-wayback-gateway.conf <<EOF
# WaybackProxy Gateway - Enable IP forwarding
net.ipv4.ip_forward=1
EOF

# Also update /etc/sysctl.conf if it exists (legacy systems)
if [ -f /etc/sysctl.conf ]; then
    sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf 2>/dev/null || true
    sed -i 's/net.ipv4.ip_forward=0/net.ipv4.ip_forward=1/' /etc/sysctl.conf 2>/dev/null || true

    # Add if not exists
    if ! grep -q "^net.ipv4.ip_forward=1" /etc/sysctl.conf; then
        echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    fi
fi

# Apply immediately
sysctl -w net.ipv4.ip_forward=1

log_info "✓ IP forwarding enabled"

################################################################################
# Configure iptables for NAT and transparent proxy
################################################################################

log_info "Configuring iptables rules..."

# Flush existing rules
iptables -F
iptables -t nat -F
iptables -t mangle -F
iptables -X

# Default policies
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# NAT - Allow ethernet clients to access internet through WiFi
iptables -t nat -A POSTROUTING -o "$WIFI_INTERFACE" -j MASQUERADE

# Forward traffic between interfaces
iptables -A FORWARD -i "$ETH_INTERFACE" -o "$WIFI_INTERFACE" -j ACCEPT
iptables -A FORWARD -i "$WIFI_INTERFACE" -o "$ETH_INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT

# Transparent HTTP proxy redirection
# Redirect all HTTP traffic (port 80) from ethernet clients to WaybackProxy
iptables -t nat -A PREROUTING -i "$ETH_INTERFACE" -p tcp --dport 80 -j REDIRECT --to-port "$WAYBACK_PROXY_PORT"

# Allow local connections to WaybackProxy
iptables -A INPUT -i "$ETH_INTERFACE" -p tcp --dport "$WAYBACK_PROXY_PORT" -j ACCEPT

# Allow DNS queries to dnsmasq
iptables -A INPUT -i "$ETH_INTERFACE" -p udp --dport 53 -j ACCEPT
iptables -A INPUT -i "$ETH_INTERFACE" -p tcp --dport 53 -j ACCEPT

# Allow DHCP
iptables -A INPUT -i "$ETH_INTERFACE" -p udp --dport 67:68 -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Save iptables rules
log_info "Saving iptables rules..."
netfilter-persistent save

log_info "✓ iptables configured and saved"

################################################################################
# Start services
################################################################################

log_info "Starting services..."

# Enable and start dnsmasq
systemctl enable dnsmasq
systemctl restart dnsmasq

# Wait for dnsmasq to start
sleep 2

# Check if dnsmasq is running
if systemctl is-active --quiet dnsmasq; then
    log_info "✓ dnsmasq is running"
else
    log_error "dnsmasq failed to start"
    journalctl -u dnsmasq -n 20 --no-pager
    exit 1
fi

################################################################################
# Verify WaybackProxy is running
################################################################################

log_info "Verifying WaybackProxy service..."

if systemctl is-active --quiet waybackproxy; then
    log_info "✓ WaybackProxy is running"
else
    log_warn "WaybackProxy service is not running"
    log_info "Starting WaybackProxy..."
    systemctl start waybackproxy
    sleep 2
    if systemctl is-active --quiet waybackproxy; then
        log_info "✓ WaybackProxy started"
    else
        log_error "Failed to start WaybackProxy"
        journalctl -u waybackproxy -n 20 --no-pager
        exit 1
    fi
fi

################################################################################
# Display configuration summary
################################################################################

echo ""
log_info "=========================================="
log_info "Gateway setup complete!"
log_info "=========================================="
echo ""
log_info "Configuration:"
log_info "  Gateway IP: $GATEWAY_IP"
log_info "  DHCP Range: $DHCP_RANGE_START - $DHCP_RANGE_END"
log_info "  Ethernet Interface: $ETH_INTERFACE"
log_info "  Internet Interface: $WIFI_INTERFACE"
log_info "  WaybackProxy Port: $WAYBACK_PROXY_PORT"
echo ""
log_info "Next steps:"
log_info "  1. Connect a computer to the $ETH_INTERFACE port"
log_info "  2. The computer should automatically get an IP via DHCP"
log_info "  3. All HTTP traffic will be transparently proxied through WaybackProxy"
log_info "  4. Browse to any HTTP website to see archived content"
echo ""
log_info "Troubleshooting:"
log_info "  - Check dnsmasq: journalctl -u dnsmasq -f"
log_info "  - Check WaybackProxy: journalctl -u waybackproxy -f"
log_info "  - View DHCP leases: cat /var/lib/misc/dnsmasq.leases"
log_info "  - Test from client: ping $GATEWAY_IP"
echo ""
log_info "To disable gateway mode, run: sudo ./disable-gateway.sh"
echo ""
