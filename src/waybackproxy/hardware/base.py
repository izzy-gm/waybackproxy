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

"""Abstract base classes for hardware components."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class InputDevice(ABC):
    """Abstract input device interface.

    Supports rotation events (encoder, arrow keys) and button presses.
    Implementations: RotaryEncoderInput, KeyboardInput
    """

    @abstractmethod
    def on_rotate(self, callback: Callable[[int], None]) -> None:
        """Register callback for rotation events.

        Args:
            callback: Function called with rotation delta (-1 or +1)
        """
        ...

    @abstractmethod
    def on_button_press(self, callback: Callable[[], None]) -> None:
        """Register callback for button press events.

        Args:
            callback: Function called when button is pressed
        """
        ...

    @abstractmethod
    def start(self) -> None:
        """Start listening for input events."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop listening and cleanup resources."""
        ...


class Display(ABC):
    """Abstract display device interface.

    Supports text output and color control.
    Implementations: LCD1602Display, TerminalDisplay
    """

    @abstractmethod
    def write(self, text: str, line: int = 0, column: int = 0) -> None:
        """Write text at specified position.

        Args:
            text: Text to display
            line: Line number (0-indexed)
            column: Column number (0-indexed)
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear the entire display."""
        ...

    @abstractmethod
    def set_color(self, r: int, g: int, b: int) -> None:
        """Set backlight/text color.

        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)

        Note:
            Terminal implementations may ignore this or use ANSI colors
        """
        ...

    @abstractmethod
    def get_dimensions(self) -> tuple[int, int]:
        """Get display dimensions.

        Returns:
            Tuple of (columns, rows)
        """
        ...
