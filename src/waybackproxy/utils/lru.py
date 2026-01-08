# Copyright (C) 2024-2026 Izzy Graniel
# Based on ActiveState Code Recipe 580644 (LRU Dictionary)
# http://code.activestate.com/recipes/580644-lru-dictionary/
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

"""LRU Dictionary implementation with time-based expiration.

Based on: http://code.activestate.com/recipes/580644-lru-dictionary/
"""
from __future__ import annotations

import collections
import time
from typing import Any, Iterator, Optional


class LRUDict(collections.OrderedDict):
	"""A dict that can discard least-recently-used items.

	Supports both maximum capacity and time-to-live expiration.
	An item's TTL is refreshed (aka the item is considered "used") by direct access
	via [] or get() only, not via iterating over the whole collection with items().

	Expired entries only get purged after insertions or changes. Either call purge()
	manually or check an item's ttl with ttl() if that's unacceptable.
	"""

	def __init__(self, *args, maxduration: Optional[int] = None, maxsize: int = 128, **kwargs):
		'''Same arguments as OrderedDict with these 2 additions:
		maxduration: number of seconds entries are kept. 0 or None means no timelimit.
		maxsize: maximum number of entries being kept.'''
		super().__init__(*args, **kwargs)
		self.maxduration = maxduration
		self.maxsize = maxsize
		self.purge()

	def purge(self):
		"""Removes expired or overflowing entries."""
		if self.maxsize:
			# pop until maximum capacity is reached
			overflowing = max(0, len(self) - self.maxsize)
			for _ in range(overflowing):
				self.popitem(last=False)
		if self.maxduration:
			# expiration limit
			limit = time.time() - self.maxduration
			# as long as there are still items in the dictionary
			while self:
				# look at the oldest (front)
				_, lru = next(iter(super().values()))
				# if it is within the timelimit, we're fine
				if lru > limit:
					break
				# otherwise continue to pop the front
				self.popitem(last=False)

	def __getitem__(self, key):
		# retrieve item
		value = super().__getitem__(key)[0]
		# update lru time
		super().__setitem__(key, (value, time.time()))
		self.move_to_end(key)
		return value

	def get(self, key, default=None):
		try:
			return self[key]
		except KeyError:
			return default

	def ttl(self, key):
		'''Returns the number of seconds this item will live.
		The item might still be deleted if maxsize is reached.
		The time to live can be negative, as for expired items
		that have not been purged yet.'''
		if self.maxduration:
			lru = super().__getitem__(key)[1]
			return self.maxduration - (time.time() - lru)

	def __setitem__(self, key, value):
		super().__setitem__(key, (value, time.time()))
		self.purge()

	def items(self):
		# remove ttl from values
		return ((k, v) for k, (v, _) in super().items())

	def values(self):
		# remove ttl from values
		return (v for v, _ in super().values())
