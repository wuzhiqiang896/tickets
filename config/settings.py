import yaml
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl, validator, SecretStr, ValidationError
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pytz # Added

# Define paths relative to this file
CONFIG_DIR = Path(__file__).parent.resolve() # Use resolve for absolute path
ROOT_DIR = CONFIG_DIR.parent

# --- Pydantic Models for Validation ---
class TimeSettings(BaseModel):
    timezone: str = 'Asia/Seoul'
    sell_time_str: str # Format: "YYYY-MM-DD HH:MM:SS"
    wait_buffer_seconds: float = Field(0.1, ge=0) # Start slightly before exact time

    @validator('timezone')
    def validate_timezone(cls, v):
        try:
            pytz.timezone(v)
            return v
        except pytz.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone string: {v}")

class TargetEvent(BaseModel):
    performance_id: str
    language_code: str = 'EN'
    target_date: Optional[str] = None # Format: YYYYMMDD (if needed for API)
    target_schedule_id: Optional[str] = None # Often crucial, find via inspect/API
    num_tickets: int = Field(1, gt=0)
    preferred_seat_ids: Optional[List[str]] = None # For Manual/API strategy
    preferred_zone_ids: Optional[List[str]] = None # For Zone strategy
    seat_selection_strategy: str = Field("api", description="'api', 'zone', or 'manual'")

    @validator('seat_selection_strategy')
    def validate_strategy(cls, v):
        allowed = {"api", "zone", "manual"}
        if v.lower() not in allowed:
             raise ValueError(f"seat_selection_strategy must be one of {allowed}")
        return v.lower()

class CaptchaSettings(BaseModel):
    service: str = Field("2captcha", description="Name of CAPTCHA service") # Example
    api_key: SecretStr # Loaded from .env
    # Add other service-specific params if needed, e.g., polling interval

class ProxySettings(BaseModel):
    enabled: bool = True
    url: Optional[SecretStr] = None # Loaded from .env if enabled

class NetworkSettings(BaseModel):
    base_url: HttpUrl
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36' # Example, keep updated
    request_timeout: float = Field(15.0, gt=0)
    retry_attempts: int = Field(3, ge=0)
    retry_delay_seconds: float = Field(1.0, ge=0)

class Credentials(BaseModel):
    username: str # Loaded from .env
    password: SecretStr # Loaded from .env

class Settings(BaseModel):
    credentials: Credentials
    network: NetworkSettings
    time: TimeSettings
    target_event: TargetEvent
    captcha: CaptchaSettings
    proxy: ProxySettings

# --- Loading Logic ---
def load_config() -> Settings:
    """Loads configuration from YAML files and environment variables."""
    # Ensure .env is loaded relative to the root directory if run from elsewhere
    env_path = ROOT_DIR / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded environment variables from: {env_path}")
    else:
        logging.warning(f".env file not found at {env_path}. Relying on system environment variables.")


    logging.info(f"Loading config YAML from: {CONFIG_DIR}")

    try:
        with open(CONFIG_DIR / 'base_config.yaml', 'r') as f:
            base_cfg_data = yaml.safe_load(f) or {}
        with open(CONFIG_DIR / 'target_event.yaml', 'r') as f:
            target_cfg_data = yaml.safe_load(f) or {}

        # Combine configs - target overrides base (deep merge could be better if needed)
        # Simple merge for this structure:
        combined_cfg = {}
        for key in set(base_cfg_data.keys()) | set(target_cfg_data.keys()):
             if isinstance(base_cfg_data.get(key), dict) and isinstance(target_cfg_data.get(key), dict):
                  combined_cfg[key] = {**base_cfg_data[key], **target_cfg_data[key]}
             else:
                  combined_cfg[key] = target_cfg_data.get(key, base_cfg_data.get(key))


        # Populate sensitive/environment-specific parts
        creds = Credentials(
            username=os.getenv("MELON_USERNAME", ""),
            password=os.getenv("MELON_PASSWORD", "")
        )
        captcha_cfg = CaptchaSettings(
             service=combined_cfg.get('captcha', {}).get('service', '2captcha'), # Default from base if not in target
             api_key=os.getenv("CAPTCHA_API_KEY", "")
         )
        proxy_cfg = ProxySettings(
            enabled=combined_cfg.get('proxy', {}).get('enabled', True), # Default from base
            url=os.getenv("PROXY_URL")
        )

        if not creds.username or not creds.password.get_secret_value():
            raise ValueError("MELON_USERNAME and MELON_PASSWORD must be set in environment or .env")
        if not captcha_cfg.api_key.get_secret_value():
             raise ValueError("CAPTCHA_API_KEY must be set in environment or .env")
        if proxy_cfg.enabled and not proxy_cfg.url:
             logging.warning("Proxy is enabled but PROXY_URL is not set. Disabling proxy.")
             proxy_cfg.enabled = False
             proxy_cfg.url = None # Ensure url is None if disabled this way


        # Construct the main Settings object data
        settings_data = {
            "credentials": creds.dict(), # Use dict() for nested models
            "network": combined_cfg.get('network', {}),
            "time": combined_cfg.get('time', {}),
            "target_event": combined_cfg.get('target_event', {}),
            "captcha": captcha_cfg.dict(),
            "proxy": proxy_cfg.dict(),
        }

        # Validate using Pydantic
        settings = Settings(**settings_data)
        logging.info("Configuration loaded and validated successfully.")
        return settings

    except FileNotFoundError as e:
        logging.error(f"Configuration file not found: {e.filename}")
        raise SystemExit(f"Config file missing: {e.filename}")
    except (yaml.YAMLError, ValidationError, ValueError, Exception) as e:
        logging.error(f"Error loading or validating configuration: {e}")
        raise SystemExit(f"Configuration error: {e}")

# Load config once on import
try:
    settings = load_config()
except SystemExit:
    # Ensure clean exit if config fails
    raise