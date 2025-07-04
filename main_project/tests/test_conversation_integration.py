"""
Integration tests for conversation flow with real DeepSeek API calls.
Tests common user inputs to ensure they don't result in validation errors.
"""
import asyncio
import logging
import os
import sys
import pytest
import pytest_asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables BEFORE importing modules that need config
from dotenv import load_dotenv

# Load test environment first
test_env_path = project_root / "main_project" / ".env.test"
env_path = project_root / "main_project" / ".env"

if test_env_path.exists():
    print(f"Loading test environment from {test_env_path}")
    load_dotenv(test_env_path)
elif env_path.exists():
    print(f"Loading environment from {env_path}")
    load_dotenv(env_path)
else:
    print("No .env or .env.test file found, using system environment variables")

# Set default test values if not found in environment
if not os.getenv('MONGO_URL'):
    os.environ['MONGO_URL'] = 'mongodb://localhost:27017/jobs_alerts_test'
    
if not os.getenv('TELEGRAM_BOT_TOKEN'):
    os.environ['TELEGRAM_BOT_TOKEN'] = '1234567890:TEST-BOT-TOKEN-FOR-TESTING'

# Now import modules that need config
from main_project.app.llm.job_search_agent import JobSearchAgent
from main_project.app.core.job_search_manager import JobSearchManager
from main_project.app.core.mongo_connection import MongoConnection
from main_project.app.core.stores.job_search_store import JobSearchStore
from main_project.app.core.stores.sent_jobs_store import SentJobsStore
from main_project.app.schedulers.job_search_scheduler import JobSearchScheduler
from shared.data import StreamManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def api_key():
    """Fixture to provide API key for testing."""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        pytest.fail(
            "❌ DEEPSEEK_API_KEY environment variable is not set!\\n"
            "Please set your DeepSeek API key in .env.test file.\\n"
            "Example .env.test content:\\n"
            "DEEPSEEK_API_KEY=your_api_key_here\\n"
            "You can get an API key from: https://platform.deepseek.com/"
        )
    
    return api_key


@pytest_asyncio.fixture
async def job_search_manager():
    """Fixture to provide JobSearchManager instance for testing."""
    
    # Initialize MongoDB connection
    mongo_conn = MongoConnection()
    try:
        await mongo_conn.connect()
        
        # Create the required stores
        job_search_store = JobSearchStore(mongo_conn)
        sent_jobs_store = SentJobsStore(mongo_conn)
        
        # Create a minimal stream manager for testing
        stream_manager = StreamManager()
        
        # Create the scheduler
        scheduler = JobSearchScheduler(stream_manager=stream_manager, sent_jobs_store=sent_jobs_store)
        
        # Initialize the scheduler (but don't start it for tests)
        # We skip scheduler.initialize() to avoid starting the actual scheduler
        
        # Create the job search manager with proper dependencies
        manager = JobSearchManager(job_search_store=job_search_store, job_search_scheduler=scheduler)
        
        yield manager
    finally:
        await mongo_conn.close()


@pytest_asyncio.fixture
async def agent(job_search_manager, api_key):
    """Fixture to provide initialized JobSearchAgent."""
    agent = JobSearchAgent(job_search_manager)
    await agent.initialize()
    return agent


# Test data for common user inputs
COMMON_USER_INPUTS = [
    # Basic greetings and help
    ("hello", "greeting"),
    ("hi there", "greeting"),
    ("help", "help_request"),
    ("what can you do?", "help_request"),
    
    # List operations
    ("list my job searches", "list_operation"),
    ("show my searches", "list_operation"),
    ("what searches do I have?", "list_operation"),
    ("show me my job alerts", "list_operation"),
    
    # General job search questions
    ("I want to find a job", "general_inquiry"),
    ("help me search for jobs", "general_inquiry"),
    ("I need a new job", "general_inquiry"),
    
    # Specific job search creation (should ask for confirmation)
    ("create a search for python developer in berlin", "create_request"),
    ("I want to search for data scientist jobs in london", "create_request"),
    ("find me software engineer positions in new york", "create_request"),
    
    # Delete operations
    ("delete my search", "delete_request"),
    ("remove a job search", "delete_request"),
    
    # Details operations
    ("show me details of my search", "details_request"),
    ("get more info about my job alert", "details_request"),
    
    # One-time search
    ("search for jobs right now", "onetime_search"),
    ("find me current openings", "onetime_search"),
]


