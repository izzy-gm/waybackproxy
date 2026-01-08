# Copyright (C) 2024-2026 Izzy Graniel
# Portions Copyright (C) Waveshare (LCD1602 RGB Module demo code)
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
#
# This file includes code from Waveshare LCD1602 RGB Module demo:
# https://files.waveshare.com/upload/5/5b/LCD1602-RGB-Module-demo.zip

"""LCD1602 RGB display driver for I2C interface.

Supports Grove RGB LCD 1602 v4.0 and compatible displays.
"""
from __future__ import annotations

import time
from typing import Union

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus  # type: ignore

from .base import Display

# I2C addresses (7-bit)
LCD_ADDRESS = 0x7c >> 1  # 0x3E
RGB_ADDRESS = 0xc0 >> 1  # 0x60

# RGB backlight registers
REG_RED = 0x04
REG_GREEN = 0x03
REG_BLUE = 0x02
REG_MODE1 = 0x00
REG_MODE2 = 0x01
REG_OUTPUT = 0x08

# LCD commands
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_SETCGRAMADDR = 0x40
LCD_SETDDRAMADDR = 0x80

# Display entry mode flags
LCD_ENTRYRIGHT = 0x00
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTINCREMENT = 0x01
LCD_ENTRYSHIFTDECREMENT = 0x00

# Display on/off control flags
LCD_DISPLAYON = 0x04
LCD_DISPLAYOFF = 0x00
LCD_CURSORON = 0x02
LCD_CURSOROFF = 0x00
LCD_BLINKON = 0x01
LCD_BLINKOFF = 0x00

# Display/cursor shift flags
LCD_DISPLAYMOVE = 0x08
LCD_CURSORMOVE = 0x00
LCD_MOVERIGHT = 0x04
LCD_MOVELEFT = 0x00

# Function set flags
LCD_8BITMODE = 0x10
LCD_4BITMODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x8DOTS = 0x00


