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

"""Display device factory and utilities."""
from __future__ import annotations

from typing import Literal

from .base import Display
from .lcd import LCD1602Display, TerminalDisplay

DisplayType = Literal["lcd", "terminal"]


def create_display(
    display_type: DisplayType,
    cols: int = 16,
    rows: int = 2
) -> Display:
    """Create a display device based on configuration.

    Args:
        display_type: Type of display ("lcd" or "terminal")
        cols: Number of columns (default: 16)
        rows: Number of rows (default: 2)

    Returns:
        Display instance

    Raises:
        ValueError: If display_type is not recognized

    Examples:
        >>> # Create LCD hardware display
        >>> display = create_display("lcd")
        >>> display.write("Hello World", line=0)
        >>> display.set_color(0, 255, 0)  # Green backlight

        >>> # Create terminal display for testing
        >>> display = create_display("terminal")
        >>> display.write("Testing", line=0)
    """
    if display_type == "lcd":
        return LCD1602Display(cols=cols, rows=rows)
    elif display_type == "terminal":
        return TerminalDisplay(cols=cols, rows=rows)
    else:
        raise ValueError(
            f"Unknown display type: {display_type}. "
            f"Must be 'lcd' or 'terminal'"
        )
