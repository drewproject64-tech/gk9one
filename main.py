"""GK9 bot: text tools and an openly accessible external gaming directory."""

import asyncio
import logging
import os
from functools import lru_cache
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
from aiogram.types import BotCommand, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message, User

from text_tools import MAX_INPUT_LENGTH, process_text
from mode_store import ModeStore, MODE_GAMES, MODE_TOOLS

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
    "WELCOME TO SYARIKAT MY\n\n"
    "⚡️4 JENAMA • 1 KELUARGA\n"
    "⚡️BERSATU BERSAMA 4DGANG\n"
    "⚡️4 JENAMA • 1 DESTINASI\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "⭐️ Kenali Jenama Kami & Terokai Lebih Banyak Pilihan!\n"
    "⭐️ DI BAWAH NAUNGAN 4DGANG GROUP\n\n"
    "⬇️ PILIH JENAMA KEGEMARAN ANDA DI BAWAH! ⬇️"
)
# Inline URL buttons displayed directly beneath the first welcome photo.
BRAND_LINKS = {
    "MY.CASH88": "https://mycash88.com/RFTELEGRAMADS",
    "GK9": "https://gk9gk9.com/RFTELEGRAMADS",
    "LUCKYEGG88": "https://luckyegg88.com/RFTELEGRAMADS",
    "MAHKOTA8": "https://mkt8.vip/RFTELEGRAMADS1",
}
BRAND_MENU = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="MY.CASH88", url=BRAND_LINKS["MY.CASH88"]),
            InlineKeyboardButton(text="GK9", url=BRAND_LINKS["GK9"]),
        ],
        [
            InlineKeyboardButton(text="LUCKYEGG88", url=BRAND_LINKS["LUCKYEGG88"]),
            InlineKeyboardButton(text="MAHKOTA8", url=BRAND_LINKS["MAHKOTA8"]),
        ],
    ]
)


# Public navigation is always shown for both functions in either featured mode.
NAV_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔤 Text Tools", callback_data="nav:tools")],
    [InlineKeyboardButton(text="🎮 Games & Links (external websites)", callback_data="nav:games")],
])
TEXT_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Change Case", callback_data="tool:change_case")],
    [InlineKeyboardButton(text="Count Words", callback_data="tool:count_words")],
    [InlineKeyboardButton(text="Clean Text", callback_data="tool:clean_text")],
    [InlineKeyboardButton(text="🎮 Games & Links", callback_data="nav:games")],
])
TOOL_CALLBACKS = {
    "tool:change_case": CHANGE_CASE,
    "tool:count_words": COUNT_WORDS,
    "tool:clean_text": CLEAN_TEXT,
}
ADMIN_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="▶️ REDIRECT — Feature Games & Links", callback_data="admin:redirect")],
    [InlineKeyboardButton(text="⏸ REVERSE — Feature Text Tools", callback_data="admin:reverse")],
    [InlineKeyboardButton(text="ℹ️ Check Status", callback_data="admin:status")],
])
FEATURE_NOTICE = (
    "GK9 offers Text Tools and Games & Links (external gaming websites). "
    "Both sections are available to every user. Choose an option below."
)
TOOL_PROMPTS = {
    CHANGE_CASE: "Send text to see UPPERCASE, lowercase, and Title Case versions.",
    COUNT_WORDS: "Send text to count words, characters, and lines.",
    CLEAN_TEXT: "Send text to remove extra spaces and blank lines.",
}


@lru_cache(maxsize=1)
def get_mode_store() -> ModeStore:
    return ModeStore(os.getenv("GK9_MODE_DB_PATH", "data/gk9_mode.sqlite3"))


def is_admin(user: User | None) -> bool:
    raw = os.getenv("ADMIN_ID", "").strip()
    return bool(user and raw.isdecimal() and user.id == int(raw))


async def show_text_tools(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=TEXT_MENU)


async def show_games_and_links(message: Message) -> None:
    # Preserve the original photo, caption, and four direct website buttons.
    if WELCOME_IMAGE.is_file():
        await message.answer_photo(
            photo=FSInputFile(WELCOME_IMAGE),
            caption=SYARIKAT_WELCOME,
            reply_markup=BRAND_MENU,
        )
    else:
        logger.warning("Welcome image missing: %s", WELCOME_IMAGE)
        await message.answer(SYARIKAT_WELCOME, reply_markup=BRAND_MENU)


async def show_navigation(message: Message) -> None:
    await message.answer(FEATURE_NOTICE, reply_markup=NAV_MENU)


