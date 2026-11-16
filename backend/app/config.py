from functools import lru_cache
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "local"
    database_path: str = "data/northgate.db"
    static_dir: str = "frontend/dist"
    auth_secret: str = ""
    mcp_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    gemini_model: str = Field(default="gemini-2.5-flash-lite", validation_alias=AliasChoices("GEMINI_MODEL_NAME", "GEMINI_MODEL"))
    groq_model: str = "llama-3.3-70b-versatile"
    default_operator_password: str = "NorthgateDemo!2026"
    secure_cookies: bool = False
    offline_demo: bool = False
    llm_timeout_seconds: float = 40
    usd_to_gbp: float = 0.79
    gemini_input_per_million: float = 0.10
    gemini_output_per_million: float = 0.40
    groq_input_per_million: float = 0.59
    groq_output_per_million: float = 0.79


@lru_cache
def settings():
    value = Settings()
    # Ephemeral local sessions are invalidated on process restart unless configured.
    if not value.auth_secret:
        value.auth_secret = secrets.token_urlsafe(48)
    return value
