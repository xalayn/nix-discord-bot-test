import logging
import sys

import discord

from .client import MailThreadClient
from .config import Config
from .errors import ConfigurationError


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        config = Config.from_environment()
    except ConfigurationError as error:
        sys.exit(str(error))

    client = MailThreadClient(config)

    @client.tree.command(name="hello", description="Check that the bot is running")
    async def hello(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("The mail bot is running. 👋")

    client.run(config.discord_token, log_handler=None)
