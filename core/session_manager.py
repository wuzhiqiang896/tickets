import httpx
from config.settings import settings
import logging
from typing import Optional, Dict, Any

class SessionManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Returns the active httpx AsyncClient, creating it if necessary."""
        if self._client is None or self._client.is_closed:
            self.logger.info("Initializing new httpx AsyncClient...")
            headers = {
                'User-Agent': settings.network.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8', # Adjust as needed
                'Referer': str(settings.network.base_url), # Start with base URL
            }
            proxies = self._get_proxy_config()
            timeout = httpx.Timeout(settings.network.request_timeout, connect=10.0) # Separate connect timeout
            limits = httpx.Limits(max_connections=100, max_keepalive_connections=20) # Default limits

            # Enable HTTP/2 if desired/supported by server
            transport = httpx.AsyncHTTPTransport(retries=0, http2=True, limits=limits) # Retries handled manually

            self._client = httpx.AsyncClient(
                headers=headers,
                proxies=proxies,
                timeout=timeout,
                follow_redirects=True,
                transport=transport,
                # cookies can be managed implicitly or explicitly if needed
            )
            self.logger.info(f"AsyncClient initialized. Proxies {'enabled' if proxies else 'disabled'}.")
        return self._client

    def _get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Constructs proxy dictionary for httpx if enabled."""
        if settings.proxy.enabled and settings.proxy.url:
            proxy_url_str = settings.proxy.url.get_secret_value()
            self.logger.debug(f"Using proxy: {proxy_url_str[:15]}...") # Log partially
            return {"http://": proxy_url_str, "https://": proxy_url_str}
        return None

    async def update_headers(self, new_headers: Dict[str, str]):
        """Updates headers in the current client."""
        client = await self.get_client()
        client.headers.update(new_headers)
        self.logger.debug(f"Updated client headers: {new_headers}")

    async def close(self):
        """Closes the httpx client if it exists."""
        if self._client and not self._client.is_closed:
            self.logger.info("Closing httpx AsyncClient...")
            await self._client.aclose()
            self._client = None
            self.logger.info("AsyncClient closed.")

    async def send_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Sends a request using the managed client with retry logic."""
        client = await self.get_client()
        last_exception = None
        for attempt in range(settings.network.retry_attempts + 1):
            try:
                self.logger.debug(f"Request Attempt {attempt+1}/{settings.network.retry_attempts + 1}: {method} {url}")
                response = await client.request(method, url, **kwargs)
                # Maybe raise for status here or let caller handle
                # response.raise_for_status()
                self.logger.debug(f"Response: {response.status_code} {url}")
                # Update Referer for next request based on final URL after redirects
                await self.update_headers({'Referer': str(response.url)})
                return response
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                self.logger.warning(f"Request failed (Attempt {attempt+1}): {e}")
                last_exception = e
                if attempt < settings.network.retry_attempts:
                    delay = settings.network.retry_delay_seconds * (2 ** attempt) # Exponential backoff
                    self.logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                     self.logger.error(f"Max retries reached for {method} {url}")
                     raise last_exception # Re-raise the last exception

        # Should not be reached if retries > 0, but satisfy type checker
        raise last_exception if last_exception else RuntimeError("Request failed unexpectedly")

# ... (rest of the class as provided previously) ...

    async def send_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Sends a request using the managed client with retry logic."""
        client = await self.get_client()
        last_exception = None
        # Ensure max_attempts is calculated correctly
        max_attempts = settings.network.retry_attempts + 1

        for attempt in range(max_attempts):
            try:
                self.logger.debug(f"Request Attempt {attempt+1}/{max_attempts}: {method} {url}")
                # Ensure kwargs like 'data' or 'json' are handled correctly
                response = await client.request(method, url, **kwargs)

                # Optional: Raise immediately for specific client errors (4xx)
                # if 400 <= response.status_code < 500:
                #     response.raise_for_status() # Let specific handlers deal with 4xx logic

                # Raise for server errors (5xx) to trigger retry
                if response.status_code >= 500:
                     response.raise_for_status()

                self.logger.debug(f"Response: {response.status_code} {url}")
                # Update Referer based on the final URL after potential redirects
                if 'Referer' in client.headers: # Only update if it exists
                    await self.update_headers({'Referer': str(response.url)})
                return response
            except httpx.HTTPStatusError as e:
                 # Only retry on server errors (5xx) by default
                if e.response.status_code >= 500 and attempt < settings.network.retry_attempts:
                     self.logger.warning(f"Server error {e.response.status_code} (Attempt {attempt+1}). Retrying...")
                     last_exception = e
                else:
                     self.logger.error(f"HTTP Error {e.response.status_code} on {method} {url}. No more retries or non-retriable status.")
                     raise # Re-raise the status error for the caller to handle
            except httpx.RequestError as e:
                # Network errors (timeout, connection error, etc.) are retriable
                self.logger.warning(f"Request failed (Attempt {attempt+1}): {e}")
                last_exception = e
            except Exception as e:
                 # Catch unexpected errors during request
                 self.logger.exception(f"Unexpected error during request {method} {url} (Attempt {attempt+1}): {e}")
                 last_exception = e
                 # Maybe don't retry unexpected errors? Or retry cautiously.
                 # For now, let retry logic proceed.

            # If we are here, an exception occurred and we might retry
            if attempt < settings.network.retry_attempts:
                delay = settings.network.retry_delay_seconds * (2 ** attempt) # Exponential backoff
                self.logger.info(f"Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)

        # If loop finishes without returning, raise the last known exception
        self.logger.error(f"Max retries ({settings.network.retry_attempts}) reached for {method} {url}")
        raise last_exception if last_exception else NetworkError(f"Request failed after {max_attempts} attempts without specific exception.")