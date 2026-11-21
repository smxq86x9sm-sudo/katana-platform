from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    SSH_HOST: str = Field(...)
    SSH_PORT: int = Field(22)
    SSH_USER: str = Field(...)
    SSH_KEY_PATH: str = Field("")
    SSH_KEY_CONTENT: str = Field("")
    SSH_KNOWN_HOSTS: str = Field("/home/appuser/.ssh/known_hosts")
    API_TOKEN: str = Field(...)
    COMMAND_TIMEOUT: int = Field(30)
    MAX_OUTPUT_BYTES: int = Field(1_048_576)

settings = Settings()
