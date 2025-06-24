"""
LangChain tool for listing user's job searches.
"""
import logging
from typing import Type, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

from main_project.app.core.job_search_manager import JobSearchManager
from .base_tool import DocumentedTool, ToolDocumentation, ParameterInfo, InputType

logger = logging.getLogger(__name__)


class ListJobSearchesInput(BaseModel):
    """Input schema for listing job searches."""
    user_id: int = Field(description="Telegram user ID to list job searches for")


class ListJobSearchesTool(BaseTool, DocumentedTool):
    """Tool for listing all job searches for a user."""
    
    class Config:
        arbitrary_types_allowed = True
    
    name: str = "list_job_searches"
    job_search_manager: Any
    description: str = """
    List all active job searches for the current user.
    Use this tool when the user wants to see their existing job searches, search history, or asks "what searches do I have" or similar.
    
    Returns a formatted list of job searches with:
    - Search ID (for reference in other operations)
    - Job title/keywords
    - Location
    - Job types (full-time, part-time, contract, etc.)
    - Remote work preferences
    - Time period for search
    - Status and creation info
    """
    args_schema: Type[BaseModel] = ListJobSearchesInput
    return_direct: bool = False
    
    @property
    def tool_documentation(self) -> ToolDocumentation:
        """Return complete tool documentation."""
        return ToolDocumentation(
            name="List Job Searches",
            description="View all your active job search alerts",
            purpose="Display a complete list of your current job searches with their details including keywords, location, schedule, and status.",
            parameters=[
                ParameterInfo(
                    name="user_id",
                    description="Your Telegram user ID (automatically provided)",
                    type=InputType.NUMBER,
                    required=True,
                    example="12345"
                )
            ],
            examples=[
                "Show me my job searches",
                "List all my job alerts", 
                "What searches do I have?",
                "Display my active searches"
            ],
            confirmation_required=False
        )
    
    def __init__(self, job_search_manager: JobSearchManager, **kwargs):
        """Initialize the tool with JobSearchManager dependency."""
        super().__init__(job_search_manager=job_search_manager, **kwargs)
    
    async def _arun(
        self,
        user_id: int,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async implementation of the tool."""
        try:
            logger.info(f"Listing job searches for user {user_id}")
            
            # Get user's job searches
            searches = await self.job_search_manager.get_user_searches(user_id)
            
            if not searches:
                return """You don't have any active job searches yet. 
                
Would you like me to help you create your first job search? I can guide you through setting up:
- Job keywords (like "Python developer" or "Data analyst")
- Location preferences 
- Job types (full-time, part-time, contract)
- Remote work options
- How often to check for new jobs

Just say something like "I want to create a new job search" and I'll help you get started!"""
            
            # Format the search results
            result = f"📋 **Your Active Job Searches** ({len(searches)} total)\n\n"
            
            for i, search in enumerate(searches, 1):
                # Format job types
                job_types = [jt.label if hasattr(jt, 'label') else str(jt) for jt in search.job_types] if search.job_types else ["Any"]
                job_types_str = ", ".join(job_types)
                
                # Format remote types  
                remote_types = [rt.label if hasattr(rt, 'label') else str(rt) for rt in search.remote_types] if search.remote_types else ["Any"]
                remote_types_str = ", ".join(remote_types)
                
                result += f"""**{i}. {search.job_title}**
🆔 ID: `{search.id}`
📍 Location: {search.location or "Any location"}
💼 Job Types: {job_types_str}
🏠 Remote: {remote_types_str}
📅 Time Period: {search.time_period.label if hasattr(search.time_period, 'label') else str(search.time_period)}
"""
                
                # Add filter info if present
                if hasattr(search, 'filter_text') and search.filter_text:
                    result += f"🔍 Filters: {search.filter_text}\n"
                    
                # Add blacklist if present
                if hasattr(search, 'blacklist') and search.blacklist:
                    result += f"🚫 Blacklist: {', '.join(search.blacklist)}\n"
                
                result += "\n"
            
            result += """**Available Actions:**
- To view details: "Show me details for search [ID]"
- To delete a search: "Delete search [ID]" 
- To create a new search: "Create a new job search"
- To update a search: "Update search [ID]" """
            
            logger.info(f"Successfully listed {len(searches)} job searches for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error listing job searches for user {user_id}: {e}")
            return f"❌ Sorry, I couldn't retrieve your job searches. Please try again. Error: {str(e)}"
    
    def _run(
        self, 
        user_id: int,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Sync implementation (not used in async context)."""
        raise NotImplementedError("This tool only supports async execution") 