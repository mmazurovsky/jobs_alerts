"""
LangChain tool for executing one-time job searches.
"""
import logging
from typing import Type, Optional, Any, List
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

from main_project.app.core.job_search_manager import JobSearchManager
from shared.data import (
    JobSearchIn, JobType, RemoteType, TimePeriod, 
    get_job_types, get_remote_types, get_time_period_for_one_time_search, get_one_time_search_description,
    get_default_job_type, get_all_job_types, get_all_remote_types
)
from .base_tool import DocumentedTool, ToolDocumentation, ParameterInfo, InputType

logger = logging.getLogger(__name__)


class OneTimeSearchInput(BaseModel):
    """Input schema for one-time job search."""
    user_id: int = Field(description="Telegram user ID requesting the search")
    job_title: str = Field(description="Job title or keywords to search for (e.g., 'Python developer', 'Data scientist')")
    location: str = Field(description="Location to search in (e.g., 'Berlin', 'Remote', 'New York'). Required - specify city, country, or 'Remote'.")
    job_types: Optional[List[str]] = Field(default=None, description="List of job types: 'full_time', 'part_time', 'contract', 'temporary', 'internship'. Leave empty for all types.")
    remote_types: Optional[List[str]] = Field(default=None, description="Remote work preferences: 'remote', 'hybrid', 'on_site'. Leave empty for all types.")
    filter_text: Optional[str] = Field(default=None, description="Additional filter keywords that must be present in job descriptions")