async def set_admin_mode(message: Message, user: User | None, mode: str) -> None:
    if not is_admin(user):
        await message.answer("Administrator access required.")
        return
    get_mode_store().set_mode(mode)
    label = "Games & Links" if mode == MODE_GAMES else "Text Tools"
    await message.answer(
        f"Featured on /start: {label}.\n"
        "Both sections remain visible and accessible. "
        "Only future /start requests change; no broadcast is sent.",
        reply_markup=ADMIN_MENU,
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
    if get_mode_store().get_mode() == MODE_GAMES:
        await show_games_and_links(message)
    else:
        await show_text_tools(message)
    # No admin setting conceals either public feature.
    await show_navigation(message)


@router.message(Command("tools"))
async def tools_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_text_tools(message)
    await show_navigation(message)


@router.message(Command("games"))
async def games_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_games_and_links(message)
    await show_navigation(message)


@router.callback_query(F.data.in_(("nav:tools", "nav:games")))
async def feature_navigation(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    if callback.data == "nav:games":
        await show_games_and_links(callback.message)
    else:
        await show_text_tools(callback.message)
    await show_navigation(callback.message)


@router.message(Command("admin"))
async def admin_command(message: Message) -> None:
    if not is_admin(message.from_user):
        await message.answer("Administrator access required.")
        return
    mode = get_mode_store().get_mode()
    label = "Games & Links" if mode == MODE_GAMES else "Text Tools"
    await message.answer(
        f"GK9 Admin Panel\nFeatured on /start: {label}\n"
        "Both sections stay visible to all users.",
        reply_markup=ADMIN_MENU,
    )


@router.message(Command("redirect"))
@router.message(F.text.regexp(r"(?i)^redirect$"))
async def redirect_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await set_admin_mode(message, message.from_user, MODE_GAMES)


@router.message(Command("reverse"))
@router.message(F.text.regexp(r"(?i)^reverse$"))
async def reverse_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await set_admin_mode(message, message.from_user, MODE_TOOLS)


@router.callback_query(F.data.in_(("admin:redirect", "admin:reverse", "admin:status")))
async def admin_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user):
        await callback.answer("Administrator access required.", show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    if callback.data == "admin:redirect":
        await set_admin_mode(callback.message, callback.from_user, MODE_GAMES)
    elif callback.data == "admin:reverse":
        await set_admin_mode(callback.message, callback.from_user, MODE_TOOLS)
    else:
        label = ("Games & Links" if get_mode_store().get_mode() == MODE_GAMES else "Text Tools")
        await callback.message.answer(
            f"Featured on /start: {label}. Both sections remain available.",
            reply_markup=ADMIN_MENU,
        )


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        WELCOME + "\n\nUse /tools for text utilities or /games for external "
        "gaming links. Send up to " + str(MAX_INPUT_LENGTH)
        + " characters after selecting a tool. /cancel exits.",
        reply_markup=NAV_MENU,
    )


@router.message(Command("about"))
async def about_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        BOT_NAME + "\n" + BOT_ABOUT
        + "\n\nAlso available: Games & Links (external gaming websites).",
        reply_markup=NAV_MENU,
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Tool cancelled. Choose a section below.", reply_markup=NAV_MENU)


async def begin_text_tool(message: Message, state: FSMContext, tool: str) -> None:
    await state.set_state(WorkState.awaiting_text)
    await state.update_data(tool=tool)
    await message.answer(
        TOOL_PROMPTS[tool] + "\n\nMaximum: " + str(MAX_INPUT_LENGTH)
        + " characters. /cancel returns to the menu."
    )


@router.callback_query(F.data.in_(tuple(TOOL_CALLBACKS)))
async def tool_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    tool = TOOL_CALLBACKS.get(callback.data)
    if tool is None:
        await callback.answer()
        return
    await callback.answer()
    await begin_text_tool(callback.message, state, tool)


@router.message(F.text.in_(TOOLS))
async def choose_tool(message: Message, state: FSMContext) -> None:
    await begin_text_tool(message, state, message.text)


@router.message(WorkState.awaiting_text)
async def handle_text(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await message.answer("Please send a text message to use this tool.")
        return
    if message.text.startswith("/"):
        await message.answer("Unknown command. Try /tools, /games or /cancel.")
        return
    data = await state.get_data()
    tool = data.get("tool")
    if tool not in TOOLS:
        await state.clear()
        await message.answer("Choose a text tool below.", reply_markup=TEXT_MENU)
        return
    await message.answer(process_text(tool, message.text))


@router.message()
async def no_tool_selected(message: Message) -> None:
    await message.answer(FEATURE_NOTICE, reply_markup=NAV_MENU)


async def safely_apply(label: str, operation: Awaitable[bool]) -> None:
    try:
        await operation
        logger.info("Updated Telegram bot %s.", label)
    except TelegramAPIError:
        logger.exception("Could not update bot %s; check BotFather or API permissions.", label)


async def configure_bot(bot: Bot) -> None:
    # Do not change the BotFather name, About, or descriptions.
    await safely_apply(
        "commands",
        bot.set_my_commands(commands=[
            BotCommand(command="start", description="Open GK9 features"),
            BotCommand(command="tools", description="Use three text tools"),
            BotCommand(command="games", description="View games and external links"),
            BotCommand(command="help", description="How GK9 works"),
            BotCommand(command="about", description="About GK9"),
            BotCommand(command="cancel", description="Leave the active text tool"),
        ]),
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
