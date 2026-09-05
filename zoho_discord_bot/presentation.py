import asyncio
import html
import logging
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any

import aiohttp
import discord

from .errors import ZohoError
from .messages import message_id, received_time
from .zoho import ZohoMailClient


logger = logging.getLogger(__name__)


class _HTMLTextExtractor(HTMLParser):
    block_tags = {"br", "div", "p", "li", "tr", "blockquote", "h1", "h2", "h3"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth += 1
        elif tag in self.block_tags and self.parts:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
        elif tag in self.block_tags and self.parts:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)


def html_to_text(content: str) -> str:
    parser = _HTMLTextExtractor()
    try:
        parser.feed(content)
        text = "".join(parser.parts)
    except Exception:
        text = content
    lines = [" ".join(line.split()) for line in html.unescape(text).splitlines()]
    return "\n".join(line for line in lines if line).strip()


def clipped(value: Any, limit: int, fallback: str = "—") -> str:
    text = html.unescape(str(value or "")).strip() or fallback
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def thread_name(message: dict[str, Any]) -> str:
    subject = clipped(message.get("subject"), 70, "(no subject)")
    sender = clipped(message.get("sender") or message.get("fromAddress"), 24, "Unknown")
    name = " ".join(f"{subject} — {sender}".replace("\n", " ").split())
    return clipped(name, 100, "Email discussion")


async def email_embed(
    zoho: ZohoMailClient, message: dict[str, Any]
) -> discord.Embed:
    try:
        body = html_to_text(await zoho.message_content(message))
    except (aiohttp.ClientError, asyncio.TimeoutError, ZohoError):
        logger.warning(
            "Could not retrieve content for Zoho message %s; using its summary",
            message_id(message),
            exc_info=True,
        )
        body = html_to_text(str(message.get("summary", "")))

    subject = clipped(message.get("subject"), 256, "(no subject)")
    description = clipped(body, 3900, "(No message preview available)")
    timestamp = None
    if received_time(message):
        try:
            timestamp = datetime.fromtimestamp(received_time(message) / 1000, tz=UTC)
        except (OverflowError, OSError, ValueError):
            pass

    embed = discord.Embed(
        title=subject,
        description=description,
        color=discord.Color.blue(),
        timestamp=timestamp,
    )
    sender_name = str(message.get("sender") or "").strip()
    sender_address = str(message.get("fromAddress") or "").strip()
    sender = (
        f"{sender_name} <{sender_address}>"
        if sender_name and sender_address and sender_name != sender_address
        else sender_address or sender_name
    )
    embed.add_field(name="From", value=clipped(sender, 512, "Unknown"), inline=False)
    embed.add_field(
        name="To", value=clipped(message.get("toAddress"), 512), inline=False
    )
    cc_address = str(message.get("ccAddress") or "").strip()
    if cc_address and cc_address.casefold() != "not provided":
        embed.add_field(name="Cc", value=clipped(cc_address, 512), inline=False)
    if str(message.get("hasAttachment", "0")).casefold() in {"1", "true"}:
        embed.add_field(name="Attachments", value="Yes", inline=True)
    embed.set_footer(text=f"Zoho message {message_id(message)}")
    return embed
