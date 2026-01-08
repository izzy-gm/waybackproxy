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

"""Centralized logging configuration.

Replaces scattered print() calls with proper logging infrastructure.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    silent: bool = False
) -> None:
    """Configure application logging.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional log file path
        silent: If True, suppress all logging output

    Examples:
        >>> # Basic setup
        >>> setup_logging()

        >>> # Debug mode with file logging
        >>> setup_logging(level=logging.DEBUG, log_file="wayback.log")

        >>> # Silent mode (warnings only)
        >>> setup_logging(silent=True)
    """
    if silent:
        level = logging.WARNING

    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter(
            fmt='[%(levelname)s] %(name)s: %(message)s'
        )
    )
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting proxy server")
        >>> logger.warning("Connection timeout")
        >>> logger.error("Failed to load config")
    """
    return logging.getLogger(name)
