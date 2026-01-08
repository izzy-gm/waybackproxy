# WaybackProxy Installation Guide

## Quick Start (Raspberry Pi)

Run this single command as root on your Raspberry Pi:

```bash
bash -c "$(curl https://raw.githubusercontent.com/izzy-gm/waybackproxy/refs/heads/main/scripts/install.sh)"
```

That's it! The script will automatically detect and install the **latest stable release**.

## What Gets Installed

- **Location**: `/opt/waybackproxy`
- **User**: Dedicated `waybackproxy` system user
- **Service**: Systemd service running at boot
- **Logs**: `/var/log/waybackproxy/`
- **Config**: `/opt/waybackproxy/config.json`

## Install Specific Version or Branch

By default, the installer fetches the latest stable release. To install a specific version or development branch:

```bash
# Install from main branch (bleeding-edge development)
WAYBACKPROXY_BRANCH=main bash -c "$(curl https://raw.githubusercontent.com/izzy-gm/waybackproxy/refs/heads/main/scripts/install.sh)"

# Install specific release tag
WAYBACKPROXY_BRANCH=v2.0.0 bash -c "$(curl https://raw.githubusercontent.com/izzy-gm/waybackproxy/refs/heads/main/scripts/install.sh)"

# Install from develop branch
WAYBACKPROXY_BRANCH=develop bash -c "$(curl https://raw.githubusercontent.com/izzy-gm/waybackproxy/refs/heads/main/scripts/install.sh)"
```

## After Installation

### Managing the Service

```bash
# Check status
systemctl status waybackproxy

# View live logs
journalctl -u waybackproxy -f

# Restart after config changes
systemctl restart waybackproxy

# Stop/start
systemctl stop waybackproxy
systemctl start waybackproxy
```

### Edit Configuration

```bash
sudo nano /opt/waybackproxy/config.json
sudo systemctl restart waybackproxy
```

### View Logs

```bash
# Live system logs
journalctl -u waybackproxy -f

# Application logs
tail -f /var/log/waybackproxy/waybackproxy.log

# Error logs
tail -f /var/log/waybackproxy/waybackproxy.error.log
```

## Updating

Simply re-run the installation command to update to the latest stable release:

```bash
bash -c "$(curl https://raw.githubusercontent.com/izzy-gm/waybackproxy/refs/heads/main/scripts/install.sh)"
```

Your configuration and whitelist will be automatically backed up and restored.

The installer automatically detects and installs the latest release. Use `WAYBACKPROXY_BRANCH=main` to update to bleeding-edge development code.

## Requirements

- Raspberry Pi (tested on Pi 4)
- Raspberry Pi OS (Debian Trixie Lite or similar)
- Internet connection during installation
- Root access

## Hardware (Optional)

If using the LCD and rotary encoder:
- Connect LCD to I2C interface
- Connect rotary encoder to GPIO pins 26, 19 (encoder) and 13 (button)
- The install script enables I2C automatically (reboot required)

## Troubleshooting

### Service won't start

```bash
# Check logs for errors
journalctl -u waybackproxy -n 50

# Check service status
systemctl status waybackproxy
```

### LCD not working

```bash
# Verify I2C is enabled
ls /dev/i2c-*

# If not found, reboot after installation
sudo reboot

# Test I2C devices
i2cdetect -y 1
```

### Permission issues

```bash
# Verify user is in correct groups
groups waybackproxy

# Should show: waybackproxy gpio i2c dialout

# If not, reinstall
```

### Update not working

```bash
# Check if git repository is intact
sudo ls -la /opt/waybackproxy/.git

# If corrupted, remove and reinstall
sudo rm -rf /opt/waybackproxy
# Then run install command again
```

## Manual Installation (Not Recommended)

If you need to install manually:

1. Clone repository:
   ```bash
   git clone https://github.com/izzy-gm/waybackproxy /opt/waybackproxy
   cd /opt/waybackproxy
   ```

2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install urllib3 requests RPi.GPIO smbus2 RGB1602
   ```

4. Copy and edit configuration:
   ```bash
   cp config.sample.json config.json
   nano config.json
   ```

5. Run manually:
   ```bash
   ./start.sh
   ```

For production use, use the automated installer to set up the systemd service.

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop waybackproxy
sudo systemctl disable waybackproxy
sudo rm /etc/systemd/system/waybackproxy.service
sudo systemctl daemon-reload

# Remove installation
sudo rm -rf /opt/waybackproxy
sudo rm -rf /var/log/waybackproxy

# Remove user (optional)
sudo userdel waybackproxy
```

## Support

For issues, check:
1. Service logs: `journalctl -u waybackproxy -n 100`
2. Application logs: `/var/log/waybackproxy/waybackproxy.error.log`
3. Repository: https://github.com/izzy-gm/waybackproxy
