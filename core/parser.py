from bs4 import BeautifulSoup
import json
import re
import logging

logger = logging.getLogger(__name__)

def extract_csrf_token(html_content: str, form_id: str) -> str | None:
    """Extracts CSRF token from a specific form."""
    soup = BeautifulSoup(html_content, 'html.parser')
    form = soup.find('form', {'id': form_id})
    if form:
        token_input = form.find('input', {'name': re.compile(r'csrf_token', re.I)}) # Case-insensitive regex
        if token_input and 'value' in token_input.attrs:
            logger.debug(f"Extracted CSRF token: {token_input['value'][:5]}...")
            return token_input['value']
    logger.warning(f"Could not find CSRF token in form '{form_id}'")
    return None

def find_schedule_id(html_content: str, target_date: str) -> str | None:
    """Finds schedule ID based on date (example logic)."""
    # Needs specific logic based on how schedule IDs are presented in HTML
    # Could be in data attributes, JavaScript variables, etc.
    soup = BeautifulSoup(html_content, 'html.parser')
    # Example: Find a button/link with data-schedule-id for the target date
    # schedule_element = soup.find('a', {'data-date': target_date})
    # if schedule_element and 'data-schedule-id' in schedule_element.attrs:
    #     sched_id = schedule_element['data-schedule-id']
    #     logger.debug(f"Found schedule ID '{sched_id}' for date '{target_date}'")
    #     return sched_id
    logger.warning(f"Could not determine schedule ID for date '{target_date}' - Requires specific parsing logic.")
    return None # Return None if not found

def parse_booking_error(response_content: str | bytes) -> str | None:
    """Tries to find a user-friendly error message from HTML or JSON."""
    try:
        data = json.loads(response_content)
        if isinstance(data, dict) and 'message' in data:
            return data['message']
        elif isinstance(data, dict) and 'error' in data and isinstance(data['error'], dict) and 'message' in data['error']:
             return data['error']['message']
    except json.JSONDecodeError:
        pass # Not JSON, try HTML

    try:
        if isinstance(response_content, bytes):
            response_content = response_content.decode('utf-8', errors='ignore')
        soup = BeautifulSoup(response_content, 'html.parser')
        # Look for common error message elements (adapt selectors!)
        error_el = soup.find(class_=re.compile(r'error|alert|warning', re.I))
        if error_el:
            return error_el.get_text(strip=True)
        # Check for specific known error messages in text
        if "SOLD_OUT" in response_content.upper(): return "Tickets may be sold out."
        if "INVALID_CAPTCHA" in response_content.upper(): return "Invalid CAPTCHA submitted."
        if "SEAT_ALREADY_TAKEN" in response_content.upper(): return "Seat already taken."

    except Exception as e:
        logger.warning(f"Could not parse error message: {e}")

    return "Unknown error occurred."

# Add more parsing functions as needed (e.g., for seat availability data)