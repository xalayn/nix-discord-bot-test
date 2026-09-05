import os
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigurationError


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} is not set")
    return value


def _integer_environment(name: str, default: int, minimum: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer") from error
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return value


@dataclass(frozen=True)
class Config:
    discord_token: str
    discord_channel_id: int
    zoho_client_id: str
    zoho_client_secret: str
    zoho_refresh_token: str
    zoho_account_id: str | None
    zoho_folder_id: str | None
    zoho_api_base_url: str
    zoho_accounts_base_url: str
    state_db_path: Path
    poll_interval_seconds: int

    @classmethod
    def from_environment(cls) -> "Config":
        channel_id = _required_environment("DISCORD_CHANNEL_ID")
        try:
            parsed_channel_id = int(channel_id)
        except ValueError as error:
            raise ConfigurationError("DISCORD_CHANNEL_ID must be an integer") from error

        return cls(
            discord_token=_required_environment("DISCORD_TOKEN"),
            discord_channel_id=parsed_channel_id,
            zoho_client_id=_required_environment("ZOHO_CLIENT_ID"),
            zoho_client_secret=_required_environment("ZOHO_CLIENT_SECRET"),
            zoho_refresh_token=_required_environment("ZOHO_REFRESH_TOKEN"),
            zoho_account_id=os.environ.get("ZOHO_ACCOUNT_ID") or None,
            zoho_folder_id=os.environ.get("ZOHO_FOLDER_ID") or None,
            zoho_api_base_url=os.environ.get(
                "ZOHO_API_BASE_URL", "https://mail.zoho.com/api"
            ).rstrip("/"),
            zoho_accounts_base_url=os.environ.get(
                "ZOHO_ACCOUNTS_BASE_URL", "https://accounts.zoho.com"
            ).rstrip("/"),
            state_db_path=Path(
                os.environ.get("STATE_DB_PATH", "zoho-discord-bot.sqlite3")
            ).expanduser(),
            poll_interval_seconds=_integer_environment(
                "POLL_INTERVAL_SECONDS", default=30, minimum=10
            ),
        )
