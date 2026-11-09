"""Tests for visible modes and admin protection."""

import os
import tempfile
import unittest
from unittest.mock import patch

from aiogram.types import User
from mode_store import ModeStore, MODE_TOOLS, MODE_GAMES
from main import ADMIN_MENU, BRAND_MENU, BRAND_LINKS, NAV_MENU, is_admin


class ModeStoreTests(unittest.TestCase):
    def test_default_and_persistent_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "subfolder", "mode.db")
            db = ModeStore(path)
            self.assertEqual(db.get_mode(), MODE_TOOLS)
            db.set_mode(MODE_GAMES)
            self.assertEqual(ModeStore(path).get_mode(), MODE_GAMES)
            db.set_mode(MODE_TOOLS)
            self.assertEqual(ModeStore(path).get_mode(), MODE_TOOLS)

    def test_invalid_mode_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            db = ModeStore(os.path.join(folder, "mode.db"))
            with self.assertRaises(ValueError):
                db.set_mode("hidden")


class VisibilityTests(unittest.TestCase):
    def test_both_features_visible(self):
        names = [button.text for row in NAV_MENU.inline_keyboard for button in row]
        self.assertTrue(any("Text Tools" in name for name in names))
        self.assertTrue(any("Games & Links" in name for name in names))

    def test_original_urls_preserved(self):
        urls = [button.url for row in BRAND_MENU.inline_keyboard for button in row]
        self.assertEqual(list(BRAND_LINKS.values()), urls)

    def test_admin_buttons_present(self):
        actions = [button.callback_data for row in ADMIN_MENU.inline_keyboard for button in row]
        self.assertIn("admin:redirect", actions)
        self.assertIn("admin:reverse", actions)

    def test_only_admin_authorized(self):
        user = User(id=12345, is_bot=False, first_name="Admin")
        with patch.dict(os.environ, {"ADMIN_ID": "12345"}):
            self.assertTrue(is_admin(user))
        with patch.dict(os.environ, {"ADMIN_ID": "99999"}):
            self.assertFalse(is_admin(user))
        with patch.dict(os.environ, {"ADMIN_ID": ""}):
            self.assertFalse(is_admin(user))


if __name__ == "__main__":
    unittest.main()
