import asyncio
from .base import SeatSelector, SeatSelectionResult
from config.settings import settings
import logging

class ManualSeatSelector(SeatSelector):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.target_seats = settings.target_event.preferred_seat_ids or []
        self.num_tickets = settings.target_event.num_tickets

    async def select_seats(self, client: 'MelonClient', **kwargs) -> SeatSelectionResult:
        """Prompts user to input seat IDs."""
        self.logger.info("--- MANUAL SEAT SELECTION REQUIRED ---")
        print("\n" + "="*40)
        print("Please select seats manually in your browser or enter IDs.")
        print(f"Target number of tickets: {self.num_tickets}")
        if self.target_seats:
            print(f"Configured preferred seats: {', '.join(self.target_seats)}")
        print("Enter the chosen Seat IDs separated by commas, then press Enter.")
        print("Example: R-101, R-102")
        print("="*40)

        selected_ids = []
        while len(selected_ids) != self.num_tickets:
            try:
                # Run input in executor to avoid blocking asyncio event loop
                loop = asyncio.get_running_loop()
                input_str = await loop.run_in_executor(None, input, "Enter Seat IDs: ")
                raw_ids = [s.strip() for s in input_str.split(',') if s.strip()]
                if len(raw_ids) != self.num_tickets:
                    print(f"Error: Please enter exactly {self.num_tickets} seat IDs.")
                    continue
                selected_ids = raw_ids
                self.logger.info(f"User entered Seat IDs: {selected_ids}")
            except Exception as e:
                 self.logger.error(f"Error reading manual input: {e}")
                 # Decide how to handle errors - retry or raise?
                 raise RuntimeError("Failed to get manual seat input") from e

        # In a real scenario, you might need additional info like seat grade ID
        # associated with the seat ID, which might require more complex parsing or API calls.
        # This basic version just returns the IDs.
        return SeatSelectionResult(
            success=True,
            selected_seat_ids=selected_ids,
            # Add other relevant data like grade_id, price_id if known/needed
            payload_data={"selectedSeats": [{"seatId": sid} for sid in selected_ids]} # Example payload part
        )