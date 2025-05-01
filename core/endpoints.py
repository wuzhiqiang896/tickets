from urllib.parse import urljoin, urlencode
from config.settings import settings

# CRITICAL: These paths MUST be verified by inspecting network traffic
# Use f-strings or .format() if paths depend on dynamic data like IDs

BASE_URL = str(settings.network.base_url)

def home():
    return BASE_URL + "/"

def login_action():
    # Verify this path! Likely POST
    return urljoin(BASE_URL, "/member/login/web/login_process.htm")

def performance_page(prod_id: str, lang_cd: str):
    params = {'langCd': lang_cd, 'prodId': prod_id}
    return urljoin(BASE_URL, f"/performance/index.htm?{urlencode(params)}")

def booking_initiation():
    # Verify! Might need prodId, scheduleId etc. in query or POST data
    # This often triggers the popup/seat selection page/iframe
    return urljoin(BASE_URL, "/ticket/onestop/popup/onestop.htm") # Highly likely placeholder

def captcha_image():
    # Verify! Might have cache-busting query params
    return urljoin(BASE_URL, "/comm/captcha/captchaImg.do") # Placeholder

def captcha_submit_and_seat_query():
     # Verify! This might be the request after entering CAPTCHA to load seats
     # Could be the same as booking_step_submit or a separate step.
     return urljoin(BASE_URL, "/ticket/booking/bookingGate.json") # Highly likely placeholder

def seat_selection_action():
     # Verify! The request to lock/select seats. Payload is critical.
     return urljoin(BASE_URL, "/ticket/booking/selectSeat.json") # Highly likely placeholder

def booking_details_submit():
    # Verify! Submits ticket count, user info, agreements, payment method
    return urljoin(BASE_URL, "/ticket/booking/bookingAction.json") # Highly likely placeholder

def final_payment_action():
     # Verify! The final confirmation before payment gateway
     return urljoin(BASE_URL, "/ticket/payment/paymentAction.json") # Highly likely placeholder

# Add more endpoints as discovered...