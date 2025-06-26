"""
LangChain tool for getting detailed information about a specific job search.
"""
import logging
from typing import Type, Optional, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

from main_project.app.core.job_search_manager import JobSearchManager
from .base_tool import DocumentedTool, ToolDocumentation, ParameterInfo, InputType

logger = logging.getLogger(__name__)


class GetJobSearchDetailsInput(BaseModel):
    """Input schema for getting job search details."""
    user_id: int = Field(description="Telegram user ID who owns the search")
    search_id: str = Field(description="ID of the job search to get details for (UUID string)")


class GetJobSearchDetailsTool(BaseTool, DocumentedTool):
    """Tool for getting detailed information about a specific job search."""
    
    class Config:
        arbitrary_types_allowed = True

    name: str = "get_job_search_details"
    job_search_manager: Any
    description: str = """
    Get detailed information about a specific job search.
    Use this tool when the user wants to see full details of one of their job searches, 
    or when they reference a specific search by ID.
    
    Required information:
    - user_id: The user's Telegram ID
    - search_id: The ID of the search to get details for
    
    This will show all the search parameters, status, and provide options for managing the search.
    """
    args_schema: Type[BaseModel] = GetJobSearchDetailsInput
    return_direct: bool = False
    
    @property
    def tool_documentation(self) -> ToolDocumentation:
        """Return complete tool documentation."""
        return ToolDocumentation(
            name="Get Job Search Details",
            description="View detailed information about a specific job search",
            purpose="Get comprehensive details about one of your existing job searches, including all settings, criteria, and status information.",
            parameters=[
                ParameterInfo(
                    name="user_id",
                    description="Your Telegram user ID (automatically provided)",
                    type=InputType.NUMBER,
                    required=True,
                    example="12345"
                ),
                ParameterInfo(
                    name="search_id",
                    description="The unique ID of the job search to view details for",
                    type=InputType.TEXT,
                    required=True,
                    example="abc123def-456-789",
                    validation_rules="Must be a valid search ID from your existing searches. Use 'List job searches' to find the correct ID."
                )
            ],
            examples=[
                "Show details for search abc123",
                "Get information about my Python developer search",
                "View details of search xyz789",
                "Show me more info about that Berlin search"
            ],
            confirmation_required=False
        )
    
    def __init__(self, job_search_manager: JobSearchManager, **kwargs):
        """Initialize the tool with JobSearchManager dependency."""
        super().__init__(job_search_manager=job_search_manager, **kwargs)
    
    async def _arun(
        self,
        user_id: int,
        search_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async implementation of the tool."""
        try:
            logger.info(f"Getting details for job search {search_id} for user {user_id}")
            
            # Get user's searches and find the specific one
            searches = await self.job_search_manager.get_user_searches(user_id)
            target_search = None
            
            for search in searches:
                if search.id == search_id:
                    target_search = search
                    break
            
            if not target_search:
                return f"""❌ **Search not found**

I couldn't find that job search in your account.

Please check the search description and try again. You can use "Show my job searches" to see all your active searches."""
            
            # Format detailed information
            job_types = [jt.label if hasattr(jt, 'label') else str(jt) for jt in target_search.job_types] if target_search.job_types else ["Any"]
            job_types_str = ", ".join(job_types)
            
            remote_types = [rt.label if hasattr(rt, 'label') else str(rt) for rt in target_search.remote_types] if target_search.remote_types else ["Any"]
            remote_types_str = ", ".join(remote_types)
            
            result = f"""📋 **Job Search Details**

🔍 **Keywords:** {target_search.job_title}
📍 **Location:** {target_search.location or "Any location"}
💼 **Job Types:** {job_types_str}
🏠 **Remote Options:** {remote_types_str}
📅 **Time Period:** {target_search.time_period.label if hasattr(target_search.time_period, 'label') else str(target_search.time_period)}
"""
            
            # Add filter text if present
            if hasattr(target_search, 'filter_text') and target_search.filter_text:
                result += f"🔍 **Smart Filter:** {target_search.filter_text}\n"
            
            result += f"📅 **Created:** {target_search.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            
            result += """**What this search does:**
✅ Automatically checks for new job postings every {period}
✅ Filters results using LinkedIn's search parameters
✅ Applies your smart filter to exclude unwanted positions
✅ Sends you only relevant job opportunities

**Available actions:**
🗑️ Delete this search: Say "Delete job search {search_id}"
📝 Modify search: Say "Update my job search for {title}"
🔍 Run search now: Say "Search for {title} jobs in {location}"

**Need help?** 
• To see all your searches: "List my job searches"
• To create a new search: "Create a job search for [job title]"
• To run a quick search: "Find [job title] jobs in [location]"
""".format(
                period=target_search.time_period.display_name.lower(),
                search_id=search_id,
                title=target_search.job_title,
                location=target_search.location
            )
            
            logger.info(f"Successfully retrieved details for job search {search_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting details for job search {search_id} for user {user_id}: {e}")
            return f"❌ Sorry, I couldn't retrieve the job search details. Please try again. Error: {str(e)}"
    
    def _run(
        self,
        user_id: int,
        search_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Sync implementation (not used in async context)."""
        raise NotImplementedError("This tool only supports async execution") 