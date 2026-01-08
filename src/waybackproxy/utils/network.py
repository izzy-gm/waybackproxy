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

"""Network utility functions."""
from __future__ import annotations

import socket
import time
from typing import Optional

import requests


def get_local_ip() -> str:
    """Get local IP address of this machine.

    Returns:
        Local IP address as string (fallback to '127.0.0.1' if unavailable)

    Examples:
        >>> ip = get_local_ip()
        >>> print(f"Server running on {ip}:8888")
        Server running on 192.168.1.100:8888

    Note:
        This uses a trick of connecting to a non-routable address to determine
        the local IP. No actual network traffic is sent.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0)
    try:
        # Connect to non-routable address (doesn't need to be reachable)
        sock.connect(('10.254.254.254', 1))
        ip_address = sock.getsockname()[0]
    except Exception:
        ip_address = '127.0.0.1'
    finally:
        sock.close()
    return ip_address


def wait_for_network(
    timeout_s: float = 60.0,
    poll_period_s: float = 0.5,
    test_url: str = "http://www.google.com/"
) -> bool:
    """Wait for network connectivity.

    Args:
        timeout_s: Maximum time to wait in seconds
        poll_period_s: Time between connection attempts
        test_url: URL to test connectivity

    Returns:
        True if network is available, False if timeout

    Examples:
        >>> # Wait up to 60 seconds for network
        >>> if wait_for_network():
        ...     print("Network ready")
        ... else:
        ...     print("Network unavailable")
    """
    start_time = time.time()

    while time.time() - start_time < timeout_s:
        try:
            # Try to reach test URL
            requests.head(test_url, timeout=poll_period_s)
            return True
        except requests.ConnectionError:
            # Network not ready, wait and retry
            time.sleep(poll_period_s)
        except requests.Timeout:
            # Timeout on request, but network might be up
            return True
        except Exception:
            # Other errors, wait and retry
            time.sleep(poll_period_s)

    return False


def check_port_available(port: int, host: str = '0.0.0.0') -> bool:
    """Check if a port is available for binding.

    Args:
        port: Port number to check
        host: Host address (default: 0.0.0.0)

    Returns:
        True if port is available, False if in use

    Examples:
        >>> if check_port_available(8888):
        ...     print("Port 8888 is available")
        ... else:
        ...     print("Port 8888 is in use")
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False
