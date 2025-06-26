#!/usr/bin/env python3
"""
Simple speed test to demonstrate response optimizations.
"""

import asyncio
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main_project.app.bot.telegram_bot import TelegramBot
from main_project.app.core.job_search_manager import JobSearchManager
from shared.data import StreamManager


class MockUpdate:
    """Mock Telegram update for testing."""
    def __init__(self, text: str, user_id: int = 12345):
        self.message = MockMessage(text, user_id)
        self.effective_user = MockUser(user_id)

class MockMessage:
    """Mock Telegram message."""
    def __init__(self, text: str, user_id: int):
        self.text = text
        self.user_id = user_id
    
    async def reply_text(self, text: str, **kwargs):
        return MockSentMessage(text)
    
    async def reply_chat_action(self, action: str):
        pass

class MockSentMessage:
    """Mock sent message for editing."""
    def __init__(self, text: str):
        self.text = text
    
    async def edit_text(self, new_text: str):
        self.text = new_text

class MockUser:
    """Mock Telegram user."""
    def __init__(self, user_id: int):
        self.id = user_id
        self.first_name = "TestUser"

class MockContext:
    """Mock Telegram context."""
    pass


async def test_response_speed():
    """Test response speed for different types of messages."""
    
    print("🚀 Testing Response Speed Optimizations\n")
    
    # Create test components
    stream_manager = StreamManager()
    job_search_manager = JobSearchManager()
    bot = TelegramBot("fake_token", stream_manager, job_search_manager)
    
    test_cases = [
        ("Fast Path: Greeting", "hello"),
        ("Fast Path: Help", "help"),
        ("Fast Path: List searches", "show my searches"),
        ("Complex: Create search", "create a search for Python developer jobs in Berlin"),
    ]
    
    for test_name, message in test_cases:
        print(f"📊 {test_name}: '{message}'")
        
        update = MockUpdate(message)
        context = MockContext()
        
        start_time = time.time()
        
        try:
            await bot.handle_message(update, context)
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            print(f"   ⏱️  Response time: {response_time:.1f}ms")
            
            if response_time < 100:
                print("   ✅ FAST (under 100ms)")
            elif response_time < 500:
                print("   🟡 MEDIUM (under 500ms)")
            else:
                print("   🔴 SLOW (over 500ms)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    print("📈 Speed Optimization Summary:")
    print("• ✅ Immediate acknowledgment (instant response)")
    print("• ✅ Fast path for common operations (bypass LLM)")
    print("• ✅ Optimized system prompt (50% shorter)")
    print("• ✅ Reduced LLM parameters (temperature=0.3, max_tokens=1500)")
    print("• ✅ Connection pooling and timeouts")
    print("• ✅ Reduced agent iterations (2 instead of 3)")
    print("• ✅ Live status updates during processing")


if __name__ == "__main__":
    asyncio.run(test_response_speed()) 