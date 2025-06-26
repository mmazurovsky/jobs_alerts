"""
Comprehensive unit tests for LangChain tools functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import List
from datetime import datetime, timezone

# Import the tools
from main_project.app.llm.tools import (
    ListJobSearchesTool,
    CreateJobSearchTool,
    DeleteJobSearchTool,
    GetJobSearchDetailsTool,
    OneTimeSearchTool
)
from main_project.app.llm.tools.tool_registry import create_tool_registry
from main_project.app.core.job_search_manager import JobSearchManager
from shared.data import JobType, RemoteType, TimePeriod


class TestToolRegistry:
    """Test the tool registry functionality."""
    
    def test_tool_registry_creation(self):
        """Test creating a tool registry with all tools."""
        mock_manager = Mock(spec=JobSearchManager)
        registry = create_tool_registry(mock_manager)
        
        assert registry is not None
        assert len(registry.tools) == 5
        
        expected_tools = [
            'list_job_searches',
            'create_job_search', 
            'delete_job_search',
            'get_job_search_details',
            'one_time_search'
        ]
        
        for tool_name in expected_tools:
            assert tool_name in registry.tools


class TestListJobSearchesTool:
    """Test the ListJobSearchesTool functionality."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock JobSearchManager."""
        manager = Mock(spec=JobSearchManager)
        return manager
    
    @pytest.fixture
    def tool(self, mock_manager):
        """Create a ListJobSearchesTool instance."""
        return ListJobSearchesTool(mock_manager)
    
    @pytest.mark.asyncio
    async def test_list_searches_success(self, tool, mock_manager):
        """Test successful listing of job searches."""
        # Create mock search objects with proper attributes
        from shared.data import JobType, RemoteType, TimePeriod
        
        class MockJobSearch:
            def __init__(self, id, job_title, location, job_types, remote_types, time_period):
                self.id = id
                self.job_title = job_title
                self.location = location
                self.job_types = job_types
                self.remote_types = remote_types
                self.time_period = time_period
                self.filter_text = None
        
        mock_searches = [
            MockJobSearch(
                id='search1',
                job_title='Python Developer',
                location='Berlin',
                job_types=[JobType.parse('Full-time')],
                remote_types=[RemoteType.parse('Hybrid')],
                time_period=TimePeriod.parse('1 hour')
            ),
            MockJobSearch(
                id='search2', 
                job_title='Data Scientist',
                location='Remote',
                job_types=[JobType.parse('Full-time')],
                remote_types=[RemoteType.parse('Remote')],
                time_period=TimePeriod.parse('1 hour')
            )
        ]
        
        mock_manager.get_user_searches = AsyncMock(return_value=mock_searches)
        
        # Execute tool
        result = await tool._arun(user_id=12345)
        
        # Verify
        mock_manager.get_user_searches.assert_called_once_with(12345)
        assert "Your Active Job Searches" in result
        assert "Python Developer" in result
        assert "Data Scientist" in result
    
    @pytest.mark.asyncio
    async def test_list_searches_empty(self, tool, mock_manager):
        """Test listing when user has no searches."""
        mock_manager.get_user_searches = AsyncMock(return_value=[])
        
        result = await tool._arun(user_id=12345)
        
        assert "don't have any active job searches" in result
        assert "create your first" in result.lower()


class TestCreateJobSearchTool:
    """Test the CreateJobSearchTool functionality."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock JobSearchManager."""
        manager = Mock(spec=JobSearchManager)
        return manager
    
    @pytest.fixture
    def tool(self, mock_manager):
        """Create a CreateJobSearchTool instance."""
        return CreateJobSearchTool(mock_manager)
    
    @pytest.mark.asyncio
    async def test_create_search_success(self, tool, mock_manager):
        """Test successful job search creation."""
        mock_manager.add_search = AsyncMock(return_value="search123")
        
        result = await tool._arun(
            user_id=12345,
            job_title="Python Developer",
            location="Berlin",
            job_types=["Full-time"],
            remote_types=["Hybrid"],
            time_period="1 hour"
        )
        
        # Verify manager was called
        mock_manager.add_search.assert_called_once()
        call_args = mock_manager.add_search.call_args[0][0]
        assert call_args.job_title == "Python Developer"
        assert call_args.location == "Berlin"
        assert call_args.user_id == 12345
        
        # Verify response (should not contain the search ID for security)
        assert "✅" in result
        assert "Python Developer" in result
        assert "Berlin" in result
        # Ensure no ID is exposed in the response
        assert "search123" not in result
    
    def test_job_type_parsing(self, tool):
        """Test job type parsing functionality."""
        # Test valid job types (use display names that match our data)
        job_types = tool._parse_job_types(["Full-time", "Part-time"])
        assert len(job_types) == 2
        
        # Test empty input (should return default)
        default_types = tool._parse_job_types(None)
        assert len(default_types) >= 1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"]) 