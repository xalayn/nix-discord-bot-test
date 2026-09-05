import asyncio
import logging
from typing import Any

import discord
from discord import app_commands

from .config import Config
from .messages import message_id, received_time, zoho_thread_id
from .presentation import email_embed, thread_name
from .state import StateStore
from .zoho import ZohoMailClient


logger = logging.getLogger(__name__)


class MailThreadClient(discord.Client):
    """Discord client and the polling/delivery orchestration loop."""

    def __init__(self, config: Config) -> None:
        super().__init__(intents=discord.Intents.none())
        self.config = config
        self.tree = app_commands.CommandTree(self)
        self.state_store = StateStore(config.state_db_path)
        self.zoho = ZohoMailClient(config)
        self.mail_task: asyncio.Task[None] | None = None
        self.target_channel: discord.TextChannel | discord.ForumChannel | None = None

    async def setup_hook(self) -> None:
        try:
            commands = await self.tree.sync()
            logger.info("Synced %d application command(s)", len(commands))
        except discord.HTTPException:
            # Mail delivery should not depend on the optional health-check command.
            logger.warning("Could not sync application commands", exc_info=True)
        self.mail_task = asyncio.create_task(self.mail_loop(), name="zoho-mail-poller")

    async def on_ready(self) -> None:
        if self.user is not None:
            logger.info("Connected as %s (%s)", self.user, self.user.id)

    async def close(self) -> None:
        if self.mail_task is not None:
            self.mail_task.cancel()
            try:
                await self.mail_task
            except asyncio.CancelledError:
                pass
        await self.zoho.close()
        self.state_store.close()
        await super().close()

    async def get_target_channel(
        self,
    ) -> discord.TextChannel | discord.ForumChannel:
        if self.target_channel is None:
            channel = await self.fetch_channel(self.config.discord_channel_id)
            if not isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
                raise RuntimeError(
                    "DISCORD_CHANNEL_ID must identify a server text or forum channel"
                )
            self.target_channel = channel
        return self.target_channel

    async def get_discord_thread(self, thread_id: int) -> discord.Thread:
        cached = self.get_channel(thread_id)
        if isinstance(cached, discord.Thread):
            return cached
        fetched = await self.fetch_channel(thread_id)
        if not isinstance(fetched, discord.Thread):
            raise RuntimeError(f"Discord channel {thread_id} is not a thread")
        return fetched

    async def create_discord_thread(
        self, message: dict[str, Any], embed: discord.Embed
    ) -> discord.Thread:
        channel = await self.get_target_channel()
        name = thread_name(message)
        allowed_mentions = discord.AllowedMentions.none()
        if isinstance(channel, discord.ForumChannel):
            created = await channel.create_thread(
                name=name,
                embed=embed,
                allowed_mentions=allowed_mentions,
                reason="New Zoho Mail conversation",
            )
            return created.thread

        starter = await channel.send(embed=embed, allowed_mentions=allowed_mentions)
        return await starter.create_thread(
            name=name,
            reason="New Zoho Mail conversation",
        )

    async def deliver_message(self, message: dict[str, Any]) -> int:
        zoho_thread = zoho_thread_id(message)
        discord_thread = self.state_store.discord_thread_id(zoho_thread)
        embed = await email_embed(self.zoho, message)

        if discord_thread is not None:
            try:
                thread = await self.get_discord_thread(discord_thread)
                await thread.send(
                    embed=embed, allowed_mentions=discord.AllowedMentions.none()
                )
                return thread.id
            except discord.NotFound:
                logger.warning(
                    "Discord thread %s was deleted; creating a replacement",
                    discord_thread,
                )
                self.state_store.forget_discord_thread(zoho_thread)

        thread = await self.create_discord_thread(message, embed)
        return thread.id

    async def new_messages(self) -> list[dict[str, Any]]:
        new: list[dict[str, Any]] = []
        start = 1
        page_size = 200
        while True:
            page = await self.zoho.list_messages_page(start=start, limit=page_size)
            reached_processed_message = False
            for message in page:
                if self.state_store.is_processed(message_id(message)):
                    reached_processed_message = True
                else:
                    new.append(message)
            if reached_processed_message or len(page) < page_size:
                break
            start += len(page)

        # Zoho returns newest first; Discord should read in chronological order.
        new.sort(key=lambda item: (received_time(item), message_id(item)))
        return new

    async def poll_once(self) -> None:
        if not self.state_store.initialized:
            current_messages = await self.zoho.list_messages_page()
            self.state_store.bootstrap(current_messages)
            logger.info(
                "Established inbox baseline with %d existing message(s); no backfill sent",
                len(current_messages),
            )
            return

        messages = await self.new_messages()
        for message in messages:
            zoho_message = message_id(message)
            zoho_thread = zoho_thread_id(message)
            discord_thread = await self.deliver_message(message)
            self.state_store.complete_message(
                zoho_message, zoho_thread, discord_thread
            )
            logger.info(
                "Delivered Zoho message %s to Discord thread %s",
                zoho_message,
                discord_thread,
            )

    async def mail_loop(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Zoho inbox poll failed")
            await asyncio.sleep(self.config.poll_interval_seconds)
