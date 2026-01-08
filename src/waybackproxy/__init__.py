# Copyright (C) 2024-2026 Izzy Graniel
#
# This file is part of WaybackProxy.
#
# WaybackProxy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""WaybackProxy - Retro-friendly HTTP proxy for Internet Archive.

For Raspberry Pi 4 with Raspberry Pi OS (Debian Trixie).
"""
from __future__ import annotations

__version__ = "2.0.0"
__author__ = "izzy-gm"

# Core proxy components
from .core import Handler, SharedState, ThreadedProxyServer

# Configuration
from .config import (
    HardwareSettings,
    ProxySettings,
    Settings,
    load_config,
    save_config,
)

# Hardware abstractions
from .hardware import Display, DisplayType, InputDevice, create_display

# UI components
from .ui import DateSelector, UIController

# Utilities
from .utils import get_local_ip, setup_logging

__all__ = [
    # Version
    "__version__",
    "__author__",
    # Core
    "Handler",
    "SharedState",
    "ThreadedProxyServer",
    # Configuration
    "Settings",
    "ProxySettings",
    "HardwareSettings",
    "load_config",
    "save_config",
    # Hardware
    "Display",
    "InputDevice",
    "DisplayType",
    "create_display",
    # UI
    "UIController",
    "DateSelector",
    # Utilities
    "setup_logging",
    "get_local_ip",
]
