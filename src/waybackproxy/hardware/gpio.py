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

"""GPIO handling for Raspberry Pi hardware.

Uses lgpio backend for compatibility with Raspberry Pi OS Trixie (Debian 13).
"""
from __future__ import annotations

import os
from typing import Callable, Optional

# Use lgpio backend for compatibility with Raspberry Pi OS Trixie and newer
os.environ['GPIOZERO_PIN_FACTORY'] = 'lgpio'

try:
    import RPi.GPIO as GPIO
except ImportError:
    # Fall back to lgpio-based GPIO
    try:
        from RPi import GPIO
    except ImportError:
        raise ImportError(
            "RPi.GPIO not found. Install with: pip install rpi-lgpio"
        )


class RotaryEncoder:
    """Rotary encoder interface using RPi.GPIO.

    Decodes mechanical rotary encoder pulses and button presses.

    Attributes:
        gpioA: GPIO pin for encoder channel A
        gpioB: GPIO pin for encoder channel B
        gpioButton: Optional GPIO pin for push button
    """

    def __init__(
        self,
        gpioA: int,
        gpioB: int,
        callback: Optional[Callable[[int], None]] = None,
        buttonPin: Optional[int] = None,
        buttonCallback: Optional[Callable[[], None]] = None,
        onExitCallback: Optional[Callable[[], None]] = None
    ):
        """Initialize rotary encoder.

        Args:
            gpioA: GPIO pin number for channel A (BCM numbering)
            gpioB: GPIO pin number for channel B (BCM numbering)
            callback: Function called when encoder rotates, receives delta (-1 or +1)
            buttonPin: Optional GPIO pin for push button (BCM numbering)
            buttonCallback: Function called when button is pressed
            onExitCallback: Function called on cleanup (deprecated, not used)

        Raises:
            PermissionError: If user lacks GPIO access permissions
            RuntimeError: If GPIO pins cannot be initialized
        """
        self.lastGpio: Optional[int] = None
        self.gpioA = gpioA
        self.gpioB = gpioB
        self.callback = callback
        self.gpioButton = buttonPin
        self.buttonCallback = buttonCallback
        self.onExitCallback = onExitCallback
        self.levA = 0
        self.levB = 0
        self.bouncetime = 1  # ms debounce time

        # Clean up any existing GPIO state before initializing
        # This prevents "Failed to add edge detection" errors on restart
        try:
            GPIO.cleanup()
        except RuntimeWarning:
            pass  # Ignore "no channels set up" warning
        except Exception as e:
            print(f"Warning during GPIO cleanup: {e}")

        # Check GPIO access permissions
        if not os.access('/dev/gpiomem', os.R_OK | os.W_OK):
            raise PermissionError(
                "No access to /dev/gpiomem. "
                "User must be in 'gpio' group and have proper permissions. "
                "Run: sudo usermod -a -G gpio $(whoami) && sudo reboot"
            )

        # Set BCM pin numbering mode
        GPIO.setmode(GPIO.BCM)

        # Set up encoder GPIO pins with pull-up resistors
        try:
            GPIO.setup(self.gpioA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.gpioB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception as e:
            raise RuntimeError(
                f"Failed to set up GPIO pins {self.gpioA}, {self.gpioB}: {e}"
            )

        # Add event detection for encoder pins with retry logic
        self._setup_event_detection(
            self.gpioA, GPIO.RISING, self._callback, self.bouncetime
        )
        self._setup_event_detection(
            self.gpioB, GPIO.FALLING, self._callback, self.bouncetime
        )

        # Set up optional button
        if self.gpioButton:
            try:
                GPIO.setup(self.gpioButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self._setup_event_detection(
                    self.gpioButton, GPIO.FALLING, self._buttonCallback, 200
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to set up button GPIO pin {self.gpioButton}: {e}"
                )

    def _setup_event_detection(
        self,
        gpio: int,
        edge: int,
        callback: Callable[[int], None],
        bouncetime: int
    ) -> None:
        """Set up event detection with retry logic.

        Args:
            gpio: GPIO pin number
            edge: GPIO.RISING or GPIO.FALLING
            callback: Callback function
            bouncetime: Debounce time in milliseconds
        """
        try:
            GPIO.add_event_detect(gpio, edge, callback, bouncetime)
        except RuntimeError:
            # Try to clean up the specific pin and retry
            try:
                GPIO.remove_event_detect(gpio)
            except Exception:
                pass
            GPIO.add_event_detect(gpio, edge, callback, bouncetime)

    def destroy(self) -> None:
        """Clean up GPIO resources.

        Removes event detection and releases GPIO pins.
        Call this before program exit.
        """
        try:
            GPIO.remove_event_detect(self.gpioA)
            GPIO.remove_event_detect(self.gpioB)
            if self.gpioButton:
                GPIO.remove_event_detect(self.gpioButton)
            GPIO.cleanup()
        except Exception as e:
            print(f"Warning during GPIO cleanup: {e}")

    def _buttonCallback(self, channel: int) -> None:
        """Internal callback for button press events.

        Args:
            channel: GPIO pin that triggered the event
        """
        if self.buttonCallback:
            self.buttonCallback()

    def _callback(self, channel: int) -> None:
        """Internal callback for encoder rotation events.

        Implements quadrature decoding:
        - When both channels are high, determine direction based on which was set last
        - Channel A high last = forward rotation (+1)
        - Channel B high last = reverse rotation (-1)

        Args:
            channel: GPIO pin that triggered the event
        """
        level = GPIO.input(channel)

        # Update channel levels
        if channel == self.gpioA:
            self.levA = level
        else:
            self.levB = level

        # Debounce: ignore repeated triggers from same pin
        if channel == self.lastGpio:
            return

        self.lastGpio = channel

        # Fire callback when both inputs are high
        if channel == self.gpioA and level == 1:
            if self.levB == 1 and self.callback:
                self.callback(1)  # Forward rotation
        elif channel == self.gpioB and level == 1:
            if self.levA == 1 and self.callback:
                self.callback(-1)  # Reverse rotation
