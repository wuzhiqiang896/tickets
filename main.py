import asyncio
import logging
import sys
import os

# Set environment variable for easier debugging if needed
# os.environ['LOGURU_DEBUG'] = '1' # Example

# Setup logging ASAP
from utils.logging_setup import setup_logging
setup_logging() # Use default levels defined in the function

# Now import other modules after logging is set up
from core.client import MelonClient
from config.settings import settings # To log some config info

async def run_bot():
    """Initializes and runs the MelonClient."""
    logger = logging.getLogger("main") # Use Loguru's getLogger adaptation
    logger.info("Initializing Melon Ticket Bot...")
    try:
        # Log some non-sensitive config details
        logger.info(f"Target Performance ID: {settings.target_event.performance_id}")
        logger.info(f"Sale Time ({settings.time.timezone}): {settings.time.sell_time_str}")
        logger.info(f"Seat Strategy: {settings.target_event.seat_selection_strategy}")
        logger.info(f"User: {settings.credentials.username}")
        logger.info(f"Proxy Enabled: {settings.proxy.enabled}")
    except Exception as e:
         logger.critical(f"Failed to access loaded settings: {e}")
         return # Exit if settings are broken

    client = MelonClient()
    await client.run_booking_flow()
    logger.info("Melon Ticket Bot run complete.")

if __name__ == "__main__":
    main_logger = logging.getLogger("main")
    try:
        # Handle potential asyncio loop policy issues on Windows
        if sys.platform == "win32":
             # SelectorEventLoop is generally recommended over ProactorEventLoop for libraries like httpx
             # asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
             main_logger.debug("Set Windows asyncio event loop policy to Selector.")

        asyncio.run(run_bot())

    except KeyboardInterrupt:
        main_logger.warning("Process interrupted by user.")
    except SystemExit as e:
         # Config errors should already be logged, just note the exit
         main_logger.warning(f"Exiting due to configuration or critical error: {e}")
    except Exception as e:
         # Catchall for unexpected errors at the top level
         main_logger.exception(f"Unhandled exception at top level: {e}")
    finally:
         main_logger.info("Application shutting down.")
         # Optional: Keep console open for user review
         # input("Press Enter to exit...")