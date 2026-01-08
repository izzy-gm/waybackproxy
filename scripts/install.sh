#!/bin/bash
#
# WaybackProxy Installation Script for Raspberry Pi OS
# Usage: bash -c "$(curl https://raw.githubusercontent.com/izzy-gm/waybackproxy/refs/heads/main/scripts/install.sh)"
#
# This script installs or updates WaybackProxy on Raspberry Pi OS (Debian Trixie)
# Must be run as root
#

set -e  # Exit on error

# Configuration
REPO_URL="https://github.com/izzy-gm/waybackproxy"
BRANCH="${WAYBACKPROXY_BRANCH:-main}"
INSTALL_DIR="/opt/waybackproxy"
SERVICE_USER="waybackproxy"
SERVICE_NAME="waybackproxy"
LOG_DIR="/var/log/waybackproxy"
VENV_DIR="${INSTALL_DIR}/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

log_info "WaybackProxy Installation Script"
log_info "Branch: ${BRANCH}"
log_info "Install Directory: ${INSTALL_DIR}"

# Detect if this is an update or fresh install
if [ -d "${INSTALL_DIR}" ]; then
    OPERATION="update"
    log_info "Existing installation detected - performing update"
else
    OPERATION="install"
    log_info "No existing installation - performing fresh install"
fi

# Update system packages
log_info "Updating system packages..."
apt-get update -qq

# Install system dependencies
log_info "Installing system dependencies..."
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    swig \
    git \
    i2c-tools \
    python3-smbus

# Install GPIO system libraries
# liblgpio-dev is required for compiling rpi-lgpio from source
log_info "Installing GPIO system libraries..."
GPIO_SYSTEM_PACKAGE=""

# Try to install liblgpio-dev (development library for lgpio)
if apt-get install -y -qq liblgpio-dev 2>/dev/null; then
    log_info "✓ Installed liblgpio-dev (GPIO development library)"
fi

# Try to install modern GPIO library (for Bookworm/Trixie/kernel 6.x+)
# Falls back to old RPi.GPIO if not available (Bullseye and older)
if apt-get install -y -qq python3-rpi-lgpio 2>/dev/null; then
    log_info "✓ Installed python3-rpi-lgpio (modern GPIO library)"
    GPIO_SYSTEM_PACKAGE="python3-rpi-lgpio"
else
    log_warn "python3-rpi-lgpio not available, trying python3-rpi.gpio (legacy)"
    if apt-get install -y -qq python3-rpi.gpio; then
        log_info "✓ Installed python3-rpi.gpio (legacy GPIO library)"
        GPIO_SYSTEM_PACKAGE="python3-rpi.gpio"
    else
        log_warn "Could not install system GPIO library (OK if running headless)"
    fi
fi

# Enable I2C for LCD display
log_info "Enabling I2C interface..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null && \
   ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null; then
    # Try new location first (Bookworm and later)
    if [ -f /boot/firmware/config.txt ]; then
        echo "dtparam=i2c_arm=on" >> /boot/firmware/config.txt
    # Fallback to old location
    elif [ -f /boot/config.txt ]; then
        echo "dtparam=i2c_arm=on" >> /boot/config.txt
    fi
    log_warn "I2C enabled - reboot required for changes to take effect"
fi

# Load I2C kernel module
if ! lsmod | grep -q i2c_dev; then
    modprobe i2c-dev 2>/dev/null || true
fi

# Create system user if it doesn't exist
if ! id -u ${SERVICE_USER} >/dev/null 2>&1; then
    log_info "Creating system user: ${SERVICE_USER}"
    useradd --system --home-dir ${INSTALL_DIR} --shell /bin/false ${SERVICE_USER}
fi

# Add user to required groups for GPIO and I2C access
log_info "Adding ${SERVICE_USER} to gpio, i2c, dialout, and video groups..."
usermod -a -G gpio,i2c,dialout,video ${SERVICE_USER} 2>/dev/null || true

# Ensure proper GPIO permissions
log_info "Setting up GPIO permissions..."
# Add udev rule for GPIO access
cat > /etc/udev/rules.d/99-gpio.rules <<'UDEV_EOF'
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /sys/class/gpio/export /sys/class/gpio/unexport ; chmod 220 /sys/class/gpio/export /sys/class/gpio/unexport'"
SUBSYSTEM=="gpio", KERNEL=="gpio*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /sys%p/active_low /sys%p/direction /sys%p/edge /sys%p/value ; chmod 660 /sys%p/active_low /sys%p/direction /sys%p/edge /sys%p/value'"
SUBSYSTEM=="bcm2835-gpiomem", KERNEL=="gpiomem", MODE="0660", GROUP="gpio"
UDEV_EOF

