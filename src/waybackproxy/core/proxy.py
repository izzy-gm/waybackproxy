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

"""HTTP proxy server with threading support."""
from __future__ import annotations

import socketserver
from typing import Type


class ThreadedProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Multi-threaded TCP server for HTTP proxy requests.

    Attributes:
        allow_reuse_address: Prevents 'Address already in use' errors on restart
        daemon_threads: Ensures clean shutdown of worker threads
    """

    allow_reuse_address = True
    daemon_threads = True
