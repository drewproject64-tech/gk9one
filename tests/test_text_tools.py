"""Run with: python -m unittest discover -s tests -v"""

import unittest

from text_tools import clean_text, process_text, MAX_INPUT_LENGTH


class TextToolsTests(unittest.TestCase):
    def test_clean_extra_spaces(self):
        self.assertEqual(clean_text(" Hello   world \t ! "), "Hello world !")

    def test_clean_blank_lines(self):
        self.assertEqual(
            clean_text("\n First   line \n\n \t\n Second\tline \n"),
            "First line\nSecond line",
        )

    def test_clean_empty(self):
        self.assertEqual(clean_text("\n \t\n"), "")

    def test_case_conversions(self):
        result = process_text("Change Case", "hello WORLD")
        self.assertIn("HELLO WORLD", result)
        self.assertIn("hello world", result)
        self.assertIn("Hello World", result)

    def test_word_and_character_counts(self):
        result = process_text("Count Words", "Hi  there\nGK9")
        self.assertIn("Words: 3", result)
        self.assertIn("Characters (including spaces): 13", result)
        self.assertIn("Characters (excluding whitespace): 10", result)
        self.assertIn("Lines: 2", result)

    def test_clean_tool(self):
        self.assertEqual(
            process_text("Clean Text", " a  b \n\n c "),
            "Cleaned text:\na b\nc",
        )

    def test_empty_input(self):
        self.assertIn("non-empty", process_text("Change Case", "\n  "))

    def test_unknown_tool(self):
        self.assertIn("choose", process_text("Wrong tool", "Hello"))

    def test_input_limit(self):
        self.assertIn(
            "too long",
            process_text("Count Words", "x" * (MAX_INPUT_LENGTH + 1)),
        )

    def test_unicode_case_expansion(self):
        self.assertIn("STRASSE", process_text("Change Case", "straße"))

    def test_too_many_emojis(self):
        self.assertIn(
            "shorter",
            process_text("Change Case", "😀" * MAX_INPUT_LENGTH),
        )



from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramUnauthorizedError
from aiogram.methods import GetMe
from main import retry_telegram_call


class StartupRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_then_success(self):
        op = AsyncMock(side_effect=[
            TelegramNetworkError(method=GetMe(), message="timeout"),
            "connected",
        ])
        with patch("main.asyncio.sleep", new_callable=AsyncMock) as sleep:
            self.assertEqual(await retry_telegram_call("getMe", op), "connected")
            sleep.assert_awaited_once_with(5)
            self.assertEqual(op.await_count, 2)

    async def test_respects_flood_control(self):
        op = AsyncMock(side_effect=[
            TelegramRetryAfter(method=GetMe(), message="Too Many Requests", retry_after=27),
            "connected",
        ])
        with patch("main.asyncio.sleep", new_callable=AsyncMock) as sleep:
            self.assertEqual(await retry_telegram_call("getMe", op), "connected")
            sleep.assert_awaited_once_with(28)

    async def test_exponential_delay_for_outage(self):
        op = AsyncMock(side_effect=[
            TelegramNetworkError(method=GetMe(), message="timeout"),
            TelegramNetworkError(method=GetMe(), message="timeout"),
            TelegramNetworkError(method=GetMe(), message="timeout"),
            "connected",
        ])
        with patch("main.asyncio.sleep", new_callable=AsyncMock) as sleep:
            self.assertEqual(await retry_telegram_call("getMe", op), "connected")
            self.assertEqual(
                [call.args[0] for call in sleep.await_args_list], [5, 10, 20]
            )

    async def test_invalid_token_fails_without_retry(self):
        op = AsyncMock(side_effect=TelegramUnauthorizedError(
            method=GetMe(), message="Unauthorized"
        ))
        with patch("main.asyncio.sleep", new_callable=AsyncMock) as sleep:
            with self.assertRaises(TelegramUnauthorizedError):
                await retry_telegram_call("getMe", op)
            sleep.assert_not_awaited()

if __name__ == "__main__":
    unittest.main()