# Reload udev rules
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

# Set permissions on /dev/gpiomem if it exists
if [ -e /dev/gpiomem ]; then
    chgrp gpio /dev/gpiomem 2>/dev/null || true
    chmod g+rw /dev/gpiomem 2>/dev/null || true
fi

# Backup existing config if updating
if [ "${OPERATION}" = "update" ] && [ -f "${INSTALL_DIR}/config.json" ]; then
    log_info "Backing up existing configuration..."
    cp "${INSTALL_DIR}/config.json" "${INSTALL_DIR}/config.json.backup"
fi

# Backup existing whitelist if updating
if [ "${OPERATION}" = "update" ] && [ -f "${INSTALL_DIR}/whitelist.txt" ]; then
    log_info "Backing up existing whitelist..."
    cp "${INSTALL_DIR}/whitelist.txt" "${INSTALL_DIR}/whitelist.txt.backup"
fi

# Stop service if running
if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_info "Stopping ${SERVICE_NAME} service..."
    systemctl stop ${SERVICE_NAME}
fi

# Create installation directory
mkdir -p ${INSTALL_DIR}

# Clone or update repository
if [ -d "${INSTALL_DIR}/.git" ]; then
    log_info "Updating repository from branch ${BRANCH}..."
    cd ${INSTALL_DIR}

    # Add safe.directory exception for git operations
    git config --global --add safe.directory ${INSTALL_DIR} 2>/dev/null || true

    # Temporarily take ownership for git operations
    ORIGINAL_OWNER=$(stat -c '%U' ${INSTALL_DIR} 2>/dev/null || stat -f '%Su' ${INSTALL_DIR} 2>/dev/null || echo "root")
    if [ "${ORIGINAL_OWNER}" != "root" ]; then
        chown -R root:root ${INSTALL_DIR}
    fi

    # Discard any local changes
    git reset --hard HEAD 2>/dev/null || true
    git clean -fd 2>/dev/null || true

    git fetch --all
    git checkout ${BRANCH}
    git reset --hard origin/${BRANCH}

    # Restore ownership
    if [ "${ORIGINAL_OWNER}" != "root" ]; then
        chown -R ${ORIGINAL_OWNER}:${ORIGINAL_OWNER} ${INSTALL_DIR}
    fi
else
    log_info "Cloning repository from branch ${BRANCH}..."
    # If directory exists but isn't a git repo, move it
    if [ -d "${INSTALL_DIR}" ] && [ "$(ls -A ${INSTALL_DIR})" ]; then
        mv ${INSTALL_DIR} ${INSTALL_DIR}.old.$(date +%s)
        mkdir -p ${INSTALL_DIR}
    fi
    git clone --branch ${BRANCH} ${REPO_URL} ${INSTALL_DIR}
    cd ${INSTALL_DIR}
fi

################################################################################
# Clean up legacy files from old architecture (pre-2.0)
################################################################################

