from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: list[str] = ["http://localhost:5173"]

    # OpenRouter — https://openrouter.ai/docs (OpenAI-compatible chat completions)
    openrouter_api_key: str = ""
    openrouter_model: str = "stepfun/step-3.5-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 600.0
    # Optional OpenRouter headers (recommended for rankings / identification)
    openrouter_http_referer: str = ""
    openrouter_app_title: str = "LLM Pipeline Optimizer"

    # Optimization: pipelines with this many LLM calls or fewer use one combined prompt + repair loop.
    optimize_single_shot_llm_call_threshold: int = 4
    # Max model calls per phase (step 1 JSON, step 2 JSON, step 3 code) before giving up.
    optimize_repair_attempts_per_phase: int = 25


settings = Settings()
