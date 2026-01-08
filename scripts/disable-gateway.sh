#!/bin/bash
################################################################################
# WaybackProxy Gateway Disable Script
# Removes gateway configuration and restores normal operation
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root"
    exit 1
fi

log_info "Disabling WaybackProxy gateway mode..."

# Stop dnsmasq
log_info "Stopping dnsmasq..."
systemctl stop dnsmasq 2>/dev/null || true
systemctl disable dnsmasq 2>/dev/null || true

# Restore original dnsmasq config
if [ -f /etc/dnsmasq.conf.backup ]; then
    mv /etc/dnsmasq.conf.backup /etc/dnsmasq.conf
    log_info "✓ Restored original dnsmasq configuration"
fi

# Remove systemd override
if [ -d /etc/systemd/system/dnsmasq.service.d ]; then
    rm -rf /etc/systemd/system/dnsmasq.service.d
    systemctl daemon-reload
    log_info "✓ Removed dnsmasq systemd overrides"
fi

# Detect which network manager was used
NETWORK_MANAGER=""
if [ -f /etc/waybackproxy-gateway.conf ]; then
    NETWORK_MANAGER=$(cat /etc/waybackproxy-gateway.conf)
    rm /etc/waybackproxy-gateway.conf
fi

# Remove network configuration based on manager type
case "$NETWORK_MANAGER" in
    networkmanager)
        log_info "Removing NetworkManager configuration..."
        nmcli con delete "wayback-gateway" 2>/dev/null || true
        log_info "✓ Removed NetworkManager gateway connection"
        ;;
    dhcpcd)
        log_info "Removing dhcpcd configuration..."
        # Remove gateway config block from dhcpcd.conf
        if [ -f /etc/dhcpcd.conf ]; then
            sed -i '/# WaybackProxy Gateway Start/,/# WaybackProxy Gateway End/d' /etc/dhcpcd.conf
            log_info "✓ Removed static IP from dhcpcd.conf"
        fi
        systemctl restart dhcpcd 2>/dev/null || true
        ;;
    manual|*)
        log_info "Network was configured manually, no cleanup needed"
        ;;
esac

# Flush iptables rules
log_info "Flushing iptables rules..."
iptables -F
iptables -t nat -F
iptables -t mangle -F
iptables -X

# Reset default policies
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# Save cleared rules
netfilter-persistent save 2>/dev/null || true

log_info "✓ iptables rules cleared"

# Remove IP forwarding configuration
if [ -f /etc/sysctl.d/99-wayback-gateway.conf ]; then
    rm /etc/sysctl.d/99-wayback-gateway.conf
    log_info "✓ Removed IP forwarding configuration"
fi

# Optionally disable IP forwarding (commented out to preserve other uses)
# sysctl -w net.ipv4.ip_forward=0

# Restart network manager to get DHCP on ethernet
if systemctl is-active --quiet NetworkManager; then
    systemctl restart NetworkManager
elif systemctl is-active --quiet dhcpcd; then
    systemctl restart dhcpcd
fi

log_info "=========================================="
log_info "Gateway mode disabled"
log_info "=========================================="
log_info "The Raspberry Pi is no longer acting as a gateway."
log_info "Ethernet interface will now use DHCP."
log_info ""
log_info "To re-enable gateway mode, run: sudo ./setup-gateway.sh"
