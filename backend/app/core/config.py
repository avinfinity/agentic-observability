from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Loads application settings from environment variables."""
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    
    GOOGLE_API_KEY: str
    GEMINI_MODEL_ID: str = "gemini-1.5-pro-latest"

settings = Settings()