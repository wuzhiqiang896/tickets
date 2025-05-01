import asyncio
from typing import Any
# Use actual library if available, e.g.: from twocaptcha import TwoCaptcha
# Mocking the library for now
class MockTwoCaptcha:
     def __init__(self, apiKey): self.apiKey = apiKey
     def normal(self, file, **kwargs):
          print(f"[Mock 2Captcha] Solving image CAPTCHA with args: {kwargs}")
          # Simulate API call time
          # time.sleep(5) # Don't use time.sleep in async!
          print("[Mock 2Captcha] Solved image.")
          return {'code': 'MOCKIMG123', 'captchaId': 'mock_img_id_123'}
     def recaptcha(self, sitekey, url, **kwargs):
          print(f"[Mock 2Captcha] Solving reCAPTCHA for sitekey {sitekey} on {url} with args: {kwargs}")
          # Simulate API call time
          # time.sleep(15) # Don't use time.sleep in async!
          print("[Mock 2Captcha] Solved reCAPTCHA.")
          return {'code': 'MOCK_RECAPTCHA_TOKEN_abc...', 'captchaId': 'mock_recaptcha_id_456'}

from .base import CaptchaSolver, CaptchaSolution, CaptchaType
from config.settings import settings
import logging

class TwoCaptchaSolver(CaptchaSolver):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = settings.captcha.api_key.get_secret_value()
        if not self.api_key:
            raise ValueError("2Captcha API key not configured")
        # Replace MockTwoCaptcha with the actual library instance
        self.solver = MockTwoCaptcha(apiKey=self.api_key)
        # self.solver = TwoCaptcha(self.api_key) # Use actual library
        self.logger.info("Initialized 2Captcha Solver (Using Mock)") # Change if using real lib

    async def solve(self, captcha_type: CaptchaType, **kwargs) -> CaptchaSolution:
        """Solves a CAPTCHA using the 2Captcha service."""
        loop = asyncio.get_running_loop()

        try:
            if captcha_type == CaptchaType.IMAGE:
                image_bytes = kwargs.get('image_bytes')
                if not image_bytes: raise ValueError("Missing 'image_bytes' for IMAGE captcha")
                self.logger.info("Solving image CAPTCHA using 2Captcha...")
                # Wrap synchronous library call in executor
                result = await loop.run_in_executor(
                    None, # Default executor
                    lambda: self.solver.normal(file=image_bytes, **kwargs) # Pass extra args if any
                )

            elif captcha_type == CaptchaType.RECAPTCHA_V2:
                site_key = kwargs.get('site_key')
                page_url = kwargs.get('page_url')
                if not site_key or not page_url:
                    raise ValueError("Missing 'site_key' or 'page_url' for RECAPTCHA_V2")
                self.logger.info("Solving reCAPTCHA v2 using 2Captcha...")
                result = await loop.run_in_executor(
                     None,
                     lambda: self.solver.recaptcha(sitekey=site_key, url=page_url, **kwargs)
                )
            # Add elif blocks for HCAPTCHA, RECAPTCHA_V3 etc.
            else:
                raise NotImplementedError(f"2Captcha solver does not support {captcha_type.name}")

            if not result or 'code' not in result:
                 raise ConnectionError("2Captcha API returned an invalid response.")

            solution_code = result['code']
            captcha_id = result.get('captchaId')
            self.logger.info(f"2Captcha solution received: ID {captcha_id} Code: {solution_code[:10]}...")
            return CaptchaSolution(code=solution_code, captcha_id=captcha_id)

        except Exception as e:
            self.logger.error(f"2Captcha solving failed for {captcha_type.name}: {e}")
            # Consider reporting bad CAPTCHAs if applicable
            raise ConnectionError(f"2Captcha API error: {e}") from e