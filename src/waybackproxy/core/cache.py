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

"""Connection pooling and caching for proxy requests."""
from __future__ import annotations

import urllib3
from pathlib import Path

from ..utils.lru import LRUDict


class SharedState:
    """Shared state across request handlers.

    Manages:
    - HTTP connection pool
    - Date availability cache
    - URL redirect cache
    - Domain whitelist
    """

    def __init__(self):
        """Initialize shared state with connection pool and caches."""
        # Create urllib3 connection pool optimized for asset-heavy pages
        # Increased from 16 to 64 to handle concurrent image requests
        # Archive.org is slow, so we need many parallel connections
        self.http = urllib3.PoolManager(
            maxsize=64,              # Total connections across all hosts
            block=True,              # Block when pool exhausted (respects rate limits)
            num_pools=10,            # Max distinct host connection pools
            timeout=urllib3.Timeout(connect=10.0, read=60.0),  # Default timeouts
            retries=False            # Disable default retries (handler controls retry logic)
        )
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Create internal LRU dictionary for preserving URLs on redirect
        # 24 hour TTL for URL->date mappings
        self.date_cache = LRUDict(maxduration=86400, maxsize=1024)

        # Create internal LRU dictionary for date availability
        # 24 hour TTL for Wayback API responses
        self.availability_cache = LRUDict(maxduration=86400, maxsize=1024)

        # Domain whitelist (loaded separately)
        self.whitelist: list[str] = []

    def load_whitelist(self, path: str = 'whitelist.txt') -> None:
        """Load domain whitelist from file.

        Args:
            path: Path to whitelist file (default: whitelist.txt)
        """
        try:
            whitelist_path = Path(path)
            if whitelist_path.exists():
                with open(whitelist_path, 'r') as f:
                    self.whitelist = f.read().splitlines()
            else:
                self.whitelist = []
        except Exception:
            self.whitelist = []
