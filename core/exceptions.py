class MelonBotError(Exception):
    """Base exception for the Melon Ticket Bot."""
    pass

class ConfigError(MelonBotError):
    """Error related to configuration loading or validation."""
    pass

class NetworkError(MelonBotError):
    """Error related to network requests (excluding HTTP status errors handled elsewhere)."""
    pass

class LoginError(MelonBotError):
    """Error specifically during the login process."""
    pass

class BookingError(MelonBotError):
    """General error during the booking flow after login."""
    pass

class SoldOutError(BookingError):
    """Error indicating tickets are likely sold out."""
    pass

class CaptchaError(MelonBotError):
    """Error related to fetching or solving CAPTCHAs."""
    pass

class SeatSelectionError(BookingError):
    """Error during the seat selection phase."""
    def __init__(self, message, result=None):
        super().__init__(message)
        self.result = result # Optional: Attach SeatSelectionResult

class ParsingError(MelonBotError):
    """Error during HTML/JSON parsing."""
    pass