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

"""Application settings with validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ProxySettings:
    """Wayback proxy configuration.

    Replaces global variables from config.py and config_handler.py.
    """

    # Server settings
    listen_port: int = 8888

    # Wayback settings
    date: str = "20011025"
    date_tolerance: int = 365
    wayback_api: bool = False
    quick_images: bool = True
    geocities_fix: bool = True

    # HTTP settings
    content_type_encoding: bool = True
    settings_page: bool = True

    # Logging
    silent: bool = False

    def validate(self) -> None:
        """Validate settings values.

        Raises:
            ValueError: If any setting has an invalid value
        """
        if not 1024 <= self.listen_port <= 65535:
            raise ValueError(f"Invalid port: {self.listen_port}. Must be between 1024-65535")

        if not self._is_valid_date_format(self.date):
            raise ValueError(f"Invalid date format: {self.date}. Must be YYYY, YYYYMM, or YYYYMMDD")

        if self.date_tolerance < 0:
            raise ValueError(f"Invalid date_tolerance: {self.date_tolerance}. Must be >= 0")

    @staticmethod
    def _is_valid_date_format(date_str: str) -> bool:
        """Check if date is in YYYY, YYYYMM, or YYYYMMDD format.

        Args:
            date_str: Date string to validate

        Returns:
            True if valid, False otherwise
        """
        if not date_str.isdigit():
            return False

        length = len(date_str)

        # YYYY format
        if length == 4:
            year = int(date_str)
            return 1996 <= year <= datetime.now().year

        # YYYYMM format
        elif length == 6:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            return 1996 <= year <= datetime.now().year and 1 <= month <= 12

        # YYYYMMDD format
        elif length == 8:
            try:
                datetime.strptime(date_str, "%Y%m%d")
                year = int(date_str[:4])
                return 1996 <= year <= datetime.now().year
            except ValueError:
                return False

        return False


@dataclass
class HardwareSettings:
    """Hardware configuration for Raspberry Pi."""

    # Display
    display_type: str = "lcd"  # "lcd" or "terminal"

    # Input
    input_method: str = "rotary"  # "rotary" or "keyboard"

    # GPIO pins (BCM numbering)
    gpio_clk: int = 26
    gpio_dt: int = 19
    gpio_button: int = 13

    def validate(self) -> None:
        """Validate hardware settings.

        Raises:
            ValueError: If any setting has an invalid value
        """
        if self.display_type not in ("lcd", "terminal"):
            raise ValueError(f"Invalid display_type: {self.display_type}. Must be 'lcd' or 'terminal'")

        if self.input_method not in ("rotary", "keyboard"):
            raise ValueError(f"Invalid input_method: {self.input_method}. Must be 'rotary' or 'keyboard'")

        # Validate GPIO pin numbers (BCM mode: 0-27 for Pi 4)
        for pin_name, pin_value in [
            ("gpio_clk", self.gpio_clk),
            ("gpio_dt", self.gpio_dt),
            ("gpio_button", self.gpio_button)
        ]:
            if not 0 <= pin_value <= 27:
                raise ValueError(f"Invalid {pin_name}: {pin_value}. Must be between 0-27 (BCM mode)")


@dataclass
class Settings:
    """Complete application settings."""

    proxy: ProxySettings = field(default_factory=ProxySettings)
    hardware: HardwareSettings = field(default_factory=HardwareSettings)

    def validate(self) -> None:
        """Validate all settings.

        Raises:
            ValueError: If any setting has an invalid value
        """
        self.proxy.validate()
        self.hardware.validate()