class TestConversationIntegration:
    """Integration tests for conversation flow."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent, api_key):
        """Test that the agent initializes correctly without errors."""
        assert agent is not None
        assert agent.agent_executor is not None
        assert agent.llm is not None
        assert len(agent.tools) > 0
        
        # Test that the agent has all expected tools
        tool_names = [tool.name for tool in agent.tools]
        expected_tools = [
            "list_job_searches",
            "create_job_search", 
            "delete_job_search",
            "get_job_search_details",
            "one_time_search"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing tool: {expected_tool}"
    
    @pytest.mark.asyncio
    async def test_common_inputs_no_validation_errors(self, agent):
        """Test that common user inputs don't result in validation errors."""
        test_user_id = 12345
        
        for user_input, input_type in COMMON_USER_INPUTS:
            logger.info(f"Testing input: '{user_input}' (type: {input_type})")
            
            try:
                response = await agent.chat(test_user_id, user_input)

                # Handle empty responses (LLM can occasionally return empty responses)
                if not response or len(response.strip()) <= 10:
                    logger.warning(f"⚠️ Empty/short response for input '{user_input}', retrying once...")
                    await asyncio.sleep(1)
                    response = await agent.chat(test_user_id, user_input)

                # Verify response is not empty after retry
                assert response and len(response.strip()) > 10, f"Empty/short response for input: '{user_input}'"

                # Verify no validation error occurred
                assert "❌ **Input Validation Issue**" not in response, f"Validation error for input: '{user_input}'"
                assert "There seems to be an issue with your request" not in response, f"Request issue for input: '{user_input}'"

                logger.info(f"✅ Input '{user_input}' handled successfully")

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.5)

            except Exception as e:
                pytest.fail(f"Exception occurred for input '{user_input}': {e}")
    
    @pytest.mark.asyncio
    async def test_greeting_responses(self, agent):
        """Test that greeting inputs receive appropriate responses."""
        test_user_id = 12345
        greeting_inputs = ["hello", "hi", "hey there", "good morning"]
        
        for greeting in greeting_inputs:
            response = await agent.chat(test_user_id, greeting)
            
            # Should not be a validation error
            assert "❌ **Input Validation Issue**" not in response
            
            # Should contain helpful job search related content
            response_lower = response.lower()
            job_search_keywords = ["job", "search", "help", "assist", "alert"]
            
            has_job_keyword = any(keyword in response_lower for keyword in job_search_keywords)
            assert has_job_keyword, f"Greeting response should mention job search capabilities: {response}"
            
            await asyncio.sleep(0.5)
    
    @pytest.mark.asyncio
    async def test_list_operations(self, agent):
        """Test that list operations work correctly."""
        test_user_id = 12345
        list_inputs = [
            "list my job searches",
            "show my searches", 
            "what searches do I have?",
            "show me my job alerts"
        ]
        
        for list_input in list_inputs:
            response = await agent.chat(test_user_id, list_input)
            
            # Should not be a validation error
            assert "❌ **Input Validation Issue**" not in response
            
            # For list operations, the main goal is no validation errors
            # The response content can vary but should be helpful
            assert len(response.strip()) > 20, f"Response too short for input: '{list_input}'"
            
            # Should either indicate empty list OR show searches OR offer to create one
            response_lower = response.lower()
            is_helpful_response = (
                "search" in response_lower and (
                    "don't have" in response_lower or
                    "no " in response_lower or
                    "create" in response_lower or
                    "here are" in response_lower or
                    "your " in response_lower
                )
            )
            
            assert is_helpful_response, f"Response should be helpful about job searches: {response}"
            
            await asyncio.sleep(0.5)
    
    @pytest.mark.asyncio 
    async def test_create_job_search_flow(self, agent):
        """Test that job search creation requests are handled properly."""
        test_user_id = 12345
        create_inputs = [
            "create a search for python developer in berlin",
            "I want to search for data scientist jobs in london"
        ]
        
        for create_input in create_inputs:
            response = await agent.chat(test_user_id, create_input)
            
            # Should not be a validation error
            assert "❌ **Input Validation Issue**" not in response
            
            # Should either ask for confirmation or more details
            response_lower = response.lower()
            is_valid_create_response = (
                "create this alert" in response_lower or
                "confirm" in response_lower or
                "yes/no" in response_lower or
                "more information" in response_lower or
                "need to know" in response_lower
            )
            
            assert is_valid_create_response, f"Invalid create response: {response}"
            
            await asyncio.sleep(0.5)
    
    @pytest.mark.asyncio
    async def test_help_requests(self, agent):
        """Test that help requests receive appropriate responses."""
        test_user_id = 12345
        help_inputs = ["help", "what can you do?", "how does this work?", "commands"]
        
        for help_input in help_inputs:
            response = await agent.chat(test_user_id, help_input)
            
            # Should not be a validation error
            assert "❌ **Input Validation Issue**" not in response
            
            # Should contain helpful information about capabilities
            response_lower = response.lower()
            help_keywords = ["create", "list", "delete", "search", "alert", "job", "can help"]
            
            has_help_content = any(keyword in response_lower for keyword in help_keywords)
            assert has_help_content, f"Help response should contain capability information: {response}"
            
            await asyncio.sleep(0.5)
    
    @pytest.mark.asyncio
    async def test_off_topic_handling(self, agent):
        """Test that off-topic requests are handled gracefully."""
        test_user_id = 12345
        off_topic_inputs = [
            "what's the weather like?",
            "tell me a joke",
            "how to cook pasta?",
            "what is python programming?"
        ]
        
        for off_topic_input in off_topic_inputs:
            response = await agent.chat(test_user_id, off_topic_input)
            
            # Should redirect to job search topics
            response_lower = response.lower()
            is_redirect = (
                "job search assistant" in response_lower or
                "help with your job search" in response_lower or
                "job search" in response_lower and ("only" in response_lower or "focus" in response_lower)
            )
            
            assert is_redirect, f"Off-topic input should be redirected to job search: {response}"
            
            await asyncio.sleep(0.5)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, agent):
        """Test that rate limiting works properly without breaking functionality."""
        test_user_id = 12345
        
        # Send multiple requests quickly
        responses = []
        for i in range(5):
            response = await agent.chat(test_user_id, f"hello {i}")
            responses.append(response)
            
        # All responses should be valid (rate limiting should be reasonable for tests)
        for i, response in enumerate(responses):
            assert response, f"Empty response for request {i}"
            # Rate limiting messages are acceptable but not required for this volume
            if "Rate Limit Exceeded" not in response:
                assert "❌ **Input Validation Issue**" not in response, f"Validation error in request {i}"


if __name__ == "__main__":
    # Run a simple test if called directly
    async def main():
        # Test environment loading
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            print("❌ DEEPSEEK_API_KEY not found in environment")
            return
        
        print("✅ Environment loaded successfully")
        print("✅ DeepSeek API key found")
        print("🧪 Run full tests with: python -m pytest main_project/tests/test_conversation_integration.py -v")
    
    asyncio.run(main()) 