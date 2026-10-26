"""GK9 Telegram bot: three useful text tools, no external redirects."""

import asyncio
import logging
import os
from collections.abc import Awaitable

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, KeyboardButton, Message, ReplyKeyboardMarkup

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
    "Choose one of the three tools below:\n"
    "Change Case - uppercase, lowercase, and title case.\n"
    "Count Words - word, character, and line counts.\n"
    "Clean Text - remove extra spaces and blank lines.\n\n"
    "Tap a button to begin."
)

MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=CHANGE_CASE)],
        [KeyboardButton(text=COUNT_WORDS)],
        [KeyboardButton(text=CLEAN_TEXT)],
    ],
    resize_keyboard=True,
    input_field_placeholder="Choose a GK9 text tool",
)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)
logger = logging.getLogger(__name__)


class WorkState(StatesGroup):
    awaiting_text = State()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=MENU)


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        WELCOME
        + "\n\nAfter choosing a tool, send up to "
        + str(MAX_INPUT_LENGTH)
        + " characters. Use /cancel to return to the menu.",
        reply_markup=MENU,
    )


@router.message(Command("about"))
async def about_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        BOT_NAME + "\n" + BOT_ABOUT + "\n\nChoose a tool below to start.",
        reply_markup=MENU,
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Tool cancelled. Choose a tool below.", reply_markup=MENU)


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
        reply_markup=MENU,
    )


@router.message(WorkState.awaiting_text)
async def handle_text(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await message.answer("Please send a text message to use this tool.", reply_markup=MENU)
        return

    if message.text.startswith("/"):
        await message.answer(
            "Unknown command. Send text, choose another tool, or use /cancel.",
            reply_markup=MENU,
        )
        return

    data = await state.get_data()
    tool = data.get("tool")
    if tool not in TOOLS:
        await state.clear()
        await message.answer("Choose a tool below first.", reply_markup=MENU)
        return

    result = process_text(tool, message.text)
    await message.answer(result, reply_markup=MENU)


@router.message()
async def no_tool_selected(message: Message) -> None:
    await message.answer("Choose one of the three text tools below to begin.", reply_markup=MENU)


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

    async with Bot(token=token) as bot:
        identity = await bot.get_me()
        if (identity.username or "").casefold() != BOT_USERNAME.casefold():
            raise RuntimeError(
                "This token belongs to @"
                + str(identity.username)
                + ", not @"
                + BOT_USERNAME
                + ". Refusing to modify another bot."
            )

        await bot.delete_webhook(drop_pending_updates=False)
        await configure_bot(bot)
        logger.info("GK9 polling started as @%s", identity.username)
        await dp.start_polling(bot, close_bot_session=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())