class LCD1602Display(Display):
    """Grove RGB LCD 1602 display driver.

    16 columns × 2 rows character LCD with RGB backlight.
    Communicates over I2C bus using two addresses:
    - 0x3E for LCD control
    - 0x60 for RGB backlight
    """

    def __init__(self, cols: int = 16, rows: int = 2, bus: int = 1):
        """Initialize LCD display.

        Args:
            cols: Number of columns (default: 16)
            rows: Number of rows (default: 2)
            bus: I2C bus number (default: 1 for Raspberry Pi)

        Raises:
            IOError: If I2C communication fails
        """
        self._cols = cols
        self._rows = rows
        self._bus = SMBus(bus)

        # Display state
        self._showfunction = LCD_4BITMODE | LCD_1LINE | LCD_5x8DOTS
        self._showcontrol = 0
        self._showmode = 0
        self._numlines = 0
        self._currline = 0

        # Initialize display
        self._begin(self._rows, self._cols)

    def _command(self, cmd: int) -> None:
        """Send command to LCD.

        Args:
            cmd: Command byte
        """
        self._bus.write_byte_data(LCD_ADDRESS, 0x80, cmd)

    def _write_char(self, data: int) -> None:
        """Write character data to LCD.

        Args:
            data: Character byte
        """
        self._bus.write_byte_data(LCD_ADDRESS, 0x40, data)

    def _set_reg(self, reg: int, data: int) -> None:
        """Set RGB backlight register.

        Args:
            reg: Register address
            data: Register value
        """
        self._bus.write_byte_data(RGB_ADDRESS, reg, data)

    def _begin(self, cols: int, lines: int) -> None:
        """Initialize LCD hardware.

        Args:
            cols: Number of columns
            lines: Number of rows
        """
        if lines > 1:
            self._showfunction |= LCD_2LINE

        self._numlines = lines
        self._currline = 0

        time.sleep(0.05)

        # Send function set command sequence (HD44780 initialization)
        self._command(LCD_FUNCTIONSET | self._showfunction)
        time.sleep(0.005)
        self._command(LCD_FUNCTIONSET | self._showfunction)
        time.sleep(0.005)
        self._command(LCD_FUNCTIONSET | self._showfunction)
        self._command(LCD_FUNCTIONSET | self._showfunction)

        # Turn on display with no cursor or blinking
        self._showcontrol = LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF
        self._display_on()

        # Clear display
        self.clear()

        # Set text direction (left-to-right)
        self._showmode = LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT
        self._command(LCD_ENTRYMODESET | self._showmode)

        # Initialize RGB backlight controller
        self._set_reg(REG_MODE1, 0)
        self._set_reg(REG_OUTPUT, 0xFF)  # LEDs controllable by PWM
        self._set_reg(REG_MODE2, 0x20)   # Blink mode

        # Set default white backlight
        self.set_color(255, 255, 255)

    def _display_on(self) -> None:
        """Turn display on."""
        self._showcontrol |= LCD_DISPLAYON
        self._command(LCD_DISPLAYCONTROL | self._showcontrol)

    def _set_cursor(self, col: int, row: int) -> None:
        """Set cursor position.

        Args:
            col: Column (0-15)
            row: Row (0-1)
        """
        if row == 0:
            col |= 0x80
        else:
            col |= 0xc0
        self._command(col)

    def write(self, text: str, line: int = 0, column: int = 0) -> None:
        """Write text at specified position.

        Args:
            text: Text to display (will be truncated to fit)
            line: Line number (0-1)
            column: Column number (0-15)
        """
        # Clamp to valid positions
        line = max(0, min(line, self._rows - 1))
        column = max(0, min(column, self._cols - 1))

        # Set cursor position
        self._set_cursor(column, line)

        # Write text, truncate if too long
        max_length = self._cols - column
        text = text[:max_length]

        # Convert to bytes and write
        for char in bytearray(text, 'utf-8'):
            self._write_char(char)

    def clear(self) -> None:
        """Clear the entire display."""
        self._command(LCD_CLEARDISPLAY)
        time.sleep(0.002)  # Clear command takes longer

    def set_color(self, r: int, g: int, b: int) -> None:
        """Set RGB backlight color.

        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
        """
        # Clamp values to 0-255
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        self._set_reg(REG_RED, r)
        self._set_reg(REG_GREEN, g)
        self._set_reg(REG_BLUE, b)

    def get_dimensions(self) -> tuple[int, int]:
        """Get display dimensions.

        Returns:
            Tuple of (columns, rows)
        """
        return (self._cols, self._rows)

    def printout(self, text: Union[str, int]) -> None:
        """Print text at current cursor position.

        Compatibility method for old RGB1602 API.

        Args:
            text: Text or number to display
        """
        if isinstance(text, int):
            text = str(text)

        for char in bytearray(text, 'utf-8'):
            self._write_char(char)


class TerminalDisplay(Display):
    """Terminal-based display for development/debugging.

    Simulates LCD display using console output.
    Useful for testing without hardware.
    """

    def __init__(self, cols: int = 16, rows: int = 2):
        """Initialize terminal display.

        Args:
            cols: Number of columns to simulate
            rows: Number of rows to simulate
        """
        self._cols = cols
        self._rows = rows
        self._buffer = [[' ' for _ in range(cols)] for _ in range(rows)]

    def write(self, text: str, line: int = 0, column: int = 0) -> None:
        """Write text at specified position.

        Args:
            text: Text to display
            line: Line number (0-indexed)
            column: Column number (0-indexed)
        """
        if 0 <= line < self._rows:
            for i, char in enumerate(text):
                col = column + i
                if col >= self._cols:
                    break
                self._buffer[line][col] = char
            self._render()

    def clear(self) -> None:
        """Clear the display."""
        self._buffer = [[' ' for _ in range(self._cols)] for _ in range(self._rows)]
        self._render()

    def set_color(self, r: int, g: int, b: int) -> None:
        """Set color (no-op for terminal).

        Args:
            r: Red component (ignored)
            g: Green component (ignored)
            b: Blue component (ignored)
        """
        pass  # Terminal doesn't support RGB backlight

    def get_dimensions(self) -> tuple[int, int]:
        """Get display dimensions.

        Returns:
            Tuple of (columns, rows)
        """
        return (self._cols, self._rows)

    def _render(self) -> None:
        """Render buffer to terminal."""
        print("\n" + "=" * (self._cols + 4))
        for row in self._buffer:
            print("| " + "".join(row) + " |")
        print("=" * (self._cols + 4) + "\n")
