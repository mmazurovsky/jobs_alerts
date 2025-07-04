"""
LangChain tool for executing one-time job searches.
"""
import logging
from typing import Type, Optional, Any, List
from pydantic import BaseModel, Field, field_validator
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

from main_project.app.core.job_search_manager import JobSearchManager
from shared.data import (
    JobSearchIn, JobType, RemoteType, TimePeriod, get_default_remote_type, 
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
    job_types: Optional[List[str]] = Field(default=None, description=f"List of job types. Valid options: {', '.join(get_job_types())}. Leave empty for all types.")
    remote_types: Optional[List[str]] = Field(default=None, description=f"Remote work preferences. Valid options: {', '.join(get_remote_types())}. Leave empty for all types.")
    filter_text: Optional[str] = Field(default=None, description="🌟 Our unique AI-powered smart filter! Use natural language to describe what you want to EXCLUDE from results")

    @field_validator('job_types')
    @classmethod
    def validate_job_types(cls, v):
        if v is None:
            return v
        valid_types = get_job_types()
        invalid_types = [jt for jt in v if jt not in valid_types]
        if invalid_types:
            raise ValueError(f"Invalid job types: {', '.join(invalid_types)}. Valid options are: {', '.join(valid_types)}")
        return v
    
    @field_validator('remote_types')
    @classmethod
    def validate_remote_types(cls, v):
        if v is None:
            return v
        valid_types = get_remote_types()
        invalid_types = [rt for rt in v if rt not in valid_types]
        if invalid_types:
            raise ValueError(f"Invalid remote types: {', '.join(invalid_types)}. Valid options are: {', '.join(valid_types)}")
        return v


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
    - filter_text: 🌟 Our unique AI-powered smart filter! Use natural language to describe what you want to EXCLUDE from results
    
    The search will be executed immediately and results sent to the user.
    """
    args_schema: Type[BaseModel] = OneTimeSearchInput
    return_direct: bool = False
    
    @property
    def tool_documentation(self) -> ToolDocumentation:
        """Return complete tool documentation."""
        return ToolDocumentation(
            name="One-time Immediate Job Search",
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
                    description="Types of employment to search for",
                    type=InputType.MULTISELECT,
                    required=False,
                    options=get_job_types(),
                    example=get_default_job_type(),
                    validation_rules=f"Must choose from: {', '.join(get_job_types())}. Leave empty to include all types."
                ),
                ParameterInfo(
                    name="remote_types",
                    description="Remote work arrangement preferences",
                    type=InputType.MULTISELECT,
                    required=False,
                    options=get_remote_types(),
                    example=get_default_remote_type(),
                    validation_rules=f"Must choose from: {', '.join(get_remote_types())}. Leave empty to include all arrangements."
                ),
                ParameterInfo(
                    name="filter_text",
                    description="🌟 Our unique AI-powered smart filter! Use natural language to describe what you want to EXCLUDE from results",
                    type=InputType.TEXT,
                    required=False,
                    example="No entry level positions, no travel required, no security clearance needed, exclude startups",
                    validation_rules="This is our signature feature - describe in natural language what you DON'T want. Examples: 'No entry level jobs', 'Avoid companies requiring travel', 'No positions requiring specific certifications'"
                )
            ],
            examples=[
                "Search for Python developer jobs in Berlin now, filter out jobs that require German language and travelling",
                "Find remote data scientist positions with full-time",
                "Show me React developer jobs in London immediately - no entry level",
                "Search for marketing manager roles in New York - hybrid work preferred, exclude travel requirements"
            ],
            confirmation_required=False
        )
    
    def __init__(self, job_search_manager: JobSearchManager, **kwargs):
        """Initialize the tool with JobSearchManager dependency."""
        super().__init__(job_search_manager=job_search_manager, **kwargs)
    
    def _parse_job_types(self, job_types: Optional[List[str]]) -> List[JobType]:
        """Parse and validate job type strings to JobType instances."""
        if not job_types:
            # Default to all available job types
            return [JobType.parse(jt) for jt in get_all_job_types()]
        
        valid_types = get_job_types()
        parsed_types = []
        invalid_types = []
        
        for jt in job_types:
            if jt not in valid_types:
                invalid_types.append(jt)
            else:
                try:
                    parsed_types.append(JobType.parse(jt))
                except ValueError:
                    invalid_types.append(jt)
        
        if invalid_types:
            raise ValueError(f"Invalid job types: {', '.join(invalid_types)}. Valid options are: {', '.join(valid_types)}")
        
        return parsed_types if parsed_types else [JobType.parse(jt) for jt in get_all_job_types()]
    
    def _parse_remote_types(self, remote_types: Optional[List[str]]) -> List[RemoteType]:
        """Parse and validate remote type strings to RemoteType instances."""
        if not remote_types:
            # Default to all available remote types
            return [RemoteType.parse(rt) for rt in get_all_remote_types()]
        
        valid_types = get_remote_types()
        parsed_types = []
        invalid_types = []
        
        for rt in remote_types:
            if rt not in valid_types:
                invalid_types.append(rt)
            else:
                try:
                    parsed_types.append(RemoteType.parse(rt))
                except ValueError:
                    invalid_types.append(rt)
        
        if invalid_types:
            raise ValueError(f"Invalid remote types: {', '.join(invalid_types)}. Valid options are: {', '.join(valid_types)}")
        
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
            try:
                parsed_job_types = self._parse_job_types(job_types)
                parsed_remote_types = self._parse_remote_types(remote_types)
            except ValueError as e:
                # Return validation error with helpful information
                error_msg = str(e)
                return f"""❌ **Invalid Input**

{error_msg}

**Please specify valid values:**
• **Job Types:** {', '.join(get_job_types())}
• **Remote Types:** {', '.join(get_remote_types())}

❓ Would you like to try again with the correct values?"""
            
            # Create JobSearchIn object for one-time search
            job_search_in = JobSearchIn(
                job_title=job_title,
                location=location,
                job_types=parsed_job_types,
                remote_types=parsed_remote_types,
                time_period=TimePeriod.parse(get_time_period_for_one_time_search()),
                user_id=user_id,
                filter_text=filter_text,
            )
            
            # Execute search
            results = await self.job_search_manager.execute_one_time_search(job_search_in)
            
            if not results:
                # Format no results response
                job_types_str = ", ".join([jt.label for jt in parsed_job_types])
                remote_types_str = ", ".join([rt.label for rt in parsed_remote_types])
                
                return f"""🔍 **Search Complete - No Results Found**

**Your search criteria:**
🔍 **Job:** {job_title}
📍 **Location:** {location}
💼 **Types:** {job_types_str}
🏠 **Remote:** {remote_types_str}
{f'🔍 **Filters:** {filter_text}' if filter_text else ''}

**What this means:**
• No jobs matching your criteria were found in recent postings
• This doesn't mean there are no jobs available - just none in our current search results

**What you can try:**
• Broaden your search terms (e.g., use fewer specific keywords)
• Try different job types or remote arrangements
• Search in additional locations
• Create a recurring alert to catch new postings: "Set up job alerts for {job_title}"

❓ Would you like to try a different search or set up ongoing alerts?"""
            
            # Format results response
            results_count = len(results)
            job_types_str = ", ".join([jt.label for jt in parsed_job_types])
            remote_types_str = ", ".join([rt.label for rt in parsed_remote_types])
            
            response = f"""🎯 **Found {results_count} Job{'s' if results_count != 1 else ''}!**

**Your search:**
🔍 **Job:** {job_title}
📍 **Location:** {location}
💼 **Types:** {job_types_str}
🏠 **Remote:** {remote_types_str}
{f'🔍 **Filters:** {filter_text}' if filter_text else ''}

**Results:** {results_count} matching position{'s' if results_count != 1 else ''}

I'll send you the job details in separate messages. Each job includes:
✅ Company and role information
✅ Location and work arrangement details
✅ Direct application links
✅ AI-powered compatibility insights

**Want ongoing alerts?**
Say: "Set up alerts for {job_title}" to get notified of new matching jobs automatically!
"""
            
            logger.info(f"One-time search completed for user {user_id}: found {results_count} results")
            return response
            
        except Exception as e:
            logger.error(f"Error in one-time search for user {user_id}: {e}")
            return f"""❌ **Search Failed**

Sorry, I couldn't complete your job search due to a technical issue.

**Error:** {str(e)}

**What you can do:**
• Try again in a few moments
• Simplify your search terms
• Contact support if the problem persists

❓ Would you like to try searching again?"""
    
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