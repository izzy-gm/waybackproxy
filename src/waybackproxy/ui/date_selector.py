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

"""Date selection and formatting logic for Wayback Machine dates."""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date as Date, datetime
from typing import Literal

Segment = Literal["Y", "M", "D"]


@dataclass
class DateSelection:
    """Represents a selected date in Wayback format.

    Attributes:
        year: Year (1996-present)
        month: Month (1-12)
        day: Day (1-31, constrained by month)
    """

    year: int
    month: int
    day: int

    def to_wayback_format(self) -> str:
        """Convert to YYYYMMDD format for Wayback Machine.

        Returns:
            Date string in YYYYMMDD format

        Examples:
            >>> date = DateSelection(2007, 6, 29)
            >>> date.to_wayback_format()
            '20070629'
        """
        return f"{self.year}{self.month:02d}{self.day:02d}"

    def format_display(self, selected_segment: Segment) -> str:
        """Format for display with brackets around selected segment.

        Args:
            selected_segment: Which segment is selected ("Y", "M", or "D")

        Returns:
            Formatted date string with selected segment in brackets

        Examples:
            >>> date = DateSelection(2007, 6, 29)
            >>> date.format_display("Y")
            '[2007]-06-29'
            >>> date.format_display("M")
            '2007-[06]-29'
            >>> date.format_display("D")
            '2007-06-[29]'
        """
        y = str(self.year)
        m = f"{self.month:02d}"
        d = f"{self.day:02d}"

        if selected_segment == "Y":
            return f"[{y}]-{m}-{d}"
        elif selected_segment == "M":
            return f"{y}-[{m}]-{d}"
        else:  # "D"
            return f"{y}-{m}-[{d}]"


class DateSelector:
    """Manages date selection state and operations.

    Replaces DateChanger class with better separation of concerns.
    Handles date validation and constraints for Wayback Machine:
    - Minimum date: 1996-05-10 (first Internet Archive snapshot)
    - Maximum date: Today

    Attributes:
        current: Current date selection
        selected_segment: Which segment is selected ("Y", "M", or "D")
    """

    # Wayback Machine constraints
    MIN_YEAR = 1996
    MIN_MONTH = 5  # May (when year is 1996)
    MIN_DAY = 10   # May 10, 1996 (first snapshot)

    def __init__(self, initial_date: str = "20070629"):
        """Initialize date selector.

        Args:
            initial_date: Initial date in YYYYMMDD format (default: 2007-06-29)

        Raises:
            ValueError: If initial_date is not in valid format
        """
        self.current = self._parse_date(initial_date)
        self.selected_segment: Segment = "Y"

    def _parse_date(self, date_str: str) -> DateSelection:
        """Parse date string to DateSelection.

        Args:
            date_str: Date in YYYYMMDD format

        Returns:
            DateSelection instance

        Raises:
            ValueError: If date format is invalid
        """
        try:
            parsed = datetime.strptime(date_str, "%Y%m%d")
            return DateSelection(
                year=parsed.year,
                month=parsed.month,
                day=parsed.day
            )
        except ValueError as e:
            raise ValueError(f"Invalid date format '{date_str}': {e}")

    def increment(self) -> DateSelection:
        """Increment currently selected segment.

        Returns:
            Updated DateSelection
        """
        return self._change(+1)

    def decrement(self) -> DateSelection:
        """Decrement currently selected segment.

        Returns:
            Updated DateSelection
        """
        return self._change(-1)

    def _change(self, delta: int) -> DateSelection:
        """Change selected segment by delta.

        Args:
            delta: Amount to change (+1 or -1)

        Returns:
            Updated DateSelection
        """
        if self.selected_segment == "Y":
            self.current.year = self._constrain_year(self.current.year + delta)
        elif self.selected_segment == "M":
            self.current.month = self._constrain_month(self.current.month + delta)
        elif self.selected_segment == "D":
            self.current.day = self._constrain_day(self.current.day + delta)

        return self.current

    def toggle_segment(self) -> Segment:
        """Toggle between Y/M/D selection.

        Returns:
            New selected segment

        Examples:
            >>> selector = DateSelector()
            >>> selector.selected_segment
            'Y'
            >>> selector.toggle_segment()
            'M'
            >>> selector.toggle_segment()
            'D'
            >>> selector.toggle_segment()
            'Y'
        """
        if self.selected_segment == "Y":
            self.selected_segment = "M"
        elif self.selected_segment == "M":
            self.selected_segment = "D"
        else:  # "D"
            self.selected_segment = "Y"

        return self.selected_segment

    def get_display_string(self) -> str:
        """Get formatted display string with selected segment highlighted.

        Returns:
            Formatted date string
        """
        return self.current.format_display(self.selected_segment)

    def get_wayback_date(self) -> str:
        """Get current date in Wayback format.

        Returns:
            Date string in YYYYMMDD format
        """
        return self.current.to_wayback_format()

    def set_date(self, date_str: str) -> None:
        """Set date from string.

        Args:
            date_str: Date in YYYYMMDD format

        Raises:
            ValueError: If date format is invalid
        """
        self.current = self._parse_date(date_str)

    def _constrain_year(self, year: int) -> int:
        """Constrain year to valid Wayback range.

        Args:
            year: Year value

        Returns:
            Constrained year (1996 - current year)
        """
        max_year = Date.today().year
        return max(self.MIN_YEAR, min(year, max_year))

    def _constrain_month(self, month: int) -> int:
        """Constrain month to valid range for current year.

        Args:
            month: Month value

        Returns:
            Constrained month (1-12, with additional constraints for MIN/MAX years)
        """
        # Determine valid month range for current year
        if self.current.year == self.MIN_YEAR:
            min_month = self.MIN_MONTH  # May 1996 or later
        else:
            min_month = 1

        if self.current.year == Date.today().year:
            max_month = Date.today().month  # Can't select future months
        else:
            max_month = 12

        return max(min_month, min(month, max_month))

    def _constrain_day(self, day: int) -> int:
        """Constrain day to valid range for current year/month.

        Args:
            day: Day value

        Returns:
            Constrained day (1-31, based on month and year constraints)
        """
        # Determine valid day range for current year/month
        _, max_day_in_month = monthrange(self.current.year, self.current.month)

        # Special case: first Wayback snapshot is May 10, 1996
        if self.current.year == self.MIN_YEAR and self.current.month == self.MIN_MONTH:
            min_day = self.MIN_DAY
        else:
            min_day = 1

        # Can't select future days
        if (self.current.year == Date.today().year and
                self.current.month == Date.today().month):
            max_day = min(max_day_in_month, Date.today().day)
        else:
            max_day = max_day_in_month

        return max(min_day, min(day, max_day))
