import logging
import sys
from pathlib import Path
from loguru import logger # Using Loguru for nicer async/file logging

LOGS_DIR = Path(__file__).parent.parent / 'logs' # Place logs directory at project root level

def setup_logging(level="INFO", console_level="INFO", file_level="DEBUG"):
    """Configures Loguru logger."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file_path = LOGS_DIR / "bot_{time:YYYY-MM-DD}.log"

    # Remove default handler
    logger.remove()

    # Add console handler
    logger.add(
        sys.stderr,
        level=console_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )

    # Add file handler
    logger.add(
        log_file_path,
        level=file_level.upper(),
        rotation="1 day",  # New log file daily
        retention="7 days", # Keep logs for 7 days
        compression="zip", # Compress old logs
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
        enqueue=True, # Make logging async-safe
        backtrace=True, # Better tracebacks
        diagnose=True  # Extra diagnostic info on exceptions
    )

    # Configure standard logging to redirect to Loguru
    # This captures logs from libraries like httpx
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True) # Capture all stdlib logs
    logging.getLogger("httpx").setLevel(logging.WARNING) # Silence verbose httpx logs unless needed
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.info(f"Logging setup complete. Console: {console_level}, File: {file_level} ({log_file_path})")