"""
LangChain tool for deleting job searches.
"""
import logging
from typing import Type, Optional, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

from main_project.app.core.job_search_manager import JobSearchManager
from shared.data import JobSearchRemove
from .base_tool import DocumentedTool, ToolDocumentation, ParameterInfo, InputType

logger = logging.getLogger(__name__)


class DeleteJobSearchInput(BaseModel):
    """Input schema for deleting a job search."""
    user_id: int = Field(description="Telegram user ID who owns the search")
    search_id: str = Field(description="ID of the job search to delete (UUID string)")


class DeleteJobSearchTool(BaseTool, DocumentedTool):
    """Tool for deleting a job search."""
    
    class Config:
        arbitrary_types_allowed = True

    name: str = "delete_job_search"
    job_search_manager: Any
    description: str = """
    Delete an existing job search alert.
    Use this tool when the user wants to remove/cancel a job search they no longer need.
    
    Required information:
    - user_id: The user's Telegram ID
    - search_id: The ID of the search to delete (can be found using list_job_searches tool)
    
    Before calling this tool:
    1. Make sure you have the correct search_id from the user
    2. Consider showing the search details first so user can confirm they want to delete the right one
    3. Ask for confirmation before actually deleting
    
    The search will be permanently removed and stop sending notifications.
    """
    args_schema: Type[BaseModel] = DeleteJobSearchInput
    return_direct: bool = False
    
    @property
    def tool_documentation(self) -> ToolDocumentation:
        """Return complete tool documentation."""
        return ToolDocumentation(
            name="Delete Job Search",
            description="Remove an existing job search alert permanently",
            purpose="Cancel a job search that you no longer need. This will stop all notifications and permanently remove the search from your account.",
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
                    description="The unique ID of the job search to delete",
                    type=InputType.TEXT,
                    required=True,
                    example="abc123def-456-789",
                    validation_rules="Must be a valid search ID from your existing searches. Use 'List job searches' to find the correct ID."
                )
            ],
            examples=[
                "Delete search abc123",
                "Remove the Python developer search",
                "Cancel my Berlin job alerts",
                "Delete job search with ID xyz789"
            ],
            confirmation_required=True
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
            logger.info(f"Deleting job search {search_id} for user {user_id}")
            
            # First, try to get the search details for confirmation
            searches = await self.job_search_manager.get_user_searches(user_id)
            search_to_delete = None
            
            for search in searches:
                if search.id == search_id:
                    search_to_delete = search
                    break
            
            if not search_to_delete:
                return f"""❌ **Search not found**

I couldn't find that job search in your account.

Please check the search description and try again. You can use "Show my job searches" to see all your active searches."""
            
            # Create JobSearchRemove object
            job_search_remove = JobSearchRemove(
                user_id=user_id,
                search_id=search_id
            )
            
            # Delete the search
            success = await self.job_search_manager.delete_search(job_search_remove)
            
            if success:
                result = f"""✅ **Job Search Deleted Successfully**

🗑️ **Deleted Search:**
- **Keywords:** {search_to_delete.job_title}
- **Location:** {search_to_delete.location or "Any location"}

**What this means:**
- This search will no longer check for new jobs
- You won't receive any more notifications for this search
- The search alert has been permanently removed

**Need to create a new search?**
Just say "Create a new job search" and I'll help you set it up!
"""
                logger.info(f"Successfully deleted job search {search_id} for user {user_id}")
                return result
            else:
                return f"""❌ **Failed to delete search**

I couldn't delete that job search. This could be due to:
- The search might have already been deleted
- A temporary system issue

Please try again, or contact support if the problem persists."""
            
        except Exception as e:
            logger.error(f"Error deleting job search {search_id} for user {user_id}: {e}")
            return f"❌ Sorry, I couldn't delete the job search. Please try again. Error: {str(e)}"
    
    def _run(
        self,
        user_id: int,
        search_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Sync implementation (not used in async context)."""
        raise NotImplementedError("This tool only supports async execution") 