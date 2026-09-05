import logging
import os
import sys

import discord
from discord import app_commands


token = os.environ.get("DISCORD_TOKEN")
if not token:
    sys.exit("DISCORD_TOKEN is not set")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


class HelloClient(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.none())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        commands = await self.tree.sync()
        logging.info("Synced %d application command(s)", len(commands))

    async def on_ready(self) -> None:
        if self.user is not None:
            logging.info("Connected as %s (%s)", self.user, self.user.id)


client = HelloClient()


@client.tree.command(name="hello", description="Say hello")
async def hello(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Hello, world! 👋")


client.run(token, log_handler=None)
