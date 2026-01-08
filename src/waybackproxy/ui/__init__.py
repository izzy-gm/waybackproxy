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

"""User interface components."""
from __future__ import annotations

from .controller import SimpleUIController, UIController
from .date_selector import DateSelection, DateSelector, Segment
from .input import KeyboardInput, RotaryEncoderInput

__all__ = [
    # Controllers
    "UIController",
    "SimpleUIController",
    # Date selection
    "DateSelector",
    "DateSelection",
    "Segment",
    # Input devices
    "RotaryEncoderInput",
    "KeyboardInput",
]
