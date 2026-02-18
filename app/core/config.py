from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, AnyHttpUrl
from typing import List, Union


class Settings(BaseSettings):
    PROJECT_NAME: str
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BACKEND_CORS_ORIGINS: Union[List[str], str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    DATABASE_URL: str
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str

    # Gemini Configuration
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # MCP Configuration
    MCP_SERVER_PYTHON_PATH: str = "python3"
    MCP_SERVER_SCRIPT_PATH: str | None = None

    # Custom validator to parse CORS from string or list
    @property
    def cors_origins(self) -> list[str]:
        return self.BACKEND_CORS_ORIGINS

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)


settings = Settings()