class OneTimeSearchTool(BaseTool, DocumentedTool):
    """Tool for executing a one-time job search."""
    
    class Config:
        arbitrary_types_allowed = True

    name: str = "one_time_search"
    job_search_manager: Any
    description: str = f"""
    Execute a one-time job search that finds jobs posted in the last month and provides immediate results.
    Use this tool when the user wants to search for jobs right now without creating a recurring alert.
    
    {get_one_time_search_description()}
    
    This is different from creating a job search alert - it's for immediate results only.
    Perfect for when users say things like:
    - "Search for Python developer jobs in Berlin now"
    - "Find me remote data scientist positions"
    - "Show me available React developer jobs"
    - "I want to see what full-time marketing roles are available"
    
    Required information:
    - job_title: What kind of job they're looking for
    - user_id: The user's Telegram ID
    
    Optional information:
    - location: Where they want to work (city, country, or "remote")
    - job_types: Type of employment ({', '.join(get_job_types())})
    - remote_types: Remote work preference ({', '.join(get_remote_types())})
    - filter_text: Additional keywords for filtering (e.g., specific technologies)
    
    The search will be executed immediately and results sent to the user.
    """
    args_schema: Type[BaseModel] = OneTimeSearchInput
    return_direct: bool = False
    
    @property
    def tool_documentation(self) -> ToolDocumentation:
        """Return complete tool documentation."""
        return ToolDocumentation(
            name="One-time Job Search",
            description="Execute an immediate job search and get results now",
            purpose=get_one_time_search_description(),
            parameters=[
                ParameterInfo(
                    name="user_id",
                    description="Your Telegram user ID (automatically provided)",
                    type=InputType.NUMBER,
                    required=True,
                    example="12345"
                ),
                ParameterInfo(
                    name="job_title",
                    description="Job title, role name, or keywords to search for immediately",
                    type=InputType.TEXT,
                    required=True,
                    example="Python developer",
                    validation_rules="Be specific about the role or skills you're looking for"
                ),
                ParameterInfo(
                    name="location",
                    description="City, country, or region to search in",
                    type=InputType.TEXT,
                    required=True,
                    example="Berlin, Germany",
                    validation_rules="Must specify a location - can be a city, country, or 'Remote' for remote-only positions"
                ),
                ParameterInfo(
                    name="job_types",
                    description="Types of employment to include in search",
                    type=InputType.MULTISELECT,
                    required=False,
                    options=get_job_types(),
                    example="Full-time",
                    validation_rules=f"Leave empty to include all types: {', '.join(get_job_types())}"
                ),
                ParameterInfo(
                    name="remote_types",
                    description="Remote work arrangements to include",
                    type=InputType.MULTISELECT,
                    required=False,
                    options=get_remote_types(),
                    example="Remote",
                    validation_rules=f"Leave empty to include all arrangements: {', '.join(get_remote_types())}"
                ),
                ParameterInfo(
                    name="filter_text",
                    description="Keywords for filtering job descriptions before they reach you",
                    type=InputType.TEXT,
                    required=False,
                    example="No entry level, No Spanish required, No SAP experience",
                    validation_rules="Use filters to exclude unwanted jobs. Examples: 'No entry level jobs', 'No travel required at all', 'Doesn't require working with Excel'"
                )
            ],
            examples=[
                "Search for Python developer jobs in Berlin now",
                "Find remote data scientist positions with full-time contracts",
                "Show me React developer jobs in London immediately",
                "Search for marketing manager roles in New York - hybrid work preferred"
            ],
            confirmation_required=False
        )
    
    def __init__(self, job_search_manager: JobSearchManager, **kwargs):
        """Initialize the tool with JobSearchManager dependency."""
        super().__init__(job_search_manager=job_search_manager, **kwargs)
    
    def _parse_job_types(self, job_types: Optional[List[str]]) -> List[JobType]:
        """Parse job type strings to JobType instances."""
        if not job_types:
            # Default to all available job types for one-time search
            return [JobType.parse(jt) for jt in get_all_job_types()]
        
        parsed_types = []
        for jt in job_types:
            try:
                parsed_types.append(JobType.parse(jt))
            except ValueError:
                logger.warning(f"Invalid job type: {jt}")
                continue
        
        return parsed_types if parsed_types else [JobType.parse(jt) for jt in get_all_job_types()]
    
    def _parse_remote_types(self, remote_types: Optional[List[str]]) -> List[RemoteType]:
        """Parse remote type strings to RemoteType instances."""
        if not remote_types:
            # Default to all available remote types
            return [RemoteType.parse(rt) for rt in get_all_remote_types()]
        
        parsed_types = []
        for rt in remote_types:
            try:
                parsed_types.append(RemoteType.parse(rt))
            except ValueError:
                logger.warning(f"Invalid remote type: {rt}")
                continue
        
        return parsed_types if parsed_types else [RemoteType.parse(rt) for rt in get_all_remote_types()]
    
    async def _arun(
        self,
        user_id: int,
        job_title: str,
        location: str,
        job_types: Optional[List[str]] = None,
        remote_types: Optional[List[str]] = None,
        filter_text: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async implementation of the tool."""
        try:
            logger.info(f"Executing one-time search for user {user_id}: {job_title}")
            
            # Parse and validate inputs
            parsed_job_types = self._parse_job_types(job_types)
            parsed_remote_types = self._parse_remote_types(remote_types)
            
            # Create JobSearchIn object for one-time search
            job_search_in = JobSearchIn(
                job_title=job_title,
                location=location,
                job_types=parsed_job_types,
                remote_types=parsed_remote_types,
                time_period=TimePeriod.parse(get_time_period_for_one_time_search()),  # Use centralized time period
                user_id=user_id,
                filter_text=filter_text,
                blacklist=[]
            )
            
            # Execute the one-time search
            await self.job_search_manager.execute_one_time_search(job_search_in, user_id)
            
            # Format response
            job_types_str = ", ".join([jt.label for jt in parsed_job_types])
            remote_types_str = ", ".join([rt.label for rt in parsed_remote_types])
            
            result = f"""🔍 **One-time Job Search Started!**

**Search Parameters:**
🔍 **Keywords:** {job_title}
📍 **Location:** {location or "Any location"}
💼 **Job Types:** {job_types_str}
🏠 **Remote Options:** {remote_types_str}
"""
            
            if filter_text:
                result += f"🔍 **Additional Filters:** {filter_text}\n"
            
            result += f"""
**What's happening now:**
✅ I'm searching LinkedIn for jobs matching your criteria
✅ Looking for jobs posted in the last month
✅ Results will be sent to you in this chat shortly

**Please wait a moment** - I'm gathering the latest job postings for you!

**Want to create a recurring alert?**
If you like these results, I can set up an automatic search that runs regularly. Just say "Create a job search for {job_title}" and I'll help you set it up!
"""
            
            logger.info(f"Successfully initiated one-time search for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing one-time search for user {user_id}: {e}")
            return f"""❌ **Search Failed**

Sorry, I couldn't execute the job search right now. This could be due to:
- Temporary system issues
- Scraper service being unavailable
- Network connectivity problems

Please try again in a few moments. Error: {str(e)}

**Alternative:** You can create a recurring job search instead, which will automatically check for jobs and notify you when the system is available."""
    
    def _run(
        self,
        user_id: int,
        job_title: str,
        location: str,
        job_types: Optional[List[str]] = None,
        remote_types: Optional[List[str]] = None,
        filter_text: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Sync implementation (not used in async context)."""
        raise NotImplementedError("This tool only supports async execution") 