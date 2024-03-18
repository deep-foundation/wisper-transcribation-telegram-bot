import asyncio
import logging
import os
import sys
import tempfile
from typing import Any

import aiofiles
import openai
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

import Filters as ContentTypesFilter
import db
import openai_requests
import yandex_requests
from Pay_Fait import auth_and_check_goods
from file_utils import process_media_file, send_or_split_message

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
openai.api_type = "azure"
openai.api_key = os.getenv('OPENAI_API_KEY')
openai.api_base = "https://deep-azure.openai.azure.com/"
openai.api_version = "2023-06-01-preview"

BIG_FILE_LOG = "file is too big"


class Form(StatesGroup):
    email = State()
    password = State()
    feedback = State()


dp = Dispatcher()

TOKEN = os.getenv("TELEGRAM_TOKEN")
# Initialize Bot instance with a default parse mode which will be passed to all API calls
bot = Bot(TOKEN, parse_mode=ParseMode.HTML)

router = Router(name=__name__)


@router.message(Command("help"))
async def handle_help(message: Message) -> Any:
    answer = (
        """
Привет. Что я могу делать? 
Отправь мне сообщение с видео или аудио и я пришлю тебе в ответ транскрибацию разговора.
А ещё я понимаю о чем шла речь в разговоре и готов ответить на любые вопросы, например, спроси меня: "О чем шла речь?" "О чем договорились? ". 
Меня можно развернуть изолированно и интегрировать с любыми CRM.
""")
    await message.answer(answer, reply_to_message_id=message.message_id)


@router.message(Command("feedback"))
async def start_feedback(message: Message, state: FSMContext) -> Any:
    await state.set_state(Form.feedback)
    await message.answer("Please write your feedback.")


@router.message(Form.feedback)
async def process_feedback(message: Message, state: FSMContext) -> Any:
    feedback_channel_id = os.getenv("FEEDBACK_CHANNEL_ID")
    await bot.send_message(feedback_channel_id, message.text)
    await message.answer("Your feedback has been sent. Thank you!")
    await state.clear()


@router.message(Command("buy"))
async def handle_buy_command(message: Message) -> Any:
    builder = InlineKeyboardBuilder()
    builder.button(text="Подписка 30 минут в день 800 рублей в месяц", callback_data="test1")
    builder.button(text="Подписка 60 минут в день 1700 рублей в месяц", callback_data="test2")
    builder.button(text="Подписка 120 минут в день 2500 рублей в месяц", callback_data="test3")
    markup = builder.as_markup()
    await message.answer("Выберите опцию:", reply_markup=markup)


@router.message(Command("balance"))
async def handle_balance_command(message: Message) -> Any:
    user_id = message.from_user.id
    max_minutes, used_minutes = await db.async_get_user_minutes(user_id)
    await message.answer(f"Максимум минут: {max_minutes}\nИспользовано минут: {used_minutes}")


@router.message(Command("sub"))
async def handle_sub_command(message: Message) -> Any:
    user_id = message.from_user.id
    user_email = await db.async_get_user_email(user_id)
    user_password = db.get_user_password(user_id)
    response = await auth_and_check_goods(user_id, user_email, user_password)
    goods = response["data"]["goods"]
    your_goods = ""
    for good in goods:
        your_goods += f"{good['name']}\n"
    if goods is None:
        return False
    else:
        await message.answer(f"Ваши подписки:\n{your_goods}")


@router.callback_query()
async def handle_callback_query(callback_query: CallbackQuery) -> Any:
    data = callback_query.data
    if data == "test1":
        await callback_query.message.answer("Вы выбрали 1")
    elif data == "test2":
        await callback_query.message.answer("Вы выбрали 2")
    elif data == "test3":
        await callback_query.message.answer("Вы выбрали 3")
    await callback_query.answer()


async def get_media_from_message(message: Message) -> Any:
    """
    Extracts the media from the given message.
    """
    media_types = {"audio": message.audio, "video": message.video, "voice": message.voice}
    media = next((media for media_type, media in media_types.items() if media), None)
    if message.document and ('video' in message.document.mime_type or 'audio' in message.document.mime_type):
        media = message.document
    return media


async def process_media_message(bot, message: Message, media: Any) -> None:
    """
    Processes the given media message.
    """
    try:
        await process_media_file(bot, message, media)
    except Exception as e:
        if BIG_FILE_LOG in str(e):
            await message.answer(BIG_FILE_LOG, reply_to_message_id=message.message_id)
            logger.error(e)
        else:
            logger.error(e)
        await bot.send_message(chat_id=os.getenv("ERRORS_CHAT_ID"), text=f"Failed to process media message {e}")


@router.message(ContentTypesFilter.Media())
async def handle_media(message: Message, state: FSMContext) -> Any:
    """
    Handles media messages.
    """
    if await have_valid_email_and_auth(message, state):
        media = await get_media_from_message(message)
        if media:
            await process_media_message(bot, message, media)


@router.message(Form.email)
async def process_email(message: Message, state: FSMContext) -> Any:
    logger.info(f"Processing email for user {message.from_user.id}")
    email = message.text
    user_id = message.from_user.id

    try:
        if "@" in email and "." in email:
            await db.async_add_user(user_id, email)
            await message.answer("Your email has been saved. Please provide your password.")
        else:
            await message.answer("Please provide a valid email.")
    except Exception as e:
        logger.error(f"Error processing email: {e}")
        await message.answer("Произошла ошибка при обработке email.")
    finally:
        await state.set_state(Form.password)
        logger.info(f"State set to 'password' for user {user_id}")


@router.message(Form.password)
async def process_password(message: Message, state: FSMContext) -> Any:
    logger.info(f"Processing password for user {message.from_user.id}")
    password = message.text
    user_id = message.from_user.id

    try:
        db.add_user_password(user_id, password)
        await message.answer("Your password has been saved.")
    except Exception as e:
        logger.error(f"Error processing password: {e}")
        await message.answer("Произошла ошибка при обработке пароля.")
    finally:
        await state.clear()
        logger.info(f"State finished for user {user_id}")


async def have_valid_email_and_auth(message, state):
    user_id = message.from_user.id
    user_email = await db.async_get_user_email(user_id)
    user_password = db.get_user_password(user_id)
    if user_email is None:
        await state.set_state(Form.email)
        logger.info(f"State set to 'email' for user {user_id}")
        await message.answer("Please provide your email.")
        return False
    response = await auth_and_check_goods(user_id, user_email, user_password)
    if response is None:
        return False
    return True


@router.message(ContentTypesFilter.Text())
async def handle_text(message: Message, state: FSMContext) -> Any:
    if await have_valid_email_and_auth(message, state):
        if message.reply_to_message:
            try:
                context = await extract_context(message)
                prompt = f"Context: \n{context}\nPrompt:\n{message.text}"
                answer = await yandex_requests.get_completion(prompt)
                await send_or_split_message(message, answer)
            except Exception as e:
                logger.error(f"Failed to get Yandex completion: {e}")
                await message.answer("Произошла ошибка при обработке запроса.")
                await bot.send_message(chat_id=os.getenv("ERRORS_CHAT_ID"), text=f"Failed to process text message {e}")


async def extract_context(message: Message) -> str:
    if message.reply_to_message.document:
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            await bot.download(message.reply_to_message.document, temp_file.name)
            async with aiofiles.open(temp_file.name, 'r', encoding='utf-8') as file:
                return await file.read()
    return message.reply_to_message.text


async def main() -> None:
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.ERROR)
    httpx_logger.propagate = True
    asyncio.run(main())
