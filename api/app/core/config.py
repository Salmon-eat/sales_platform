from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"

    database_url: str = "postgresql+asyncpg://bazarcito:bazarcito@localhost:5432/bazarcito"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "dev-secret"

    # Admin access (admin spec §1): Google sign-in for whitelisted emails, 30-day sessions.
    google_client_id: str = ""
    session_days: int = 30
    login_attempts_per_ip: int = 20  # per 10 minutes
    # Local development without a Google client: sign in by a whitelisted email. Never in production.
    admin_dev_login: bool = False

    # Applications (spec §9, §10)
    privacy_policy_version: str = "2026-09-19"
    applications_per_ip_per_hour: int = 5
    # GDPR (admin spec §9): closed applications lose their personal data after this many months
    anonymize_after_months: int = 24

    # Telegram bot sync: the bot pushes its applications and conversations and picks up replies written
    # in the admin. A shared secret of at least 32 chars; empty = the bot endpoints are closed.
    bot_sync_token: str = ""

    # IndexNow (Bing, Yandex and others): a random key, also served at /{key}.txt; empty = off
    indexnow_key: str = ""

    # "Sign in with Telegram": a bot of its own, so the working bot's token never leaves its server.
    # The token is only used to check Telegram's signature; the site never calls the Bot API with it.
    telegram_login_bot: str = ""  # bot username without @
    telegram_login_token: str = ""

    # Email: sign-in codes and notifications. Resend (an API key) or a plain SMTP server;
    # with neither, letters are written to the log (local development).
    mail_from: str = "Citobazar <no-reply@citobazar.com>"
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # Cloudflare Turnstile on the public forms (anti-bot); empty = off (honeypot and IP limits still work)
    turnstile_secret_key: str = ""
    public_site_url: str = "http://localhost:3000"

    # TTLs from the spec (section 7, 9)
    facets_cache_ttl: int = 60
    suggest_cache_ttl: int = 600
    taxonomy_cache_ttl: int = 300

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @model_validator(mode="after")
    def _check_secret(self) -> "Settings":
        weak = self.secret_key in {"dev-secret", "change-me"} or len(self.secret_key) < 32
        if self.is_production and weak:
            raise ValueError("SECRET_KEY must be a random string of at least 32 chars in production")
        if self.is_production and self.admin_dev_login:
            raise ValueError("ADMIN_DEV_LOGIN signs in without Google and must stay off in production")
        if self.is_production and self.bot_sync_token and len(self.bot_sync_token) < 32:
            raise ValueError("BOT_SYNC_TOKEN must be a random string of at least 32 chars")
        return self


settings = Settings()
