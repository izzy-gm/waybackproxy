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

"""Configuration file loading and merging."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .settings import HardwareSettings, ProxySettings, Settings


def load_config(config_path: str = "config.json") -> Settings:
    """Load configuration from JSON file.

    Merges with defaults from Settings dataclasses.

    Args:
        config_path: Path to configuration file (default: config.json)

    Returns:
        Settings object with loaded configuration

    Raises:
        ValueError: If configuration is invalid
        json.JSONDecodeError: If JSON file is malformed
    """
    path = Path(config_path)

    if not path.exists():
        # Return defaults if config doesn't exist
        settings = Settings()
        settings.validate()
        return settings

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Map JSON keys to ProxySettings fields
    # Maintains compatibility with old config format (uppercase keys)
    proxy_data = {
        'listen_port': data.get('LISTEN_PORT', 8888),
        'date': data.get('DATE', '20011025'),
        'date_tolerance': data.get('DATE_TOLERANCE', 365),
        'wayback_api': data.get('WAYBACK_API', False),
        'quick_images': data.get('QUICK_IMAGES', True),
        'geocities_fix': data.get('GEOCITIES_FIX', True),
        'content_type_encoding': data.get('CONTENT_TYPE_ENCODING', True),
        'settings_page': data.get('SETTINGS_PAGE', True),
        'silent': data.get('SILENT', False),
    }

    # Map hardware settings if present (optional section)
    hardware_data = {}
    if 'HARDWARE' in data:
        hw = data['HARDWARE']
        hardware_data = {
            'display_type': hw.get('display_type', 'lcd'),
            'input_method': hw.get('input_method', 'rotary'),
            'gpio_clk': hw.get('gpio_clk', 26),
            'gpio_dt': hw.get('gpio_dt', 19),
            'gpio_button': hw.get('gpio_button', 13),
        }

    # Create settings with loaded data
    settings = Settings(
        proxy=ProxySettings(**proxy_data),
        hardware=HardwareSettings(**hardware_data) if hardware_data else HardwareSettings()
    )

    # Validate configuration
    settings.validate()

    return settings


def save_config(settings: Settings, config_path: str = "config.json") -> None:
    """Save configuration to JSON file.

    Args:
        settings: Settings object to save
        config_path: Path to configuration file (default: config.json)
    """
    settings.validate()

    data = {
        'LISTEN_PORT': settings.proxy.listen_port,
        'DATE': settings.proxy.date,
        'DATE_TOLERANCE': settings.proxy.date_tolerance,
        'WAYBACK_API': settings.proxy.wayback_api,
        'QUICK_IMAGES': settings.proxy.quick_images,
        'GEOCITIES_FIX': settings.proxy.geocities_fix,
        'CONTENT_TYPE_ENCODING': settings.proxy.content_type_encoding,
        'SETTINGS_PAGE': settings.proxy.settings_page,
        'SILENT': settings.proxy.silent,
        'HARDWARE': {
            'display_type': settings.hardware.display_type,
            'input_method': settings.hardware.input_method,
            'gpio_clk': settings.hardware.gpio_clk,
            'gpio_dt': settings.hardware.gpio_dt,
            'gpio_button': settings.hardware.gpio_button,
        }
    }

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
