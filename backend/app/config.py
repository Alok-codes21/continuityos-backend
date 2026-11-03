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
        if not 1 <= self.jwt_hours <= 720 or not 1 <= self.outdated_days <= 3650 or not 1 <= self.github_max_pages <= 100:
            raise ValueError("JWT_HOURS, OUTDATED_DAYS and GITHUB_MAX_PAGES must be within supported positive ranges")
        if bool(os.getenv("TLS_CERT")) != bool(os.getenv("TLS_KEY")):
            raise ValueError("TLS_CERT and TLS_KEY must both be set or both omitted")
        self.environment = os.getenv("APP_ENV", "development")
        if self.environment == "production":
            if self.jwt_secret.startswith("dev-only") or len(self.jwt_secret) < 32:
                raise ValueError("Production requires a non-default JWT_SECRET of at least 32 characters")
            if not os.getenv("DATABASE_URL") or self.database_url.startswith("sqlite"):
                raise ValueError("Production requires an explicit persistent non-SQLite DATABASE_URL")
            if not self.token_key:
                raise ValueError("Production requires TOKEN_ENCRYPTION_KEY")
            from cryptography.fernet import Fernet
            Fernet(self.token_key.encode())
        self.cors_origins = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o]


settings = Settings()
