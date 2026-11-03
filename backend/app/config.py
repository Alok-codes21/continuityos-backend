import os


class Settings:
    """Runtime settings read from environment variables (see .env.example)."""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./continuityos.db")
        self.jwt_secret = os.getenv("JWT_SECRET", "dev-only-change-me-please-32-bytes-min")
        self.jwt_hours = int(os.getenv("JWT_HOURS", "12"))
        # Fernet key (urlsafe base64, 32 bytes) used to encrypt connector tokens at rest.
        self.token_key = os.getenv("TOKEN_ENCRYPTION_KEY", "")
        self.outdated_days = int(os.getenv("OUTDATED_DAYS", "180"))
        self.llm_provider = os.getenv("LLM_PROVIDER", "none")  # none | gemini | groq
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.github_max_pages = int(os.getenv("GITHUB_MAX_PAGES", "20"))
        self.cors_origins = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o]


settings = Settings()
