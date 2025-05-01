import httpx
import pytz
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateutil_parser # Avoid name clash with core.parser

logger = logging.getLogger(__name__)

# Use a simple cache for server time to avoid hammering endpoint
_server_time_cache = {"time": None, "fetched_at": None}
_CACHE_EXPIRY_SECONDS = 5 # How long to trust the cached server time

async def get_server_time(url: str = "https://tkglobal.melon.com/", tz_info: pytz.BaseTzInfo = pytz.utc) -> datetime:
    """Gets server time (UTC) using HEAD request, converts to specified timezone."""
    now = datetime.now(timezone.utc)

    # Check cache first
    cached = _server_time_cache.get("time")
    fetched_at = _server_time_cache.get("fetched_at")
    if cached and fetched_at and (now - fetched_at).total_seconds() < _CACHE_EXPIRY_SECONDS:
        logger.debug("Using cached server time.")
        return cached.astimezone(tz_info)

    logger.debug(f"Fetching server time from {url}...")
    try:
        # Use a short timeout for HEAD request
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.head(url)
        response.raise_for_status()
        server_time_str = response.headers.get('Date')
        if not server_time_str:
            logger.warning("Server response did not contain 'Date' header. Falling back to local time.")
            server_time_utc = datetime.now(timezone.utc)
        else:
            server_time_utc = dateutil_parser.parse(server_time_str)
            # Ensure it's timezone-aware (usually is from Date header, but make sure)
            if server_time_utc.tzinfo is None:
                server_time_utc = server_time_utc.replace(tzinfo=timezone.utc)

        # Update cache
        _server_time_cache["time"] = server_time_utc
        _server_time_cache["fetched_at"] = now
        logger.debug(f"Server time fetched: {server_time_utc}")
        return server_time_utc.astimezone(tz_info)

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Error fetching server time: {e}. Falling back to local time.")
        return datetime.now(timezone.utc).astimezone(tz_info)
    except Exception as e:
        logger.exception(f"Unexpected error getting server time: {e}. Falling back to local time.")
        return datetime.now(timezone.utc).astimezone(tz_info)

def get_tz_aware_datetime(datetime_str: str, tz_str: str) -> datetime:
    """Parses a datetime string and makes it timezone-aware."""
    try:
        naive_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        target_tz = pytz.timezone(tz_str)
        aware_dt = target_tz.localize(naive_dt)
        return aware_dt
    except (ValueError, pytz.UnknownTimeZoneError) as e:
        logger.error(f"Error parsing datetime '{datetime_str}' with timezone '{tz_str}': {e}")
        raise ValueError(f"Invalid datetime or timezone: {e}") from e

async def wait_until_target(target_dt: datetime, buffer_seconds: float = 0.1, check_interval: float = 0.05):
    """
    Asynchronously waits until the current server time is very close to the target datetime.

    Args:
        target_dt: The target timezone-aware datetime.
        buffer_seconds: How many seconds *before* the target_dt to stop waiting.
        check_interval: How often to check the time initially (adapts).
    """
    if not target_dt.tzinfo:
        raise ValueError("target_dt must be timezone-aware.")

    target_wait_until = target_dt - timedelta(seconds=buffer_seconds)
    tz = target_dt.tzinfo

    logger.info(f"Waiting until approx {target_wait_until.strftime('%Y-%m-%d %H:%M:%S.%f %Z')} (Target: {target_dt.strftime('%Y-%m-%d %H:%M:%S %Z')})")

    while True:
        # Fetch server time frequently as we get closer
        # Use the target_dt's timezone for comparison
        current_time = await get_server_time(tz_info=tz)
        time_diff_seconds = (target_wait_until - current_time).total_seconds()

        if time_diff_seconds <= 0:
            overshoot = abs(time_diff_seconds)
            if overshoot > buffer_seconds * 2: # Log if we significantly overshot the buffer
                 logger.warning(f"Overshot target wait time by {overshoot:.3f} seconds.")
            else:
                 logger.debug(f"Reached target wait time (overshoot: {overshoot:.3f}s).")
            break

        # Dynamic sleep logic
        if time_diff_seconds > 10:
             sleep_duration = 1.0 # Sleep longer when far away
             if int(time_diff_seconds) % 10 == 0: # Log less frequently
                   logger.info(f"Waiting... {time_diff_seconds:.1f} seconds remaining until wait target.")
        elif time_diff_seconds > 1:
             sleep_duration = 0.1
             logger.info(f"Waiting... {time_diff_seconds:.2f} seconds remaining until wait target.")
        else:
             # Very short sleeps when close, minimum check_interval
             sleep_duration = max(check_interval, min(time_diff_seconds / 3, 0.05)) # Sleep 1/3 remaining, capped
             logger.info(f"Waiting... {time_diff_seconds:.3f} seconds remaining until wait target.")

        await asyncio.sleep(sleep_duration)