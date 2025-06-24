"""
Security tests for the JobSearchAgent to ensure proper scope restrictions and authorization.
"""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from dotenv import load_dotenv

# Load test environment variables
env_path = Path(__file__).parent.parent / '.env.test'
load_dotenv(env_path)

from main_project.app.llm.job_search_agent import JobSearchAgent, RateLimit
from main_project.app.core.job_search_manager import JobSearchManager


class TestSecurityRestrictions:
    """Test security and scope restrictions."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock JobSearchManager."""
        manager = Mock(spec=JobSearchManager)
        manager.get_user_searches = AsyncMock(return_value=[])
        return manager
    
    @pytest.fixture
    def agent(self, mock_manager):
        """Create a JobSearchAgent instance."""
        return JobSearchAgent(mock_manager)
    
    def test_off_topic_detection_programming(self, agent):
        """Test detection of programming-related off-topic requests."""
        off_topic_messages = [
            "Help me debug this code",
            "I need coding help with my project",
            "Can you write code for me?",
            "Solve this math problem",
            "How to code in Python?"
        ]
        
        for message in off_topic_messages:
            assert agent._is_off_topic_request(message), f"Should detect off-topic: {message}"
    
    def test_off_topic_detection_general(self, agent):
        """Test detection of general off-topic requests."""
        off_topic_messages = [
            "What's the weather like today?",
            "Tell me a joke",
            "Help me with my math problem",
            "Write a poem for me",
            "What do you think about politics?",
            "Translate this to Spanish",
            "What's the meaning of life?"
        ]
        
        for message in off_topic_messages:
            assert agent._is_off_topic_request(message), f"Should detect off-topic: {message}"
    
    def test_off_topic_detection_ai_questions(self, agent):
        """Test detection of AI/system-related questions."""
        off_topic_messages = [
            "How do you work?",
            "What AI model are you?",
            "Who created you?",
            "Are you ChatGPT?",
            "How does gravity work?"
        ]
        
        for message in off_topic_messages:
            assert agent._is_off_topic_request(message), f"Should detect off-topic: {message}"
    
    def test_job_related_messages_allowed(self, agent):
        """Test that job-related messages are properly allowed."""
        job_related_messages = [
            "Show me my job searches",
            "Create a search for Python developer jobs",
            "I need help with my job search",
            "Find me work in Berlin",
            "Delete my search for marketing roles",
            "What jobs are available?",
            "Help me find a new career opportunity"
        ]
        
        for message in job_related_messages:
            assert not agent._is_off_topic_request(message), f"Should allow job-related: {message}"
    
    def test_response_filtering(self, agent):
        """Test filtering of inappropriate responses."""
        off_topic_responses = [
            "I can help you with programming in Python...",
            "Here's how to code a function...",
            "The weather is sunny today...",
            "Here's a joke for you...",
            "As an AI model, I was trained..."
        ]
        
        for response in off_topic_responses:
            assert agent._response_contains_off_topic_content(response), f"Should filter response: {response}"
    
    def test_redirect_response_format(self, agent):
        """Test that redirect response is properly formatted."""
        response = agent._get_redirect_response()
        
        assert "specialized job search assistant" in response
        assert "Create new job search alerts" in response
        assert "How can I help you with your job search today?" in response
    
    def test_rate_limiting_initialization(self, agent):
        """Test rate limiting initialization."""
        user_id = 12345
        
        # First check should pass and initialize
        assert agent._check_rate_limit(user_id)
        assert user_id in agent.rate_limits
        assert len(agent.rate_limits[user_id].requests) == 1
    
    def test_rate_limiting_minute_limit(self, agent):
        """Test minute-based rate limiting."""
        user_id = 12345
        
        # Simulate 10 requests (should all pass)
        for i in range(10):
            assert agent._check_rate_limit(user_id), f"Request {i+1} should pass"
        
        # 11th request should fail
        assert not agent._check_rate_limit(user_id), "11th request should fail minute limit"
    
    def test_rate_limiting_different_users(self, agent):
        """Test that rate limiting is per-user."""
        user1 = 12345
        user2 = 67890
        
        # User 1 hits limit
        for i in range(10):
            agent._check_rate_limit(user1)
        
        # User 1 should be blocked
        assert not agent._check_rate_limit(user1)
        
        # User 2 should still work
        assert agent._check_rate_limit(user2)


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock JobSearchManager."""
        manager = Mock(spec=JobSearchManager)
        manager.get_user_searches = AsyncMock(return_value=[])
        return manager
    
    @pytest.fixture
    def agent(self, mock_manager):
        """Create a JobSearchAgent instance."""
        return JobSearchAgent(mock_manager)
    
    @pytest.mark.asyncio
    async def test_off_topic_request_handling(self, agent):
        """Test that off-topic requests are handled without reaching LLM."""
        user_id = 12345
        off_topic_message = "What's the weather like today?"
        
        # Should get redirect response without initialization
        response = await agent.chat(user_id, off_topic_message)
        
        assert "specialized job search assistant" in response
        assert agent.agent_executor is None  # Should not have initialized LLM
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocking(self, agent):
        """Test that rate limiting blocks excessive requests."""
        user_id = 12345
        
        # Use a simple job-related request to exhaust rate limit
        # (off-topic requests don't reach rate limiting because they're blocked earlier)
        for i in range(10):
            # Use a simple non-LLM request to avoid initialization
            agent._check_rate_limit(user_id)
        
        # Next request should be rate limited
        response = await agent.chat(user_id, "list my searches")
        
        assert "Rate Limit Exceeded" in response
        assert "10 requests per minute" in response 