if [ "${OPERATION}" = "update" ]; then
    # Check if this is an upgrade from old architecture (pre-2.0)
    # by looking for legacy files
    LEGACY_DETECTED=false
    if [ -f "${INSTALL_DIR}/waybackproxy.py" ] || [ -f "${INSTALL_DIR}/init.py" ]; then
        LEGACY_DETECTED=true
    fi

    if [ "$LEGACY_DETECTED" = true ]; then
        echo ""
        log_info "╔════════════════════════════════════════════════════════════╗"
        log_info "║  Upgrading to WaybackProxy 2.0 Architecture               ║"
        log_info "╚════════════════════════════════════════════════════════════╝"
        echo ""
        log_info "This update includes a major architecture refactoring:"
        log_info "  • New modular Python package structure (src/waybackproxy/)"
        log_info "  • Modern CLI with --headless and --debug options"
        log_info "  • Type-safe configuration with validation"
        log_info "  • Hardware abstraction for better maintainability"
        log_info "  • Comprehensive logging infrastructure"
        echo ""
        log_info "Your configuration (config.json) and whitelist will be preserved."
        log_info "Legacy files will be automatically removed."
        echo ""
    fi

    log_info "Cleaning up legacy files from old architecture..."

    # List of legacy files that were replaced in 2.0 architecture refactoring
    LEGACY_FILES=(
        "waybackproxy.py"
        "init.py"
        "config.py"
        "config_handler.py"
        "DateChanger.py"
        "RotaryEncoder.py"
        "KeyCapture.py"
        "RGB1602.py"
        "lrudict.py"
        "encoder_test.py"
        "nohup.out"
    )

    CLEANED=0
    for file in "${LEGACY_FILES[@]}"; do
        if [ -f "${INSTALL_DIR}/${file}" ]; then
            rm -f "${INSTALL_DIR}/${file}"
            log_info "  Removed: ${file}"
            CLEANED=$((CLEANED+1))
        fi
    done

    # Remove legacy start.sh from scripts/ if it exists
    if [ -f "${INSTALL_DIR}/scripts/start.sh" ]; then
        rm -f "${INSTALL_DIR}/scripts/start.sh"
        log_info "  Removed: scripts/start.sh (replaced by dynamic version)"
        CLEANED=$((CLEANED+1))
    fi

    if [ $CLEANED -gt 0 ]; then
        log_info "✓ Cleaned up ${CLEANED} legacy file(s)"

        if [ "$LEGACY_DETECTED" = true ]; then
            echo ""
            log_info "Architecture upgrade complete!"
            log_info "The new package structure is now in: src/waybackproxy/"
            echo ""
        fi
    else
        log_info "✓ No legacy files found (clean upgrade)"
    fi
fi

# Create Python virtual environment
if [ ! -d "${VENV_DIR}" ]; then
    log_info "Creating Python virtual environment..."
    python3 -m venv ${VENV_DIR}
else
    log_info "Using existing Python virtual environment..."
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source ${VENV_DIR}/bin/activate

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    log_error "Failed to activate virtual environment"
    exit 1
fi

log_info "Virtual environment activated: $VIRTUAL_ENV"
log_info "Using pip: $(which pip)"

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip

# Install WaybackProxy package (core dependencies only)
log_info "Installing WaybackProxy package and core dependencies..."
pip install -e "${INSTALL_DIR}" || {
    log_error "Failed to install WaybackProxy package"
    log_error "Pip exit code: $?"
    deactivate
    exit 1
}

log_info "✓ Core package installed successfully"

# Install GPIO/hardware dependencies separately (optional for headless operation)
log_info "Installing hardware UI dependencies (GPIO and I2C libraries)..."
log_info "Note: These are optional and only needed for Raspberry Pi hardware UI"

# Determine Python version for system package path
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
SYSTEM_PACKAGES_PATH="/usr/lib/python3/dist-packages"

# First, remove any existing GPIO packages to avoid conflicts
pip uninstall -y RPi.GPIO rpi-lgpio 2>/dev/null || true

# Install smbus2 (for I2C/LCD communication)
log_info "Installing smbus2..."
if pip install smbus2 2>/dev/null; then
    log_info "✓ Installed smbus2"
else
    log_warn "Failed to install smbus2 (LCD may not work)"
fi

# Try to install rpi-lgpio via pip (may need compilation)
log_info "Installing rpi-lgpio..."
if pip install rpi-lgpio 2>/dev/null; then
    log_info "✓ Installed rpi-lgpio via pip (compiled successfully)"
