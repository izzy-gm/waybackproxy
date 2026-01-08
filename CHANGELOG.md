# Changelog

All notable changes to WaybackProxy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-01-08

### Added
- Installer now automatically detects and installs the latest stable release by default
- Support for installing specific release tags via `WAYBACKPROXY_BRANCH` environment variable
- Comprehensive project description highlighting end-to-end solution and unique features
- Documentation for dual proxy modes (transparent gateway and standard proxy)

### Changed
- Installation script now queries GitHub API for latest release instead of defaulting to main branch
- Installer script location moved to `scripts/install.sh` directory
- Updated all GitHub raw URLs to use correct format: `raw.githubusercontent.com/izzy-gm/waybackproxy/refs/heads/main/scripts/install.sh`
- Improved README.md with clear explanation of what makes WaybackProxy different from other solutions
- Enhanced documentation across README.md, INSTALL.md, and CLAUDE.md to emphasize production-ready features

### Fixed
- Corrected GitHub raw file URLs from deprecated `/raw/branch/main/` format to proper `/refs/heads/main/` format
- Installation script now properly references the `scripts/` subdirectory

## [2.0.0] - 2026-01-08

### Added
- Complete architectural refactoring to modular Python package structure
- Modern CLI with `--headless` and `--debug` options
- Type-safe configuration system with validation
- Hardware abstraction layer for better maintainability
- Comprehensive logging infrastructure with rotating file handlers
- Web-based configuration interface accessible at `http://web.archive.org` when using proxy
- Gateway mode for transparent proxy via Ethernet port
- Support for both rpi-lgpio (modern) and RPi.GPIO (legacy) libraries
- Automatic GPIO library detection and graceful fallback
- Domain whitelist functionality for bypassing Wayback Machine
- LRU caching for improved performance
- Systemd service integration for automatic startup
- Comprehensive installation script with dependency management
- Support for Raspberry Pi 4 with Raspberry Pi OS (Debian Trixie)

### Changed
- Migrated from flat file structure to organized `src/waybackproxy/` package
- Refactored configuration to use dataclasses instead of global variables
- Improved hardware abstraction for LCD and rotary encoder
- Enhanced error handling and user feedback
- Modernized code to use Python 3.12+ features and type hints

### Deprecated
- Legacy `config.py` file (now uses `config.json`)
- Old flat file structure with root-level Python files

### Removed
- Legacy files: `waybackproxy.py`, `init.py`, `config.py`, `config_handler.py`, `DateChanger.py`, `RotaryEncoder.py`, `KeyCapture.py`, `RGB1602.py`, `lrudict.py`

### Fixed
- GPIO permission issues on Raspberry Pi OS Trixie
- I2C device access reliability
- Virtual environment GPIO library compatibility
- Service startup reliability with proper dependency ordering

### Security
- Added systemd security hardening (NoNewPrivileges, PrivateTmp)
- Proper user/group permissions for GPIO and I2C access

## [1.0.0] - 2024-XX-XX (Pre-refactor)

Initial release based on richardg867's WaybackProxy with hardware interface additions.

### Added
- Basic HTTP proxy functionality for Wayback Machine
- Raspberry Pi hardware interface (LCD + rotary encoder)
- OoCities redirect support for GeoCities URLs
- Quick Images mode for faster asset loading
- Date tolerance configuration
- Basic whitelist support

[Unreleased]: https://github.com/izzy-gm/waybackproxy/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/izzy-gm/waybackproxy/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/izzy-gm/waybackproxy/releases/tag/v2.0.0
