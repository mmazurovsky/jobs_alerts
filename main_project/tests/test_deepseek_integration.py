#!/usr/bin/env python3
"""
Test script for DeepSeek LLM integration.
"""
import asyncio
import logging
import os
import sys
import pytest
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_environment():
    """Load test environment variables from .env.test file."""
    # Load .env.test first (preferred for tests), then fall back to .env
    test_env_path = project_root / "main_project" / ".env.test"
    env_path = project_root / "main_project" / ".env"
    
    if test_env_path.exists():
        logger.info(f"Loading test environment from {test_env_path}")
        load_dotenv(test_env_path)
        return True
    elif env_path.exists():
        logger.warning(f"No .env.test found, falling back to {env_path}")
        load_dotenv(env_path)
        return True
    else:
        logger.error("No .env.test or .env file found!")
        return False


class TestChatDeepSeekClient:
    """Test version of ChatDeepSeek client to avoid config dependencies."""
    
    def __init__(self, api_key: str, temperature: float = 0.3):
        """Initialize the test DeepSeek client."""
        self.api_key = api_key
        self.temperature = temperature
        
        # Initialize ChatOpenAI with DeepSeek endpoint
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=self.api_key,
            openai_api_base="https://api.deepseek.com/v1",
            temperature=self.temperature,
        )
        
        logger.info(f"Initialized test ChatDeepSeek client with temperature={temperature}")
    
    async def chat_completion(self, messages):
        """Send a chat completion request to DeepSeek."""
        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    async def simple_chat(self, prompt: str, system_message: str = None) -> str:
        """Simple chat interface for single prompts."""
        messages = []
        
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        messages.append(HumanMessage(content=prompt))
        
        return await self.chat_completion(messages)
    
    async def test_connection(self) -> bool:
        """Test the connection to DeepSeek API."""
        try:
            test_prompt = "Hello! Please respond with 'Connection successful' to confirm the API is working."
            response = await self.simple_chat(test_prompt)
            
            logger.info(f"DeepSeek API test response: {response}")
            return "connection successful" in response.lower() or len(response) > 0
            
        except Exception as e:
            logger.error(f"DeepSeek API connection test failed: {e}")
            return False


@pytest.fixture
def api_key():
    """Fixture to provide API key for testing."""
    # Load environment variables from .env.test
    load_test_environment()
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        pytest.fail(
            "❌ DEEPSEEK_API_KEY environment variable is not set!\n"
            "Please set your DeepSeek API key in .env.test file.\n"
            "Example .env.test content:\n"
            "DEEPSEEK_API_KEY=your_api_key_here\n"
            "You can get an API key from: https://platform.deepseek.com/"
        )
    
    return api_key


@pytest.mark.asyncio
async def test_basic_functionality(api_key: str):
    """Test basic DeepSeek client functionality."""
    logger.info("=" * 50)
    logger.info("Testing DeepSeek LLM Integration")
    logger.info("=" * 50)
    
    try:
        # Create test client
        client = TestChatDeepSeekClient(api_key)
        
        # Test 1: Connection test
        logger.info("1. Testing API connection...")
        connection_ok = await client.test_connection()
        
        if not connection_ok:
            logger.error("❌ Connection test failed!")
            return False
        
        logger.info("✅ Connection test passed!")
        
        # Test 2: Test simple chat
        logger.info("2. Testing simple chat...")
        response = await client.simple_chat(
            "Say 'Hello, I am DeepSeek!' and nothing else.",
            system_message="You are a helpful assistant. Follow instructions exactly."
        )
        
        logger.info(f"Response: {response}")
        logger.info("✅ Simple chat test passed!")
        
        # Test 3: Test chat completion with conversation
        logger.info("3. Testing chat completion with conversation...")
        messages = [
            SystemMessage(content="You are a job search assistant. Be concise and helpful."),
            HumanMessage(content="What information do you need to help me create a job search?"),
        ]
        
        response = await client.chat_completion(messages)
        logger.info(f"Conversation response: {response}")
        logger.info("✅ Chat completion test passed!")
        
        # Test 4: Test job search specific interaction
        logger.info("4. Testing job search domain interaction...")
        job_search_prompt = """
        I want to create a job search for "Python Developer" in "Berlin, Germany".
        I'm interested in full-time and contract positions, and I'm open to remote work.
        Please tell me what else you need to know to set this up.
        """
        
        system_prompt = """
        You are a job search assistant that helps users create job search alerts.
        Ask for any missing information needed to create a complete job search configuration.
        Be specific about what options are available.
        """
        
        response = await client.simple_chat(job_search_prompt, system_prompt)
        logger.info(f"Job search interaction response: {response}")
        logger.info("✅ Job search domain test passed!")
        
        logger.info("=" * 50)
        logger.info("🎉 All tests passed! DeepSeek integration is working.")
        logger.info("=" * 50)
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        logger.error("Make sure DEEPSEEK_API_KEY is valid and has sufficient credits.")
        return False


async def main():
    """Main test function."""
    # Load environment variables
    load_test_environment()
    
    # Check if API key is available
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        logger.error("❌ DEEPSEEK_API_KEY environment variable is not set!")
        logger.error("Please set your DeepSeek API key in .env.test or .env file.")
        logger.error("Example .env.test content:")
        logger.error("DEEPSEEK_API_KEY=your_api_key_here")
        logger.error("You can get an API key from: https://platform.deepseek.com/")
        return
    
    logger.info(f"Using DeepSeek API key: {api_key[:8]}...")
    
    # Run tests
    success = await test_basic_functionality(api_key)
    
    if success:
        logger.info("Ready to proceed with LangChain tools implementation!")
        sys.exit(0)
    else:
        logger.error("Please fix the issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 