else
    log_warn "rpi-lgpio compilation failed, trying system package..."
    # Compilation failed, use system package instead
    if [ "$GPIO_SYSTEM_PACKAGE" = "python3-rpi-lgpio" ]; then
        log_info "Using system python3-rpi-lgpio package (compilation failed)"
        # Create symlink to system package
        VENV_SITE_PACKAGES="${VENV_DIR}/lib/python${PYTHON_VERSION}/site-packages"

        # Remove any existing broken links
        rm -f "$VENV_SITE_PACKAGES/RPi" 2>/dev/null || true
        rm -f "$VENV_SITE_PACKAGES/lgpio"* 2>/dev/null || true

        # Link RPi module
        if [ -d "$SYSTEM_PACKAGES_PATH/RPi" ]; then
            ln -sf "$SYSTEM_PACKAGES_PATH/RPi" "$VENV_SITE_PACKAGES/RPi"
            log_info "✓ Linked RPi module"
        fi

        # Link lgpio module - needs both .py wrapper and .so extension
        LGPIO_PY_LINKED=false
        LGPIO_SO_LINKED=false

        # Link lgpio.py (Python wrapper)
        if [ -f "$SYSTEM_PACKAGES_PATH/lgpio.py" ]; then
            ln -sf "$SYSTEM_PACKAGES_PATH/lgpio.py" "$VENV_SITE_PACKAGES/lgpio.py"
            LGPIO_PY_LINKED=true
            log_info "✓ Linked lgpio.py"
        fi

        # Link _lgpio*.so (compiled C extension) - note the underscore prefix
        for lgpio_so in "$SYSTEM_PACKAGES_PATH/_lgpio.cpython"*.so "$SYSTEM_PACKAGES_PATH/_lgpio"*.so; do
            if [ -f "$lgpio_so" ]; then
                ln -sf "$lgpio_so" "$VENV_SITE_PACKAGES/$(basename $lgpio_so)"
                LGPIO_SO_LINKED=true
                log_info "✓ Linked lgpio C extension: $(basename $lgpio_so)"
                break
            fi
        done

        if [ "$LGPIO_PY_LINKED" = true ] && [ "$LGPIO_SO_LINKED" = true ]; then
            log_info "✓ Successfully linked system rpi-lgpio to venv"
        else
            [ "$LGPIO_PY_LINKED" = false ] && log_warn "Could not find lgpio.py in system packages"
            [ "$LGPIO_SO_LINKED" = false ] && log_warn "Could not find _lgpio*.so in system packages"
            log_warn "Hardware UI may not work without GPIO library"
        fi
    elif [ "$GPIO_SYSTEM_PACKAGE" = "python3-rpi.gpio" ]; then
        log_info "Using system python3-rpi.gpio package (legacy)"
        # Try to install legacy RPi.GPIO
        if pip install RPi.GPIO 2>/dev/null; then
            log_info "✓ Installed RPi.GPIO via pip"
        else
            # If pip install fails, symlink system package
            VENV_SITE_PACKAGES="${VENV_DIR}/lib/python${PYTHON_VERSION}/site-packages"
            if [ -d "$SYSTEM_PACKAGES_PATH/RPi" ]; then
                ln -sf "$SYSTEM_PACKAGES_PATH/RPi" "$VENV_SITE_PACKAGES/RPi" 2>/dev/null || true
                log_info "✓ Linked system RPi.GPIO to venv"
            else
                log_warn "Could not install or link RPi.GPIO"
            fi
        fi
    else
        log_warn "No GPIO library could be installed"
        log_warn "WaybackProxy will work in headless mode only (--headless)"
        log_warn "For hardware UI support, install liblgpio-dev: apt-get install liblgpio-dev"
    fi
fi

# Verify critical packages are installed
log_info "Verifying installation..."
python3 -c "import waybackproxy; print('✓ waybackproxy version:', waybackproxy.__version__)" || {
    log_error "waybackproxy package not found"
    deactivate
    exit 1
}

python3 -c "import urllib3; print('✓ urllib3 version:', urllib3.__version__)" || {
    log_error "urllib3 not found"
    deactivate
    exit 1
}

python3 -c "import requests; print('✓ requests version:', requests.__version__)" || {
    log_error "requests not found"
    deactivate
    exit 1
}

# Check GPIO library (optional - not required for headless mode)
GPIO_AVAILABLE=false
if python3 -c "import RPi.GPIO as GPIO; print('✓ RPi.GPIO available')" 2>/dev/null; then
    GPIO_AVAILABLE=true
else
    log_warn "GPIO library not available"
    log_warn "Hardware UI will not work. Use --headless mode or install GPIO libraries."
fi

# Check I2C library (optional - not required for headless mode)
if python3 -c "import smbus2; print('✓ smbus2 available')" 2>/dev/null; then
    true
else
    log_warn "smbus2 not available (I2C/LCD will not work)"
fi

log_info "WaybackProxy core installation successful"

# Summary of what's available
echo ""
log_info "Installation Summary:"
log_info "  ✓ Core proxy engine: Ready"
log_info "  ✓ Configuration system: Ready"
if [ "$GPIO_AVAILABLE" = true ]; then
    log_info "  ✓ Hardware UI support: Available"
else
    log_info "  ⚠ Hardware UI support: Not available (use --headless mode)"
fi

# Deactivate virtual environment
deactivate

