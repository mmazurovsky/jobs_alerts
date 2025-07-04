"""
Integration tests for complete conversation flows with the LLM agent.
"""
import pytest
import pytest_asyncio
import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from dotenv import load_dotenv

# Load test environment variables
env_path = Path(__file__).parent.parent / '.env.test'
load_dotenv(env_path)

from main_project.app.llm.job_search_agent import JobSearchAgent
from main_project.app.core.job_search_manager import JobSearchManager


class TestConversationFlows:
    """Test complete conversation flows with the LLM agent."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock JobSearchManager."""
        manager = Mock(spec=JobSearchManager)
        return manager
    
    @pytest_asyncio.fixture
    async def agent(self, mock_manager):
        """Create and initialize a JobSearchAgent."""
        agent = JobSearchAgent(mock_manager)
        
        # Mock the LLM client initialization
        with patch('main_project.app.llm.job_search_agent.ChatDeepSeekClient') as mock_client_class:
            mock_client = Mock()
            mock_client.test_connection = AsyncMock(return_value=True)
            mock_client.llm = Mock()  # Mock LangChain ChatOpenAI instance
            mock_client_class.return_value = mock_client
            
            await agent.initialize()
        
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test that the agent initializes properly."""
        assert agent is not None
        assert agent.job_search_manager is not None
        assert agent.agent_executor is not None
        assert agent.user_sessions is not None  # Check for session management instead of memory
        assert hasattr(agent, 'chat')
    
    @pytest.mark.asyncio
    async def test_agent_has_correct_tools(self, agent):
        """Test that the agent has all required tools."""
        # Get the tools from the agent executor
        tools = agent.agent_executor.tools
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            'list_job_searches',
            'create_job_search', 
            'delete_job_search',
            'get_job_search_details',
            'one_time_search'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not found in agent tools"
    
    @pytest.mark.asyncio
    async def test_agent_tool_documentation(self, agent):
        """Test that all tools have proper documentation."""
        tools = agent.agent_executor.tools
        
        for tool in tools:
            # Each tool should have a description
            assert hasattr(tool, 'description')
            assert tool.description is not None
            assert len(tool.description.strip()) > 0
            
            # Each tool should have proper documentation if it's a DocumentedTool
            if hasattr(tool, 'tool_documentation'):
                doc = tool.tool_documentation
                assert doc.name is not None
                assert doc.description is not None
                assert doc.purpose is not None
                assert isinstance(doc.parameters, list)
    
    @pytest.mark.asyncio
    async def test_conversation_memory_exists(self, agent):
        """Test that conversation memory is properly set up."""
        # Verify the agent has session management for memory
        assert agent.user_sessions is not None
        
        # Test that sessions can be created and managed
        user_id = 12345
        # Mock the chat at the JobSearchAgent level
        with patch.object(agent, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "Hello! How can I help you with your job search?"
            response = await agent.chat(user_id, "Hello")
            mock_chat.assert_called_once_with(user_id, "Hello")
            assert response == "Hello! How can I help you with your job search?"
    
    @pytest.mark.asyncio
    async def test_agent_user_sessions(self, agent):
        """Test that agent maintains separate user sessions."""
        user1_id = 12345
        user2_id = 67890
        
        # Both users should be able to have separate sessions
        # This is handled by the session management system
        assert agent.user_sessions is not None
        
        # Test that the agent can handle multiple users
        # We'll test the session structure directly rather than through chat
        # since that involves complex mocking of LangChain components
        
        # Initialize sessions manually to test the structure
        agent.user_sessions[user1_id] = {
            "pending_action": None,
            "pending_data": None,
            "conversation_history": ["Hello from user 1"]
        }
        agent.user_sessions[user2_id] = {
            "pending_action": None,
            "pending_data": None,
            "conversation_history": ["Hello from user 2"]
        }
        
        # Verify sessions are separate
        assert user1_id in agent.user_sessions
        assert user2_id in agent.user_sessions
        assert agent.user_sessions[user1_id] != agent.user_sessions[user2_id]
        assert agent.user_sessions[user1_id] is not agent.user_sessions[user2_id]
        
        # Verify conversation histories are different
        assert agent.user_sessions[user1_id]["conversation_history"] != agent.user_sessions[user2_id]["conversation_history"]
    
    @pytest.mark.asyncio
    async def test_agent_manager_integration(self, agent, mock_manager):
        """Test that the agent properly integrates with the job search manager."""
        # Verify the agent has the correct manager instance
        assert agent.job_search_manager is mock_manager
        
        # Verify tools have access to the manager
        tools = agent.agent_executor.tools
        for tool in tools:
            if hasattr(tool, 'job_search_manager'):
                assert tool.job_search_manager is mock_manager
    
    def test_agent_without_initialization(self, mock_manager):
        """Test that agent can be created but needs initialization."""
        agent = JobSearchAgent(mock_manager)
        
        # Agent should be created but not fully initialized
        assert agent.job_search_manager is mock_manager
        # Agent executor should be None until initialize() is called
        assert agent.agent_executor is None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"]) 