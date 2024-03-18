import asyncio
import os
import tempfile
import time
from contextlib import asynccontextmanager

import aiofiles
from aiogram.types import BufferedInputFile
from moviepy.audio.io.AudioFileClip import AudioFileClip

from custom_exceptions import ASRException

import logging

from openai_requests import send_request
from yandex_requests import get_text_from_audio
logger = logging.getLogger(__name__)


async def send_or_split_message(message, text):
    text_file = BufferedInputFile(bytes(text, 'utf-8'), filename="file.txt")
    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            text_chunk = text[i:i + 4096]
            await message.answer(text_chunk, reply_to_message_id=message.message_id)
    else:
        await message.answer(text, reply_to_message_id=message.message_id)
    await message.answer_document(text_file, reply_to_message_id=message.message_id)


@asynccontextmanager
async def temporary_audio_file(source_path: str, target_format: str = '.mp3'):
    with tempfile.NamedTemporaryFile(suffix=target_format, delete=False) as tmp:
        try:
            await asyncio.to_thread(write_audio_file, source_path, tmp.name)
            yield tmp.name
        finally:
            tmp.close()
            time.sleep(1)
            if not os.path.isfile(tmp.name) or not is_file_locked(tmp.name):
                os.remove(tmp.name)


def write_audio_file(source_path, target_path):
    audio = AudioFileClip(source_path)
    audio.write_audiofile(target_path, codec="libmp3lame", bitrate="192k")
    audio.close()


def is_file_locked(filepath):
    locked = False
    if os.path.exists(filepath):
        try:
            os.rename(filepath, filepath)
        except OSError:
            locked = True
    return locked


async def process_media_file(bot, message, media):
    """
    Downloads a media file, processes it (including conversion if necessary), and sends the result.

    :param bot: The bot instance for downloading the file.
    :param message: The message instance from which to respond.
    :param media: The media to download.
    """
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        await bot.download(media, destination=temp_file.name)

        # Process the downloaded file
        async with temporary_audio_file(temp_file.name) as temp_audio_path:
            text = await get_text_from_audio(temp_audio_path)
            await send_or_split_message(message, text)


async def read_file_content(file_path):
    try:    
        async with aiofiles.open(file_path, 'rb') as audio_file:
            return await audio_file.read()
    except FileNotFoundError as exc:
        logger.error(f"Audio file not found: {exc}")
        raise ASRException(f"Audio file not found: {file_path}") from exc
    except IOError as exc:
        logger.error(f"Error reading the audio file: {exc}")
        raise ASRException(f"Error reading the audio file: {file_path}") from exc
