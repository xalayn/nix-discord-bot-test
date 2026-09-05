import asyncio
import time
from typing import Any

import aiohttp

from .config import Config
from .errors import ZohoError
from .messages import message_id


class ZohoMailClient:
    """Small async client for the read-only Zoho Mail APIs used by the bot."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.session: aiohttp.ClientSession | None = None
        self.access_token: str | None = None
        self.access_token_expires_at = 0.0
        self.token_lock = asyncio.Lock()
        self.account_id = config.zoho_account_id
        self.folder_id = config.zoho_folder_id

    async def close(self) -> None:
        if self.session is not None:
            await self.session.close()

    def _session(self) -> aiohttp.ClientSession:
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def _refresh_access_token(self) -> str:
        async with self.token_lock:
            if self.access_token and time.monotonic() < self.access_token_expires_at:
                return self.access_token

            url = f"{self.config.zoho_accounts_base_url}/oauth/v2/token"
            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.zoho_client_id,
                "client_secret": self.config.zoho_client_secret,
                "refresh_token": self.config.zoho_refresh_token,
            }
            async with self._session().post(url, data=data) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400 or "access_token" not in payload:
                    raise ZohoError(
                        f"Zoho token refresh failed ({response.status}): {payload}"
                    )

            self.access_token = str(payload["access_token"])
            expires_in = int(payload.get("expires_in", 3600))
            self.access_token_expires_at = time.monotonic() + max(30, expires_in - 60)
            return self.access_token

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        for attempt in range(2):
            token = await self._refresh_access_token()
            headers = {
                "Accept": "application/json",
                "Authorization": f"Zoho-oauthtoken {token}",
            }
            url = f"{self.config.zoho_api_base_url}/{path.lstrip('/')}"
            async with self._session().get(
                url, params=params, headers=headers
            ) as response:
                if response.status == 401 and attempt == 0:
                    self.access_token = None
                    self.access_token_expires_at = 0.0
                    continue
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise ZohoError(
                        f"Zoho request failed ({response.status}) for {path}: {payload}"
                    )
                status_code = payload.get("status", {}).get("code")
                if status_code is not None and int(status_code) >= 400:
                    raise ZohoError(f"Zoho request failed for {path}: {payload}")
                return payload.get("data")
        raise ZohoError(f"Zoho authentication failed for {path}")

    async def resolve_mailbox(self) -> tuple[str, str]:
        if self.account_id is None:
            accounts = await self._get("accounts")
            if not isinstance(accounts, list) or not accounts:
                raise ZohoError("No Zoho Mail accounts are available to this OAuth grant")
            if len(accounts) > 1:
                choices = ", ".join(
                    f"{account.get('accountId')} ({account.get('primaryEmailAddress', 'unknown')})"
                    for account in accounts
                )
                raise ZohoError(
                    "More than one Zoho Mail account is available; set ZOHO_ACCOUNT_ID "
                    f"to one of: {choices}"
                )
            self.account_id = str(accounts[0]["accountId"])

        if self.folder_id is None:
            folders = await self._get(f"accounts/{self.account_id}/folders")
            inboxes = [
                folder
                for folder in folders or []
                if str(folder.get("folderType", "")).casefold() == "inbox"
                and str(folder.get("path", "")).casefold() == "/inbox"
            ]
            if not inboxes:
                raise ZohoError(
                    "Could not find the Zoho Inbox folder; set ZOHO_FOLDER_ID explicitly"
                )
            self.folder_id = str(inboxes[0]["folderId"])

        return self.account_id, self.folder_id

    async def list_messages_page(
        self, *, start: int = 1, limit: int = 200
    ) -> list[dict[str, Any]]:
        account_id, folder_id = await self.resolve_mailbox()
        data = await self._get(
            f"accounts/{account_id}/messages/view",
            params={
                "folderId": folder_id,
                "start": str(start),
                "limit": str(limit),
                "sortBy": "date",
                "sortorder": "false",
                "includeto": "true",
                "includesent": "false",
            },
        )
        return data if isinstance(data, list) else []

    async def message_content(self, message: dict[str, Any]) -> str:
        account_id, default_folder_id = await self.resolve_mailbox()
        folder_id = str(message.get("folderId") or default_folder_id)
        data = await self._get(
            f"accounts/{account_id}/folders/{folder_id}/messages/"
            f"{message_id(message)}/content",
            params={"includeBlockContent": "false"},
        )
        if not isinstance(data, dict):
            return ""
        return str(data.get("content", ""))
