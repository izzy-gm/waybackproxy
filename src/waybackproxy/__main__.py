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

"""Command-line entry point for WaybackProxy.

Usage:
    python -m waybackproxy [--config CONFIG] [--headless] [--debug]
    waybackproxy [--config CONFIG] [--headless] [--debug]
"""
from __future__ import annotations

import argparse
import sys
import threading

from .config.loader import load_config
from .core.cache import SharedState
from .core import handler as handler_module
from .core.handler import Handler
from .core.proxy import ThreadedProxyServer
from .hardware.display import create_display
from .ui.controller import UIController
from .ui.date_selector import DateSelector
from .ui.input import KeyboardInput, RotaryEncoderInput
from .utils.logging import get_logger, setup_logging
from .utils.network import get_local_ip, wait_for_network


def main() -> int:
    """Main entry point for WaybackProxy.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="WaybackProxy - Time-traveling HTTP proxy for Internet Archive",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Configuration file path (default: config.json)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without UI (proxy only mode)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    try:
        # Load configuration
        settings = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1

    # Setup logging
    import logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level, silent=settings.proxy.silent)

    logger = get_logger(__name__)
    logger.info(f"WaybackProxy starting on port {settings.proxy.listen_port}")

    # Initialize shared state
    shared_state = SharedState()
    shared_state.load_whitelist()

    # Configure handler module with settings
    # Set module-level globals used throughout the handler
    handler_module.LISTEN_PORT = settings.proxy.listen_port
    handler_module.DATE_TOLERANCE = settings.proxy.date_tolerance
    handler_module.GEOCITIES_FIX = settings.proxy.geocities_fix
    handler_module.QUICK_IMAGES = settings.proxy.quick_images
    handler_module.WAYBACK_API = settings.proxy.wayback_api
    handler_module.CONTENT_TYPE_ENCODING = settings.proxy.content_type_encoding
    handler_module.SETTINGS_PAGE = settings.proxy.settings_page
    handler_module.SILENT = settings.proxy.silent

    # Set class attribute for DATE (accessed as self.DATE in handler)
    Handler.DATE = settings.proxy.date
    # Set shared_state reference
    handler_module.shared_state = shared_state

    # Start proxy server in background thread
    try:
        server = ThreadedProxyServer(
            ('', settings.proxy.listen_port),
            Handler
        )
    except OSError as e:
        logger.error(f"Failed to start server on port {settings.proxy.listen_port}: {e}")
        return 1

    proxy_thread = threading.Thread(
        name='WaybackProxy',
        target=server.serve_forever,
        daemon=True
    )
    proxy_thread.start()
    logger.info(f"Proxy server listening on port {settings.proxy.listen_port}")

    if args.headless:
        # Headless mode - just keep proxy running
        logger.info("Running in headless mode (no UI)")
        try:
            proxy_thread.join()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            server.shutdown()
        return 0

    # Start UI
    try:
        # Create display
        display = create_display(settings.hardware.display_type)

        # Create input device
        if settings.hardware.input_method == "rotary":
            input_device = RotaryEncoderInput(
                gpio_clk=settings.hardware.gpio_clk,
                gpio_dt=settings.hardware.gpio_dt,
                gpio_button=settings.hardware.gpio_button
            )
        else:  # keyboard
            input_device = KeyboardInput()

        # Create date selector
        date_selector = DateSelector(initial_date=settings.proxy.date)

        # Date change callback
        def on_date_change(new_date: str) -> None:
            """Update proxy handler when date changes."""
            Handler.DATE = new_date
            # Clear caches to ensure consistent behavior with new date
            shared_state.date_cache.clear()
            shared_state.availability_cache.clear()
            logger.debug(f"Date changed to: {new_date}")

        # Create UI controller
        ui = UIController(
            input_device=input_device,
            display=display,
            date_selector=date_selector,
            on_date_change=on_date_change
        )

        # Store UI controller reference for web interface sync
        handler_module.ui_controller = ui

        # Wait for network connectivity
        logger.info("Waiting for network connectivity...")
        display.write("Starting up...", line=0)
        display.write("                ", line=1)

        if wait_for_network(timeout_s=60.0):
            logger.info("Network ready")
        else:
            logger.warning("Network unavailable, continuing anyway")

        # Get IP address for display
        ip_address = get_local_ip()
        logger.info(f"Local IP: {ip_address}")

        # Start UI (blocking)
        ui.start(
            ip_address=ip_address,
            port=settings.proxy.listen_port,
            animate_lcd=(settings.hardware.display_type == "lcd")
        )

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error in UI: {e}", exc_info=True)
        return 1
    finally:
        server.shutdown()
        if 'display' in locals():
            display.clear()

    return 0


if __name__ == "__main__":
    sys.exit(main())