# Handle configuration files
if [ "${OPERATION}" = "update" ]; then
    # Update - restore backed up config if it exists
    if [ -f "${INSTALL_DIR}/config.json.backup" ]; then
        log_info "Restoring backed up configuration..."
        cp "${INSTALL_DIR}/config.json.backup" "${INSTALL_DIR}/config.json"
    fi

    # Restore whitelist
    if [ -f "${INSTALL_DIR}/whitelist.txt.backup" ]; then
        log_info "Restoring backed up whitelist..."
        cp "${INSTALL_DIR}/whitelist.txt.backup" "${INSTALL_DIR}/whitelist.txt"
    fi
fi

# Create config.json from sample if it doesn't exist
if [ ! -f "${INSTALL_DIR}/config.json" ]; then
    log_info "Creating configuration from sample..."
    if [ -f "${INSTALL_DIR}/config.sample.json" ]; then
        cp "${INSTALL_DIR}/config.sample.json" "${INSTALL_DIR}/config.json"
        log_info "✓ Created config.json from config.sample.json"
    else
        log_error "config.sample.json not found in repository"
        exit 1
    fi
fi

# Create whitelist.txt if it doesn't exist
if [ ! -f "${INSTALL_DIR}/whitelist.txt" ]; then
    log_info "Creating empty whitelist.txt..."
    touch ${INSTALL_DIR}/whitelist.txt
fi

# Create or update start.sh
log_info "Creating start script..."
cat > ${INSTALL_DIR}/start.sh <<'EOF'
#!/bin/bash
# WaybackProxy Start Script

# Change to installation directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Check if GPIO is available
if python3 -c "import RPi.GPIO" 2>/dev/null; then
    # GPIO available - run with hardware UI
    echo "Starting WaybackProxy with hardware UI (LCD + rotary encoder)"
    exec python3 -m waybackproxy
else
    # GPIO not available - run in headless mode
    echo "GPIO not available - starting WaybackProxy in headless mode"
    exec python3 -m waybackproxy --headless
fi
EOF

chmod +x ${INSTALL_DIR}/start.sh
log_info "✓ Start script will auto-detect GPIO and run appropriate mode"

# Make gateway scripts executable
chmod +x ${INSTALL_DIR}/scripts/setup-gateway.sh 2>/dev/null || true
chmod +x ${INSTALL_DIR}/scripts/disable-gateway.sh 2>/dev/null || true

# Create log directory
log_info "Creating log directory..."
mkdir -p ${LOG_DIR}

# Set ownership
log_info "Setting file permissions..."
chown -R ${SERVICE_USER}:${SERVICE_USER} ${INSTALL_DIR}
chown -R ${SERVICE_USER}:${SERVICE_USER} ${LOG_DIR}

# Create systemd service
log_info "Creating systemd service..."
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=WaybackProxy - Retro-friendly HTTP proxy for Internet Archive
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/start.sh
ExecStopPost=/usr/bin/python3 -c "try:\n from RPi import GPIO\n GPIO.cleanup()\nexcept: pass"
Restart=always
RestartSec=10
StandardOutput=append:${LOG_DIR}/waybackproxy.log
StandardError=append:${LOG_DIR}/waybackproxy.error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Allow network binding
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
log_info "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
log_info "Enabling ${SERVICE_NAME} service to start on boot..."
systemctl enable ${SERVICE_NAME}

# Start the service (it will auto-detect GPIO and run appropriate mode)
log_info "Starting ${SERVICE_NAME} service..."
systemctl start ${SERVICE_NAME}

# Wait a moment for service to start
sleep 3

# Check service status
if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_info "✓ ${SERVICE_NAME} service is running"

    # Check what mode it started in
    sleep 1
    if journalctl -u ${SERVICE_NAME} -n 10 --no-pager | grep -q "headless"; then
        log_info "  Running in: Headless mode (no GPIO detected)"
    else
        log_info "  Running in: Hardware UI mode (GPIO available)"
    fi
else
    log_error "✗ ${SERVICE_NAME} service failed to start"
    log_error "Check logs with: journalctl -u ${SERVICE_NAME} -n 50"

    # Show last few log lines for debugging
    echo ""
    log_error "Recent logs:"
    journalctl -u ${SERVICE_NAME} -n 10 --no-pager
    exit 1
fi

# Display status
echo ""
log_info "=========================================="
log_info "WaybackProxy ${OPERATION} completed successfully!"
log_info "=========================================="
echo ""

# Check if reboot is recommended for I2C/GPIO
REBOOT_RECOMMENDED=false
I2C_AVAILABLE=false
if [ -e /dev/i2c-1 ] || [ -e /dev/i2c-0 ]; then
    I2C_AVAILABLE=true
