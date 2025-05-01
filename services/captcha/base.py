from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass

class CaptchaType(Enum):
    NONE = auto()
    IMAGE = auto()
    RECAPTCHA_V2 = auto()
    RECAPTCHA_V3 = auto()
    HCAPTCHA = auto()
    # Add other types as needed

@dataclass
class CaptchaSolution:
    """Represents the result from a CAPTCHA solver."""
    code: str # The solution string (e.g., text from image, token from reCAPTCHA)
    captcha_id: str | None = None # Optional ID returned by the solving service

class CaptchaSolver(ABC):
    """Abstract base class for CAPTCHA solving services."""

    @abstractmethod
    async def solve(self, captcha_type: CaptchaType, **kwargs) -> CaptchaSolution:
        """
        Solves a CAPTCHA of the specified type.

        Args:
            captcha_type: The type of CAPTCHA to solve.
            **kwargs: Service-specific parameters needed for solving, e.g.:
                      - image_bytes: bytes (for IMAGE)
                      - site_key: str (for RECAPTCHA_V2, HCAPTCHA)
                      - page_url: str (for RECAPTCHA_V2, HCAPTCHA)
                      - action: str (for RECAPTCHA_V3)
                      - min_score: float (for RECAPTCHA_V3)

        Returns:
            A CaptchaSolution object containing the solution code.

        Raises:
            NotImplementedError: If the solver doesn't support the captcha_type.
            ConnectionError: If there's an issue communicating with the service.
            ValueError: If required parameters are missing.
            Exception: For other solver-specific errors.
        """
        pass

    # Optional: Method to report incorrect CAPTCHAs back to the service
    # async def report_incorrect(self, captcha_id: str):
    #     pass