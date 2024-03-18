from aiogram.filters import Filter
from aiogram.types import Message


class Text(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.text is not None


class Media(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.audio or message.document or message.video or message.voice
