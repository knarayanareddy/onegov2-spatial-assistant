from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_dir = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_backend_dir / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GREENPT_KEY: str = ""

    ALLOWED_ORIGINS: str = "*"
    DEBUG: bool = False
    DICTIONARY_CACHE: bool = True
    # FAQ cache backend (Phase 3/4): "memory" (default) or "postgres".
    # "postgres" activates SqlFaqCache(engine) at startup (run the Alembic migration first).
    FAQ_CACHE_BACKEND: str = "memory"
    # Phase 5: attempt the live RWS Waterinfo chloride feed for intake scenarios.
    # Off by default (offline/sandbox uses the dated last-known fallback, never silent).
    WATERINFO_LIVE: bool = False

    # Phase 6 — authentication & audit (Woo/accountability).
    # AUTH_MODE: "dev" (single local user, default) | "jwt" (verify Bearer) | "header" (trust proxy).
    AUTH_MODE: str = "dev"
    AUTH_REQUIRED: bool = False               # reject unauthenticated requests (non-dev modes)
    AUTH_JWT_SECRET: str = ""                  # HS256 shared secret
    AUTH_JWT_ALGORITHM: str = "HS256"
    AUTH_JWT_JWKS_URL: str = ""                # RS256 via a JWKS endpoint (e.g. Keycloak/Azure AD)
    AUTH_JWT_AUDIENCE: str = ""
    AUTH_HEADER_NAME: str = "X-Auth-User"      # OIDC reverse-proxy identity header
    AUTH_HEADER_DISPLAY_NAME: str = "X-Auth-Name"
    AUTH_HEADER_ROLES: str = "X-Auth-Roles"
    AUTH_ROLES_CLAIM: str = "roles"            # JWT claim holding roles
    AUTH_ADMIN_ROLE: str = "admin"
    AUDIT_BACKEND: str = "memory"              # "memory" (default) | "postgres"
    OPENAI_MODEL: str = "qwen3-coder-30b-a3b-instruct"
    PORT: int = 8000
    DATABASE_URL: str = (
        "postgresql+asyncpg://ruimtelijke:secret123!@localhost:5432/sessions"
    )

    # MLflow observability
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "ruimtelijke-assistent-dev"
    MLFLOW_ENABLED: bool = False
    ENV: str = "dev"
    APP_VERSION: str = "dev"

    # Filter value validation — fuzzy-matching thresholds
    FILTER_MAX_FUZZY_CANDIDATES: int = (
        20  # Cap candidates shown to the correction LLM to keep the prompt concise.
    )
    FILTER_FUZZY_CUTOFF: float = 0.3  # Minimum similarity score; lower values cause too many false positives on short names.
    FILTER_ALL_VALUES_THRESHOLD: int = 200  # Columns with fewer distinct values show the full list instead of fuzzy matches.


settings = Settings()
