# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WaybackProxy is a retro-friendly HTTP proxy that retrieves pages from the Internet Archive Wayback Machine or OoCities and delivers them in their original form, without toolbars and scripts that may confuse retro browsers. The project includes a hardware interface component designed for Raspberry Pi with a rotary encoder and LCD display.

## Core Architecture

### Two-Component System

1. **Proxy Server** (`waybackproxy.py`): The HTTP proxy server that handles requests
2. **Hardware UI** (`init.py`): Optional Raspberry Pi interface with rotary encoder and LCD display

### Key Components

- **Handler Class** (waybackproxy.py:37): Main request handler inheriting from `socketserver.BaseRequestHandler`. Processes incoming HTTP requests, rewrites URLs to point to Wayback Machine, and strips archive UI elements from responses.

- **SharedState Class** (waybackproxy.py:14): Manages shared resources across handler instances:
  - `http`: urllib3 connection pool for making requests
  - `date_cache`: LRU dict preserving URLs on redirect (24hr TTL, 1024 items)
  - `availability_cache`: LRU dict for caching Wayback API date availability responses
  - `whitelist`: Domains that bypass the Wayback Machine

- **ThreadingTCPServer** (waybackproxy.py:10): Multi-threaded TCP server allowing concurrent request handling

### Configuration System

Configuration is loaded from `config.json` by `config_handler.py` which exports global variables. The legacy `config.py` file shows default values but is not used at runtime. When modifying settings:
- Edit `config.json` for persistent changes
- Use the web-based settings page at `http://web.archive.org` when connected through the proxy (if SETTINGS_PAGE is enabled)
- Hardware UI allows date changes via rotary encoder/LCD

### Request Flow

1. Client sends HTTP GET request to proxy
2. Handler parses URL and determines if it should:
   - Pass through directly (whitelisted domains)
   - Redirect to OoCities (Geocities fix)
   - Fetch from Wayback Machine
3. If using Wayback:
   - Optionally consults Wayback Availability API to find closest snapshot
   - Constructs URL with date code and asset flags (e.g., `if_`, `im_`, `js_`)
   - Fetches content via urllib3
4. For HTML responses:
   - Strips Wayback toolbar and scripts
   - Rewrites URLs to remove web.archive.org references
   - Optionally enables QUICK_IMAGES mode to keep asset URLs pointing to Wayback
5. Returns sanitized content to client

### URL Rewriting Modes

- **Standard Mode**: All URLs are rewritten to remove Wayback elements
- **QUICK_IMAGES Mode**: Asset URLs (images, CSS, JS) point directly to web.archive.org for faster loading
- **QUICK_IMAGES=2 Mode**: Uses HTTP authentication (username:password) for asset date codes (not supported by all browsers)

### Date Handling

The proxy uses Wayback Machine date codes in format YYYYMMDD[HHMMSScc][tag]:
- Base date (e.g., `20011025`) set via DATE config
- Optional asset tags: `if_` (identity/HTML), `im_` (image), `js_` (JavaScript)
- DATE_TOLERANCE restricts content to within X days of the configured date

## Installation on Raspberry Pi

### Automated Installation (Recommended)

Run the installation script as root on a fresh Raspberry Pi OS instance:

```bash
bash -c "$(curl https://github.com/izzy-gm/waybackproxy/raw/branch/main/install.sh)"
```

**To install a specific branch:**
```bash
WAYBACKPROXY_BRANCH=develop bash -c "$(curl https://github.com/izzy-gm/waybackproxy/raw/branch/main/install.sh)"
```

The script will:
- Install system dependencies (Python 3, git, I2C tools, GPIO libraries)
- Create a dedicated `waybackproxy` system user
- Install to `/opt/waybackproxy`
- Set up Python virtual environment with all dependencies
- Create default configuration at `/opt/waybackproxy/config.json`
- Install systemd service to run at boot
- Enable I2C interface for LCD display
- Start the service automatically

### Post-Installation

**Service Management:**
```bash
systemctl status waybackproxy    # Check service status
systemctl restart waybackproxy   # Restart after config changes
systemctl stop waybackproxy      # Stop service
systemctl start waybackproxy     # Start service
journalctl -u waybackproxy -f    # View live logs
```

**Configuration:**
```bash
nano /opt/waybackproxy/config.json    # Edit configuration
systemctl restart waybackproxy         # Apply changes
```

**Log Files:**
- Standard output: `/var/log/waybackproxy/waybackproxy.log`
- Error output: `/var/log/waybackproxy/waybackproxy.error.log`
- System logs: `journalctl -u waybackproxy`

**Updates:**
Re-run the install script to update to the latest version. Your `config.json` and `whitelist.txt` will be preserved.

## Development Commands

### Running Locally (Development)

**Standalone proxy server:**
```bash
python3 waybackproxy.py
```

**With hardware UI (Raspberry Pi):**
```bash
python3 init.py
```

**Using the start script:**
```bash
./start.sh
```

### Docker

**Build:**
```bash
docker build --no-cache -t waybackproxy .
```

