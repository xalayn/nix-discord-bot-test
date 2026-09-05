import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zoho_discord_bot.config import Config
from zoho_discord_bot.errors import ConfigurationError
from zoho_discord_bot.presentation import html_to_text, thread_name
from zoho_discord_bot.state import StateStore


class ConfigTests(unittest.TestCase):
    required = {
        "DISCORD_TOKEN": "discord-token",
        "DISCORD_CHANNEL_ID": "1234",
        "ZOHO_CLIENT_ID": "client-id",
        "ZOHO_CLIENT_SECRET": "client-secret",
        "ZOHO_REFRESH_TOKEN": "refresh-token",
    }

    def test_required_configuration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                Config.from_environment()

    def test_defaults(self) -> None:
        with patch.dict(os.environ, self.required, clear=True):
            config = Config.from_environment()
        self.assertEqual(config.discord_channel_id, 1234)
        self.assertEqual(config.poll_interval_seconds, 30)
        self.assertEqual(config.zoho_api_base_url, "https://mail.zoho.com/api")


class FormattingTests(unittest.TestCase):
    def test_html_to_text_removes_markup_and_scripts(self) -> None:
        content = "<p>Hello &amp; welcome</p><script>bad()</script><div>Next</div>"
        self.assertEqual(html_to_text(content), "Hello & welcome\nNext")

    def test_thread_name_is_single_line_and_bounded(self) -> None:
        message = {"subject": "A\n" + "long " * 30, "sender": "Customer"}
        result = thread_name(message)
        self.assertNotIn("\n", result)
        self.assertLessEqual(len(result), 100)


class StateStoreTests(unittest.TestCase):
    def test_bootstrap_and_conversation_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "state.sqlite3")
            existing = {"messageId": "10", "threadId": "conversation"}
            store.bootstrap([existing])
            self.assertTrue(store.initialized)
            self.assertTrue(store.is_processed("10"))

            store.complete_message("11", "conversation", 999)
            self.assertTrue(store.is_processed("11"))
            self.assertEqual(store.discord_thread_id("conversation"), 999)

            store.forget_discord_thread("conversation")
            self.assertIsNone(store.discord_thread_id("conversation"))
            store.close()


if __name__ == "__main__":
    unittest.main()
