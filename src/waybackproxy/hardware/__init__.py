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

"""Hardware abstraction layer for Raspberry Pi components."""
from __future__ import annotations

from .base import Display, InputDevice
from .display import DisplayType, create_display
from .gpio import RotaryEncoder
from .lcd import LCD1602Display, TerminalDisplay

__all__ = [
    # Abstract interfaces
    "Display",
    "InputDevice",
    # Display implementations
    "LCD1602Display",
    "TerminalDisplay",
    "DisplayType",
    "create_display",
    # GPIO implementations
    "RotaryEncoder",
]
