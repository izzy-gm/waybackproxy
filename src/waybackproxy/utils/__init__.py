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

"""Utility functions and helpers."""
from __future__ import annotations

from .logging import get_logger, setup_logging
from .lru import LRUDict
from .network import check_port_available, get_local_ip, wait_for_network

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    # Network
    "get_local_ip",
    "wait_for_network",
    "check_port_available",
    # Data structures
    "LRUDict",
]