**Run:**
```bash
docker run --rm -it -e DATE=20011225 -p 8888:8888 waybackproxy
```

### Manual Dependencies Installation

Install required packages (only needed for local development):
```bash
pip3 install urllib3 requests
```

For Raspberry Pi hardware interface:
```bash
pip3 install RPi.GPIO smbus2 RGB1602
```

## Testing

**Local Testing:**
1. Start the server: `python3 waybackproxy.py` or `systemctl start waybackproxy`
2. Configure a browser to use `localhost:8888` as HTTP proxy
3. Or use PAC file at `http://localhost:8888/proxy.pac`
4. Navigate to archived websites

**Remote Testing:**
The app runs at:
- Production: https://phoenix.example.com
- API endpoint: https://pnx.example.com/api

**Workflow for Testing on Raspberry Pi:**
1. Make changes locally on Mac
2. Commit and push to repository
3. SSH into Raspberry Pi: `ssh pi@<raspberry-pi-ip>`
4. Update: `sudo bash -c "$(curl https://github.com/izzy-gm/waybackproxy/raw/branch/main/install.sh)"`
5. Check logs: `journalctl -u waybackproxy -f`

## Hardware UI (Raspberry Pi)

When using `init.py`, the system provides:
- **Rotary encoder input** for date navigation (GPIO pins 26, 19, 13 by default)
- **LCD1602 RGB display** showing current date and proxy status
- **DateChanger class** (DateChanger.py) manages year/month/day selection with historical constraints (min: 1996-05-10, max: today)

The UI runs the proxy server in a background thread and provides a real-time interface for changing the archive date without restarting the server.

### Hardware Components

**LCD Display**: Waveshare LCD1602 RGB Module
- Documentation: https://www.waveshare.com/wiki/LCD1602_RGB_Module
- Interface: I2C (address 0x3E for LCD, 0x60 for RGB backlight)
- Uses `smbus2` Python library for I2C communication

**Rotary Encoder**: Generic KY-040 or similar
- 360-degree rotation with 20 positions/pulses
- Includes push button switch
- Specifications:
  - Rated voltage: DC 5V
  - Rotational life: Min. 50000 cycles
  - Switch life: Min. 20000 cycles
  - Shaft: 6mm diameter, 20mm length
- Reference: https://www.amazon.ca/dp/B08728K3YB

**GPIO Pin Assignments** (BCM numbering):
- GPIO 26: Rotary encoder CLK
- GPIO 19: Rotary encoder DT
- GPIO 13: Push button (encoder switch)

## Important Patterns

### LRU Caching
The custom `lrudict.py` implementation provides time-based and size-based eviction. When items are accessed via `[]` or `get()`, their TTL refreshes. Iteration does not refresh TTL.

### Error Handling
- 404/403 errors trigger redirect guessing (heuristic URL extraction from redirect scripts)
- Wayback-specific error pages are detected and converted to proper HTTP errors
- Tolerance violations return 412 Precondition Failed

### Security Considerations
- Only GET method is implemented (POST/CONNECT not supported)
- No authentication/authorization (designed for trusted networks)
- Transparent proxy mode requires HTTP/1.1 Host header

## File Structure

- `waybackproxy.py`: Core proxy server implementation
- `config_handler.py`: Loads configuration from config.json
- `config.json`: Active configuration file (edit this for changes)
- `config.py`: Legacy default values (reference only)
- `lrudict.py`: LRU dictionary with TTL support
- `init.py`: Raspberry Pi hardware UI entry point
- `DateChanger.py`: Date navigation logic with historical constraints
- `RotaryEncoder.py`: Rotary encoder hardware interface
- `RGB1602.py`: LCD display driver
- `KeyCapture.py`: Keyboard alternative to rotary encoder
- `whitelist.txt`: Domains that bypass Wayback Machine

## Configuration Reference

Key settings in `config.json`:
- `LISTEN_PORT`: Proxy server port (default: 8888)
- `DATE`: Target date in YYYYMMDD format
- `DATE_TOLERANCE`: Days after DATE that assets can be loaded (null = unlimited)
- `WAYBACK_API`: Use Availability API to find closest snapshots (slower but more reliable)
- `QUICK_IMAGES`: Keep web.archive.org URLs for assets (faster, more tainted HTML)
- `GEOCITIES_FIX`: Redirect Geocities requests to oocities.org
- `CONTENT_TYPE_ENCODING`: Allow charset in Content-Type (disable for very old browsers like Mosaic)
- `SILENT`: Disable logging to stdout
- `SETTINGS_PAGE`: Enable web-based settings at http://web.archive.org

## Known Limitations

- Only HTTP GET is supported (no POST/CONNECT)
- Transparent proxy mode requires HTTP/1.1 (incompatible with pre-1996 browsers)
- Wayback Machine itself has reliability issues (404s, redirect loops, server errors)
- Some redirect scripts cannot be parsed heuristically
- Hardware UI is Raspberry Pi specific (requires GPIO access)
