"""GK9 Telegram bot: three useful text tools, no external redirects."""

import asyncio
import logging
import os
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import TypeVar

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ChatType
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, FSInputFile, Message, ReplyKeyboardRemove

from text_tools import MAX_INPUT_LENGTH, process_text

BOT_NAME = "GK9"
BOT_USERNAME = "GK9Tool_BOT"
BOT_ABOUT = (
    "GK9 text tools: change case, count words and characters, "
    "and clean extra spaces directly in Telegram."
)
BOT_DESCRIPTION = (
    "Welcome to GK9 Text Tools!\n\n"
    "Change Case: convert text to uppercase, lowercase, or title case.\n"
    "Count Words: see word, character, and line counts.\n"
    "Clean Text: remove extra spaces and empty lines.\n\n"
    "Choose one of the three buttons, then send your text. "
    "All tools work directly in this chat. Use /start to begin."
)

CHANGE_CASE = "Change Case"
COUNT_WORDS = "Count Words"
CLEAN_TEXT = "Clean Text"
TOOLS = (CHANGE_CASE, COUNT_WORDS, CLEAN_TEXT)

WELCOME = (
    "Welcome to GK9 Text Tools!\n\n"
    "Choose a text tool by typing its name:\n"
    "Change Case - uppercase, lowercase, and title case.\n"
    "Count Words - word, character, and line counts.\n"
    "Clean Text - remove extra spaces and blank lines.\n\n"
    "Type Change Case, Count Words, or Clean Text to begin."
)

# Welcome image uploaded to welcome.jpg in this repository.
WELCOME_IMAGE = Path(__file__).resolve().parent / "welcome.jpg"
SYARIKAT_WELCOME = (
    "💝✋👩👩‍💼✖️ 😏🙂‍↕️😰😥\n\n"
    "WELCOME TO SYARIKAT MY\n\n"
    "⚡️4 JENAMA • 1 KELUARGA\n"
    "⚡️BERSATU BERSAMA 4DGANG\n"
    "⚡️4 JENAMA • 1 DESTINASI\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "⭐️ Kenali Jenama Kami & Terokai Lebih Banyak Pilihan!\n"
    "⭐️ DI BAWAH NAUNGAN 4DGANG GROUP\n\n"
    "⬇️ PILIH JENAMA KEGEMARAN ANDA DI BAWAH! ⬇️"
)
SYARIKAT_BRANDS = (
    "MY.CASH88\n"
    "https://mycash88.com/RFTELEGRAMADS\n\n"
    "GK9\n"
    "https://gk9gk9.com/RFTELEGRAMADS\n\n"
    "LUCKYEGG88\n"
    "https://luckyegg88.com/RFTELEGRAMADS\n\n"
    "MAHKOTA8\n"
    "https://mkt8.vip/RFTELEGRAMADS1"
)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)
logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_telegram_call(label: str, operation: Callable[[], Awaitable[T]]) -> T:
    """Keep one bot process alive through transient Telegram startup failures.

    Respect Telegram-provided flood-control delays; never retry authentication
    failures, bad requests, or other permanent Telegram API errors.
    """
    delay = 5
    while True:
        try:
            return await operation()
        except TelegramRetryAfter as exc:
            wait = max(1, exc.retry_after + 1)
            logger.warning("Telegram rate-limited %s; retrying in %s seconds", label, wait)
        except (TelegramNetworkError, TelegramServerError) as exc:
            wait = delay
            delay = min(delay * 2, 120)
            logger.warning(
                "Telegram %s request failed (%s); retrying in %s seconds",
                label,
                type(exc).__name__,
                wait,
            )
        await asyncio.sleep(wait)


class WorkState(StatesGroup):
    awaiting_text = State()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()

    # First message: welcome image and caption. If the image has not yet
    # been uploaded to the repository, send the caption as text instead.
    if WELCOME_IMAGE.is_file():
        await message.answer_photo(
            photo=FSInputFile(WELCOME_IMAGE),
            caption=SYARIKAT_WELCOME,
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        logger.warning("Welcome image missing: %s", WELCOME_IMAGE)
        await message.answer(SYARIKAT_WELCOME, reply_markup=ReplyKeyboardRemove())

    # Second message: the four exact brand destinations requested.
    await message.answer(SYARIKAT_BRANDS)


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        WELCOME
        + "\n\nAfter choosing a tool, send up to "
        + str(MAX_INPUT_LENGTH)
        + " characters. Use /cancel to return to the menu.",
    )


@router.message(Command("about"))
async def about_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        BOT_NAME + "\n" + BOT_ABOUT + "\n\nType Change Case, Count Words, or Clean Text to start.",
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Tool cancelled. Type Change Case, Count Words, or Clean Text.")


@router.message(F.text.in_(TOOLS))
async def choose_tool(message: Message, state: FSMContext) -> None:
    tool = message.text
    await state.set_state(WorkState.awaiting_text)
    await state.update_data(tool=tool)
    prompts = {
        CHANGE_CASE: "Send text to see UPPERCASE, lowercase, and Title Case versions.",
        COUNT_WORDS: "Send text to count words, characters, and lines.",
        CLEAN_TEXT: "Send text to remove extra spaces and blank lines.",
    }
    await message.answer(
        prompts[tool] + "\n\nMaximum: " + str(MAX_INPUT_LENGTH) + " characters.",
    )


@router.message(WorkState.awaiting_text)
async def handle_text(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await message.answer("Please send a text message to use this tool.")
        return

    if message.text.startswith("/"):
        await message.answer(
            "Unknown command. Send text, choose another tool, or use /cancel.",
            )
        return

    data = await state.get_data()
    tool = data.get("tool")
    if tool not in TOOLS:
        await state.clear()
        await message.answer("Type Change Case, Count Words, or Clean Text first.")
        return

    result = process_text(tool, message.text)
    await message.answer(result)


@router.message()
async def no_tool_selected(message: Message) -> None:
    await message.answer("Type Change Case, Count Words, or Clean Text to begin.")


async def safely_apply(label: str, operation: Awaitable[bool]) -> None:
    try:
        await operation
        logger.info("Updated Telegram bot %s.", label)
    except TelegramAPIError:
        logger.exception("Could not update bot %s; check BotFather or API permissions.", label)


async def configure_bot(bot: Bot) -> None:
    await safely_apply("name", bot.set_my_name(name=BOT_NAME))
    await safely_apply(
        "About / short description",
        bot.set_my_short_description(short_description=BOT_ABOUT),
    )
    await safely_apply(
        "description",
        bot.set_my_description(description=BOT_DESCRIPTION),
    )
    await safely_apply(
        "commands",
        bot.set_my_commands(
            commands=[
                BotCommand(command="start", description="Open the 3 text tools"),
                BotCommand(command="help", description="How GK9 tools work"),
                BotCommand(command="about", description="About GK9"),
                BotCommand(command="cancel", description="Return to the menu"),
            ]
        ),
    )


async def main() -> None:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to your deployment environment.")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    async with Bot(token=token, session=AiohttpSession(timeout=60)) as bot:
        identity = await retry_telegram_call("getMe", bot.get_me)
        if (identity.username or "").casefold() != BOT_USERNAME.casefold():
            raise RuntimeError(
                "This token belongs to @"
                + str(identity.username)
                + ", not @"
                + BOT_USERNAME
                + ". Refusing to modify another bot."
            )

        await retry_telegram_call(
            "deleteWebhook", lambda: bot.delete_webhook(drop_pending_updates=False)
        )
        await configure_bot(bot)
        logger.info("GK9 polling started as @%s", identity.username)
        await dp.start_polling(bot, close_bot_session=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())
