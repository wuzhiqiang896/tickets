import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import pytz
import json # Added

from config.settings import settings
from .session_manager import SessionManager
from . import endpoints, parser, exceptions
from services.captcha.base import CaptchaSolver, CaptchaType, CaptchaSolution # Added Solution
from services.captcha.api_solver import TwoCaptchaSolver
from strategies.seat_selection.base import SeatSelector, SeatSelectionResult
from strategies.seat_selection.api_selector import ApiSeatSelector
from strategies.seat_selection.zone_selector import ZoneSeatSelector
from strategies.seat_selection.manual_selector import ManualSeatSelector
# Import time utils correctly
from utils.time_utils import get_tz_aware_datetime, wait_until_target


class MelonClient:
    # ... (init, _get_captcha_solver, _get_seat_selector as before) ...

    async def login(self) -> bool:
         # ... (Implementation as before, ensure LoginError raised on fail) ...
         # Consider adding a check for specific login success elements if needed
         if not self.is_logged_in: # Check state after attempt
              raise exceptions.LoginError("Login attempt finished but client state not logged in.")
         return self.is_logged_in

    async def initiate_booking(self) -> str:
        # ... (Implementation as before, ensure BookingError/SoldOutError raised on fail) ...
        # Ensure dynamic data extraction happens here if needed for subsequent steps
        # e.g., self.dynamic_data['booking_csrf'] = parser.extract_csrf_token(response.text, 'bookingForm')
        return response.text

    async def handle_captcha(self, page_content: str) -> Optional[CaptchaSolution]: # Return Solution obj
         self.logger.info("Checking for CAPTCHA...")
         captcha_type = CaptchaType.NONE
         captcha_params = {}
         client = await self.session_manager.get_client() # Get client to access headers

         # --- CAPTCHA Detection Logic (CRITICAL - Needs specific implementation) ---
         # This needs to be adapted based on how Melon presents CAPTCHAs

         # Example: Simple Image CAPTCHA Detection
         if '<img id="captchaImg"' in page_content or 'id="captcha_img"' in page_content: # Check variations
              captcha_type = CaptchaType.IMAGE
              # CRITICAL: Verify the actual image URL endpoint
              img_url = endpoints.captcha_image() # May need dynamic params based on page content
              self.logger.info(f"Image CAPTCHA detected. Fetching image from {img_url}")
              try:
                   # Use send_request for retries etc.
                   img_response = await self.session_manager.send_request('GET', img_url)
                   img_response.raise_for_status() # Ensure image was fetched
                   if 'image' not in img_response.headers.get('Content-Type','').lower():
                       raise exceptions.CaptchaError(f"Expected image content type, got {img_response.headers.get('Content-Type')}")
                   captcha_params['image_bytes'] = img_response.content
                   self.logger.debug(f"CAPTCHA Image fetched ({len(img_response.content)} bytes).")
              except Exception as e:
                   raise exceptions.CaptchaError(f"Failed to fetch CAPTCHA image from {img_url}: {e}")

         # Example: reCAPTCHA v2 Detection
         # elif 'class="g-recaptcha"' in page_content:
         #      captcha_type = CaptchaType.RECAPTCHA_V2
         #      try:
         #           site_key = parser.extract_recaptcha_site_key(page_content) # Implement parser
         #           if not site_key: raise ValueError("Could not find reCAPTCHA site key")
         #           captcha_params['site_key'] = site_key
         #           captcha_params['page_url'] = str(client.headers.get('Referer', '')) # Get current URL
         #           self.logger.info(f"reCAPTCHA v2 detected. Site Key: {site_key}")
         #      except Exception as e:
         #           raise exceptions.CaptchaError(f"Failed to extract reCAPTCHA details: {e}")

         # --- End Detection Logic ---

         if captcha_type == CaptchaType.NONE:
              self.logger.info("No CAPTCHA detected.")
              return None

         try:
              self.logger.info(f"Solving {captcha_type.name} CAPTCHA...")
              solution = await self.captcha_solver.solve(captcha_type, **captcha_params)
              self.logger.info(f"CAPTCHA solved: ID {solution.captcha_id} | Solution: {solution.code[:15]}...")
              # Store solution code specifically for the payload
              self.dynamic_data['captcha_solution_code'] = solution.code
              return solution # Return the full solution object
         except Exception as e:
              self.logger.error(f"CAPTCHA solving failed: {e}")
              # Don't raise CaptchaError directly here, let the caller decide if it's fatal
              # Return None or re-raise specific errors from solver if needed
              raise exceptions.CaptchaError(f"CAPTCHA solving failed: {e}") from e # Re-raise for now

    async def select_seats(self) -> SeatSelectionResult:
         # ... (Implementation as before, ensure SeatSelectionError raised on fail) ...
         if not result or not result.success:
             # Log details from result if available
             err_msg = result.message if result else "Seat selection strategy indicated failure."
             self.logger.error(f"Seat selection failed: {err_msg}")
             raise exceptions.SeatSelectionError(err_msg, result=result)
         # Ensure payload is stored
         if not result.payload_data:
              self.logger.warning("Seat selection succeeded but returned no payload_data. Submission might fail.")
              # Decide if this is an error state
              # raise exceptions.SeatSelectionError("Seat selection missing payload data.")
         self.dynamic_data['seat_selection_payload'] = result.payload_data or {}
         self.dynamic_data['selected_seat_ids'] = result.selected_seat_ids or []
         return result

    async def submit_booking(self) -> bool:
         # ... (Payload construction as before) ...
         payload = {
             # --- Base Info ---
             'prodId': settings.target_event.performance_id,
             'scheduleNo': settings.target_event.target_schedule_id, # Ensure this is valid
             'ticketNum': settings.target_event.num_tickets,
             # --- User Details (Verify if needed/prefilled) ---
             # 'tel': settings.credentials.username,
             # 'email': settings.credentials.username,
             # 'birthday': 'YYYYMMDD', # Add if required
             # 'sex': 'M'/'F',         # Add if required
             # --- Agreements (Verify value) ---
             'chkAgreeAll': 'on',
             # --- Payment (Verify code) ---
             'payMethodCode': '002',
             # --- Dynamic Data ---
             'captchaText': self.dynamic_data.get('captcha_solution_code'), # Key name might differ
             # ** Merge seat selection payload **
             **(self.dynamic_data.get('seat_selection_payload', {})),
             # ** Add other dynamic fields like CSRF tokens **
             # 'csrf_token': self.dynamic_data.get('booking_csrf'),
         }
         payload = {k: v for k, v in payload.items() if v is not None} # Clean None values
         self.logger.debug(f"Booking submission payload: {json.dumps(payload)}") # Use json.dumps for logging dict

         # ... (Rest of the submission logic and validation as before) ...
         # Ensure specific errors (CaptchaError, SeatSelectionError) are raised on failure
         return True # Return True on success


    async def run_booking_flow(self):
        """Executes the complete booking sequence."""
        start_time = datetime.now()
        try:
            # 1. Login
            if not await self.login():
                 # Login method should raise LoginError on failure
                 return

            # 2. Wait for Sale Time
            target_dt = self.get_target_datetime() # Use synchronous helper
            await wait_until_target(target_dt, buffer_seconds=settings.time.wait_buffer_seconds)

            # --- Core Booking Sequence ---
            booking_start_time = datetime.now()
            self.logger.info(f"Target time reached, starting core booking sequence at {booking_start_time.isoformat()}")

            # 3. Initiate Booking (Get booking page/popup content)
            page_content = await self.initiate_booking()

            # 4. Handle CAPTCHA (if present on the page)
            captcha_solution = await self.handle_captcha(page_content)
            # Pass captcha solution if needed by seat selector? Some sites require it before showing seats.
            seat_selector_kwargs = {'captcha_solution': captcha_solution} if captcha_solution else {}

            # 5. Select Seats
            await self.select_seats(**seat_selector_kwargs)

            # 6. Submit Final Booking
            await self.submit_booking()

            booking_end_time = datetime.now()
            duration = (booking_end_time - booking_start_time).total_seconds()
            self.logger.info("="*20 + " BOOKING PROCESS COMPLETED SUCCESSFULLY! " + "="*20)
            self.logger.info(f"Core booking duration: {duration:.3f} seconds")
            print("\n>>> Booking successful! Check your Melon account. Manual payment might be needed. <<<")

        except exceptions.SoldOutError as e:
             self.logger.warning(f"Booking flow stopped: Tickets Sold Out. ({e})")
             print(f"\n--- Booking Failed: Tickets Sold Out ---")
        except (exceptions.LoginError, exceptions.BookingError, exceptions.CaptchaError,
                exceptions.SeatSelectionError) as e:
            self.logger.error(f"Booking flow failed: {type(e).__name__} - {e}")
            print(f"\n--- Booking Failed: {e} ---")
        except Exception as e:
            self.logger.exception(f"An unexpected error stopped the booking flow: {e}")
            print(f"\n--- An Unexpected Error Occurred: {e} ---")
        finally:
            await self.session_manager.close()
            total_duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Bot run finished. Total duration: {total_duration:.3f} seconds.")

    # Make this synchronous as it only uses config
    def get_target_datetime(self) -> datetime:
         """Parses the target sale time string into a timezone-aware datetime object."""
         try:
             return get_tz_aware_datetime(
                 settings.time.sell_time_str,
                 settings.time.timezone
             )
         except ValueError as e:
              self.logger.error(f"Fatal: Could not parse target datetime from config: {e}")
              raise SystemExit(f"Invalid time configuration: {e}")


    # Removed wait_for_sale - now called directly from run_booking_flow using utils