fi

# Check if I2C was just enabled but not yet available
if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null && \
   ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null; then
    # I2C already enabled in config
    if [ "$I2C_AVAILABLE" = false ]; then
        REBOOT_RECOMMENDED=true
    fi
fi

if [ "$REBOOT_RECOMMENDED" = true ] && [ "$GPIO_AVAILABLE" = false ]; then
    echo ""
    log_warn "╔════════════════════════════════════════╗"
    log_warn "║      REBOOT RECOMMENDED                ║"
    log_warn "╚════════════════════════════════════════╝"
    echo ""
    log_warn "I2C/GPIO interfaces were enabled but may require a reboot."
    log_warn "Currently running in headless mode."
    echo ""
    log_warn "After reboot, hardware UI (LCD + rotary encoder) will be available."
    echo ""
    log_warn "To reboot now, run:"
    echo ""
    echo "    sudo reboot"
    echo ""
    log_warn "After reboot, the service will automatically detect GPIO and use hardware UI."
    echo ""
else
    log_info "Service Status: $(systemctl is-active ${SERVICE_NAME})"
    log_info "Installation Directory: ${INSTALL_DIR}"
    log_info "Configuration File: ${INSTALL_DIR}/config.json"
    log_info "Log Files: ${LOG_DIR}/"
    echo ""
    log_info "Useful Commands:"
    echo "  - View logs:        journalctl -u ${SERVICE_NAME} -f"
    echo "  - View error logs:  tail -f ${LOG_DIR}/waybackproxy.error.log"
    echo "  - Restart service:  systemctl restart ${SERVICE_NAME}"
    echo "  - Stop service:     systemctl stop ${SERVICE_NAME}"
    echo "  - Service status:   systemctl status ${SERVICE_NAME}"
    echo "  - Edit config:      nano ${INSTALL_DIR}/config.json"
    echo "  - After editing:    systemctl restart ${SERVICE_NAME}"
    echo ""

    # Show GPIO troubleshooting if not available
    if [ "$GPIO_AVAILABLE" = false ]; then
        log_info "╔════════════════════════════════════════╗"
        log_info "║   GPIO TROUBLESHOOTING (OPTIONAL)      ║"
        log_info "╚════════════════════════════════════════╝"
        echo ""
        log_info "To enable hardware UI (LCD + rotary encoder):"
        echo "  1. Install GPIO development library:"
        echo "     sudo apt-get install liblgpio-dev"
        echo ""
        echo "  2. Reinstall WaybackProxy:"
        echo "     sudo bash -c \"\$(curl https://raw.githubusercontent.com/izzy-gm/waybackproxy/refs/heads/${BRANCH}/scripts/install.sh)\""
        echo ""
        echo "  OR run in headless mode:"
        echo "     python3 -m waybackproxy --headless"
        echo ""
    fi

    log_info "╔════════════════════════════════════════╗"
    log_info "║        GATEWAY MODE (OPTIONAL)         ║"
    log_info "╚════════════════════════════════════════╝"
    echo ""
    log_info "Gateway mode turns this Pi into a transparent proxy."
    echo "  Computers connected to the ethernet port will have all"
    echo "  HTTP traffic automatically routed through WaybackProxy."
    echo ""

    # Prompt for gateway mode
    read -p "Would you like to enable gateway mode now? [Y/n]: " ENABLE_GATEWAY
    ENABLE_GATEWAY=${ENABLE_GATEWAY:-y}
    echo ""

    if [[ "$ENABLE_GATEWAY" =~ ^[Yy]$ ]] || [ -z "$ENABLE_GATEWAY" ]; then
        log_info "Enabling gateway mode..."
        if [ -x "${INSTALL_DIR}/scripts/setup-gateway.sh" ]; then
            bash "${INSTALL_DIR}/scripts/setup-gateway.sh"
        else
            log_error "Gateway setup script not found or not executable"
            log_info "You can enable it later with: sudo ${INSTALL_DIR}/scripts/setup-gateway.sh"
        fi
    else
        log_info "Gateway mode not enabled."
        echo ""
        echo "  To enable later:   sudo ${INSTALL_DIR}/scripts/setup-gateway.sh"
        echo "  To disable:        sudo ${INSTALL_DIR}/scripts/disable-gateway.sh"
        echo ""
    fi
fi

exit 0
