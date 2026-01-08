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

"""Main UI controller coordinating input and display."""
from __future__ import annotations

import math
import threading
import time
from queue import Queue
from typing import Callable, Optional

from ..hardware.base import Display, InputDevice
from .date_selector import DateSelector


class UIController:
    """Coordinates UI components (input, display, date selection).

    Replaces the monolithic init.py main loop with a cleaner architecture.

    Attributes:
        input_device: Input device (rotary encoder or keyboard)
        display: Display device (LCD or terminal)
        date_selector: Date selection manager
        on_date_change: Callback when date changes
    """

    def __init__(
        self,
        input_device: InputDevice,
        display: Display,
        date_selector: DateSelector,
        on_date_change: Callable[[str], None]
    ):
        """Initialize UI controller.

        Args:
            input_device: Input device for user interaction
            display: Display device for output
            date_selector: Date selection manager
            on_date_change: Callback called when date changes with new date string
        """
        self.input_device = input_device
        self.display = display
        self.date_selector = date_selector
        self.on_date_change = on_date_change

        # Event queue for input events
        self._queue: Queue[int] = Queue()
        self._event = threading.Event()
        self._shutdown_event = threading.Event()

        # Display animation state
        self._message_cycle = 0
        self._message_index = 0
        self._color_phase = 0

    def start(
        self,
        ip_address: str = "127.0.0.1",
        port: int = 8888,
        animate_lcd: bool = True
    ) -> None:
        """Start the UI event loop.

        Args:
            ip_address: IP address to display
            port: Port number to display
            animate_lcd: Enable LCD message rotation and color animation

        Note:
            This is a blocking call that runs until stopped.
        """
        # Setup input callbacks
        self._setup_input_callbacks()

        # Start input device
        self.input_device.start()

        # Clear display and show initial state
        self.display.clear()
        cols, rows = self.display.get_dimensions()

        # Show initial date
        self._update_display_date()

        # Messages for LCD rotation
        ip_and_port = f"{ip_address}:{port}"
        messages = [
            "Select a date   ",
            "in the past     ",
            "Push to change  ",
            "between Y/M/D   ",
            f"{ip_and_port:<16}",
            "WaybackMachine  ",
            "by Iz           ",
            "       ;)       "
        ]

        # Main event loop
        MESSAGE_CHANGE_CYCLES = 130
        try:
            while not self._shutdown_event.is_set():
                # Process input queue
                self._consume_queue()
                self._event.clear()

                if animate_lcd:
                    # Cycle messages on line 0
                    self._message_cycle += 1
                    if self._message_cycle >= MESSAGE_CHANGE_CYCLES:
                        self._message_cycle = 0
                        self.display.write(messages[self._message_index], line=0)
                        self._message_index = (self._message_index + 1) % len(messages)

                    # Animate RGB backlight
                    r = int(abs(math.sin(math.pi * self._color_phase / 180)) * 255)
                    g = int(abs(math.sin(math.pi * (self._color_phase + 60) / 180)) * 255)
                    b = int(abs(math.sin(math.pi * (self._color_phase + 120) / 180)) * 255)
                    self._color_phase += 1
                    self.display.set_color(r, g, b)

                    # Animation speed
                    time.sleep(0.02)
                else:
                    # No animation, just wait for input
                    time.sleep(0.1)

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Gracefully shutdown UI."""
        self._shutdown_event.set()
        self.input_device.stop()
        self.display.clear()

    def _setup_input_callbacks(self) -> None:
        """Setup input device callbacks."""
        self.input_device.on_rotate(self._on_turn)
        self.input_device.on_button_press(self._on_press)

    def _on_turn(self, delta: int) -> None:
        """Handle rotation events.

        Args:
            delta: Rotation direction (-1 or +1)
        """
        self._queue.put(delta)
        self._event.set()

    def _on_press(self) -> None:
        """Handle button press events."""
        # Toggle between Y/M/D
        self.date_selector.toggle_segment()
        self._update_display_date()

    def _consume_queue(self) -> None:
        """Process all pending input events from queue."""
        while not self._queue.empty():
            delta = self._queue.get()
            self._handle_delta(delta)

    def _handle_delta(self, delta: int) -> None:
        """Handle a single rotation delta.

        Args:
            delta: Rotation direction (-1 or +1)
        """
        if delta > 0:
            self.date_selector.increment()
        else:
            self.date_selector.decrement()

        self._update_display_date()

    def _update_display_date(self) -> None:
        """Update display with current date and notify callback."""
        # Get formatted date string
        display_str = self.date_selector.get_display_string()

        # Update display (line 1)
        self.display.write(display_str, line=1)

        # Notify callback of date change
        wayback_date = self.date_selector.get_wayback_date()
        self.on_date_change(wayback_date)

    def update_date_from_external(self, new_date: str) -> None:
        """Update date from external source (e.g., web interface).

        This method allows the date to be changed programmatically without
        triggering the on_date_change callback (to avoid circular updates).

        Args:
            new_date: Date in YYYYMMDD format
        """
        # Update date selector
        self.date_selector.set_date(new_date)

        # Update display without calling the callback
        display_str = self.date_selector.get_display_string()
        self.display.write(display_str, line=1)


class SimpleUIController:
    """Simplified UI controller without animations.

    For headless or terminal-only operation.
    """

    def __init__(
        self,
        input_device: InputDevice,
        display: Display,
        date_selector: DateSelector,
        on_date_change: Callable[[str], None]
    ):
        """Initialize simple UI controller.

        Args:
            input_device: Input device for user interaction
            display: Display device for output
            date_selector: Date selection manager
            on_date_change: Callback called when date changes
        """
        self.input_device = input_device
        self.display = display
        self.date_selector = date_selector
        self.on_date_change = on_date_change
        self._shutdown_event = threading.Event()

    def start(self) -> None:
        """Start the UI.

        Note:
            This is a blocking call that runs until stopped.
        """
        # Setup and start input
        self.input_device.on_rotate(self._on_turn)
        self.input_device.on_button_press(self._on_press)
        self.input_device.start()

        # Show initial date
        self.display.clear()
        self._update_display()

        # Wait for shutdown
        try:
            self._shutdown_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Gracefully shutdown UI."""
        self._shutdown_event.set()
        self.input_device.stop()
        self.display.clear()

    def _on_turn(self, delta: int) -> None:
        """Handle rotation events.

        Args:
            delta: Rotation direction (-1 or +1)
        """
        if delta > 0:
            self.date_selector.increment()
        else:
            self.date_selector.decrement()
        self._update_display()

    def _on_press(self) -> None:
        """Handle button press events."""
        self.date_selector.toggle_segment()
        self._update_display()

    def _update_display(self) -> None:
        """Update display with current date."""
        display_str = self.date_selector.get_display_string()
        self.display.write(display_str, line=0)

        wayback_date = self.date_selector.get_wayback_date()
        self.on_date_change(wayback_date)
