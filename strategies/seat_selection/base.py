from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

# Forward declaration for type hint in methods
if False:
     from core.client import MelonClient

@dataclass
class SeatSelectionResult:
    """Represents the outcome of a seat selection attempt."""
    success: bool
    selected_seat_ids: List[str] = field(default_factory=list)
    # Optional: Store other relevant data extracted/used during selection
    message: Optional[str] = None # E.g., error message if success is False
    payload_data: Optional[Dict[str, Any]] = None # Data structure needed for booking submission payload

class SeatSelector(ABC):
    """Abstract base class for different seat selection strategies."""

    @abstractmethod
    async def select_seats(self, client: 'MelonClient', **kwargs) -> SeatSelectionResult:
        """
        Attempts to select the required number of seats using a specific strategy.

        Args:
            client: The active MelonClient instance, providing access to the
                    session manager for making necessary API calls.
            **kwargs: Strategy-specific parameters (e.g., CAPTCHA solution if needed
                      before querying seats).

        Returns:
            A SeatSelectionResult object indicating success/failure and details.

        Raises:
            SeatSelectionError: For strategy-specific failures.
            NetworkError: For underlying network issues during API calls.
        """
        pass