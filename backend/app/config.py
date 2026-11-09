from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "SENTINEL"
    environment: str = "dev"
    database_url: str = "sqlite:///./sentinel.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-me-32chars-long!!"
    encryption_key: str = ""  # Fernet key; derived from secret_key if empty
    jwt_algorithm: str = "HS256"
    access_token_expire_min: int = 60*24
    default_provider: str = "mock"
    default_model: str = "mock-llm-1"
    fallback_provider: str = ""  # e.g. "groq" — tried if primary fails
    langsmith_api_key: str = ""
    langsmith_project: str = "sentinel"
    # Optional server-side fallback keys (per-user keys via /auth/credentials take priority)
    openai_api_key: str = ""
    groq_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    tavily_api_key: str = ""  # for live web_search (future wiring)
    # Hard defaults (configurable per execution)
    max_steps: int = 20
    max_tool_calls: int = 30
    max_retries: int = 5
    max_runtime_s: int = 300
    max_concurrent_tools: int = 3
    max_replans: int = 3
    enable_mock_llm: bool = True

settings = Settings()
