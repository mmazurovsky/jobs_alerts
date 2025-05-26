import pytest
import asyncio
from unittest.mock import MagicMock
from src.bot.telegram_bot import TelegramBot, ADMIN_USER_ID
from src.data.data import StreamEvent, StreamType, StreamManager
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

@pytest.mark.asyncio
async def test_handle_send_log_message_only():
    bot = TelegramBot(
        token=TELEGRAM_BOT_TOKEN,
        stream_manager=StreamManager(),
        job_search_manager=MagicMock()
    )
    event = StreamEvent(
        type=StreamType.SEND_LOG,
        data={"message": "Test log message"},
        source="test"
    )
    await bot._handle_send_log(event)

@pytest.mark.asyncio
async def test_handle_send_log_with_image():
    image_path = os.path.join("screenshots", "test.png")
    assert os.path.exists(image_path), f"Image file {image_path} does not exist."
    bot = TelegramBot(
        token=TELEGRAM_BOT_TOKEN,
        stream_manager=StreamManager(),
        job_search_manager=MagicMock()
    )
    event = StreamEvent(
        type=StreamType.SEND_LOG,
        data={"message": "Test log with image", "image_path": image_path},
        source="test"
    )
    await bot._handle_send_log(event)

@pytest.mark.asyncio
async def test_send_message_stream_triggers_handler():
    stream_manager = StreamManager()
    bot = TelegramBot(
        token=TELEGRAM_BOT_TOKEN,
        stream_manager=stream_manager,
        job_search_manager=MagicMock()
    )
    user_id = 123456789
    event = StreamEvent(
        type=StreamType.SEND_MESSAGE,
        data={"user_id": user_id, "message": "Stream test"},
        source="test"
    )
    stream_manager.publish(event)
    await asyncio.sleep(0.1) 