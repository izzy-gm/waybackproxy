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

"""Input device implementations and adapters."""
from __future__ import annotations

import subprocess
import sys
import termios
import threading
import tty
from typing import Callable, Optional

from ..hardware.base import InputDevice
from ..hardware.gpio import RotaryEncoder


class RotaryEncoderInput(InputDevice):
    """Rotary encoder input adapter.

    Wraps hardware.gpio.RotaryEncoder with InputDevice interface.
    """

    def __init__(self, gpio_clk: int, gpio_dt: int, gpio_button: int):
        """Initialize rotary encoder input.

        Args:
            gpio_clk: GPIO pin for encoder CLK (BCM numbering)
            gpio_dt: GPIO pin for encoder DT (BCM numbering)
            gpio_button: GPIO pin for push button (BCM numbering)
        """
        self.gpio_clk = gpio_clk
        self.gpio_dt = gpio_dt
        self.gpio_button = gpio_button
        self._encoder: Optional[RotaryEncoder] = None
        self._rotate_callback: Optional[Callable[[int], None]] = None
        self._button_callback: Optional[Callable[[], None]] = None

    def on_rotate(self, callback: Callable[[int], None]) -> None:
        """Register callback for rotation events.

        Args:
            callback: Function called with rotation delta (-1 or +1)
        """
        self._rotate_callback = callback

    def on_button_press(self, callback: Callable[[], None]) -> None:
        """Register callback for button press events.

        Args:
            callback: Function called when button is pressed
        """
        self._button_callback = callback

    def start(self) -> None:
        """Start listening for input events."""
        if self._encoder is not None:
            return  # Already started

        self._encoder = RotaryEncoder(
            gpioA=self.gpio_clk,
            gpioB=self.gpio_dt,
            callback=self._rotate_callback,
            buttonPin=self.gpio_button,
            buttonCallback=self._button_callback
        )

    def stop(self) -> None:
        """Stop listening and cleanup resources."""
        if self._encoder:
            self._encoder.destroy()
            self._encoder = None


class KeyboardInput(InputDevice):
    """Keyboard input for development/testing.

    Maps arrow keys to rotary encoder-like events:
    - Left/Right arrows: Rotation events (-1/+1)
    - Up arrow: Button press
    - Esc: Exit (calls on_exit callback if set)

    Runs in a background thread to avoid blocking.
    """

    def __init__(self):
        """Initialize keyboard input."""
        self._rotate_callback: Optional[Callable[[int], None]] = None
        self._button_callback: Optional[Callable[[], None]] = None
        self._exit_callback: Optional[Callable[[], None]] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._old_settings: Optional[list] = None

    def on_rotate(self, callback: Callable[[int], None]) -> None:
        """Register callback for rotation events.

        Args:
            callback: Function called with rotation delta (-1 or +1)
        """
        self._rotate_callback = callback

    def on_button_press(self, callback: Callable[[], None]) -> None:
        """Register callback for button press events.

        Args:
            callback: Function called when button is pressed
        """
        self._button_callback = callback

    def on_exit(self, callback: Callable[[], None]) -> None:
        """Register callback for exit event (Esc key).

        Args:
            callback: Function called when Esc is pressed
        """
        self._exit_callback = callback

    def start(self) -> None:
        """Start listening for keyboard input.

        Runs keyboard capture in background thread.
        """
        if self._thread is not None:
            return  # Already started

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._key_loop,
            name="KeyboardInput",
            daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop listening and cleanup resources."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

        # Restore terminal settings
        self._restore_terminal()

    def _restore_terminal(self) -> None:
        """Restore terminal to sane settings."""
        if self._old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
                self._old_settings = None
            except Exception:
                pass

        # Restore sane terminal using subprocess
        try:
            subprocess.run(['stty', 'sane'], check=False, timeout=1.0)
        except Exception:
            pass

    def _get_key(self) -> Optional[str]:
        """Get single keypress from stdin.

        Returns:
            Key name ('up', 'down', 'left', 'right', 'esc') or character
            None if interrupted or no input
        """
        try:
            # Read up to 3 bytes (for escape sequences)
            import os
            b = os.read(sys.stdin.fileno(), 3).decode()

            # Parse key code
            if len(b) == 3:
                k = ord(b[2])  # Escape sequence: \x1b[A etc.
            else:
                k = ord(b)

            # Map key codes to names
            key_mapping = {
                27: 'esc',
                65: 'up',
                66: 'down',
                67: 'right',
                68: 'left'
            }

            return key_mapping.get(k, chr(k))

        except Exception:
            return None

    def _key_loop(self) -> None:
        """Main keyboard capture loop.

        Runs in background thread, processes key presses until stopped.
        """
        # Save terminal settings
        self._old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Set terminal to cbreak mode (no line buffering)
            tty.setcbreak(sys.stdin.fileno())

            while not self._stop_event.is_set():
                try:
                    key = self._get_key()

                    if key == 'up' and self._button_callback:
                        self._button_callback()
                    elif key == 'left' and self._rotate_callback:
                        self._rotate_callback(-1)
                    elif key == 'right' and self._rotate_callback:
                        self._rotate_callback(1)
                    elif key == 'esc':
                        if self._exit_callback:
                            self._exit_callback()
                        break  # Exit loop on Esc

                except KeyboardInterrupt:
                    break

        finally:
            # Restore terminal settings
            self._restore_terminal()
