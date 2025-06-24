"""
LangChain tool for creating new job searches.
"""
import logging
from typing import Type, Optional, List, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

from main_project.app.core.job_search_manager import JobSearchManager
from shared.data import (
    JobSearchIn, JobType, RemoteType, TimePeriod, 
    get_job_types, get_remote_types, get_time_periods,
    get_default_job_type, get_default_time_period, get_all_job_types, get_all_remote_types
)
from .base_tool import DocumentedTool, ToolDocumentation, ParameterInfo, InputType

logger = logging.getLogger(__name__)


class CreateJobSearchInput(BaseModel):
    """Input schema for creating a job search."""
    user_id: int = Field(description="Telegram user ID creating the search")
    job_title: str = Field(description="Job title or keywords to search for (e.g., 'Python developer', 'Data scientist')")
    location: str = Field(description="Location to search in (e.g., 'Berlin', 'Remote', 'New York'). Required - specify city, country, or 'Remote'.")
    job_types: Optional[List[str]] = Field(default=None, description="List of job types: 'full_time', 'part_time', 'contract', 'temporary', 'internship'. Leave empty for all types.")
    remote_types: Optional[List[str]] = Field(default=None, description="Remote work preferences: 'remote', 'hybrid', 'on_site'. Leave empty for all types.")
    time_period: Optional[str] = Field(default=None, description="How frequently to check for new jobs. Default is '1 hour' if not specified.")
    filter_text: Optional[str] = Field(default=None, description="Additional filter keywords that must be present in job descriptions")
    blacklist: Optional[List[str]] = Field(default=None, description="List of words/companies to exclude from results")


class CreateJobSearchTool(BaseTool, DocumentedTool):
    """Tool for creating a new job search."""
    
    class Config:
        arbitrary_types_allowed = True
    
    name: str = "create_job_search"
    job_search_manager: Any
    description: str = f"""
    Create a new recurring job search alert for the user.
    Use this tool when the user wants to set up ongoing notifications for new job opportunities.
    
    This creates persistent alerts that automatically check for new jobs at the specified frequency.
    
    Required information:
    - job_title: What kind of job they're looking for (keywords)
    - user_id: The user's Telegram ID
    
    Optional information:
    - location: Where they want to work (city, country, or "remote")
    - job_types: Type of employment - options: {', '.join(get_job_types())}
    - remote_types: Remote work preference - options: {', '.join(get_remote_types())}
    - time_period: How frequently to check for new jobs - options: {', '.join(get_time_periods())}
    - filter_text: Additional keywords that must be in the job description
    - blacklist: Companies or keywords to exclude
    
    Before calling this tool, make sure you have collected at least the job_title from the user.
    If any required information is missing, ask the user for it first.
    """
    args_schema: Type[BaseModel] = CreateJobSearchInput
    return_direct: bool = False
    
    @property
    def tool_documentation(self) -> ToolDocumentation:
        """Return complete tool documentation."""
        return ToolDocumentation(
            name="Create Job Search",
            description="Create a new automated job search alert",
            purpose="Set up a recurring job search that will automatically find and notify you of new job opportunities matching your criteria.",
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
                    description="Job title, role name, or keywords to search for",
                    type=InputType.TEXT,
                    required=True,
                    example="Python developer",
                    validation_rules="Be specific but not too narrow. Include main skills or technologies."
                ),
                ParameterInfo(
                    name="location",
                    description="City, country, or region where you want to find jobs",
                    type=InputType.TEXT,
                    required=True,
                    example="Berlin, Germany",
                    validation_rules="Must specify a location - can be a city, country, or 'Worldwide'"
                ),
                ParameterInfo(
                    name="job_types", 
                    description="Types of employment you're interested in",
                    type=InputType.MULTISELECT,
                    required=False,
                    options=get_job_types(),
                    example="Full-time",
                    validation_rules=f"Leave empty to include all types: {', '.join(get_job_types())}"
                ),
                ParameterInfo(
                    name="remote_types",
                    description="Remote work preferences",
                    type=InputType.MULTISELECT,
                    required=False,
                    options=get_remote_types(),
                    example="Remote",
                    validation_rules=f"Leave empty to include all arrangements: {', '.join(get_remote_types())}"
                ),
                ParameterInfo(
                    name="time_period",
                    description="How frequently to search for new jobs",
                    type=InputType.SELECT,
                    required=False,
                    options=get_time_periods(),
                    example="1 hour",
                    validation_rules="Determines how often the system checks for new jobs matching your criteria. Defaults to '1 hour' if not specified"
                ),
                ParameterInfo(
                    name="filter_text",
                    description="Additional keywords for filtering job descriptions before they reach you",
                    type=InputType.TEXT,
                    required=False,
                    example="No entry level, No Spanish required, No SAP experience",
                    validation_rules="Use negative filters to exclude unwanted jobs. Examples: 'No entry level', 'No travel required', 'No security clearance'"
                ),
                ParameterInfo(
                    name="blacklist",
                    description="Companies or specific terms to exclude from search results",
                    type=InputType.TEXT,
                    required=False,
                    example="TechCorp, startup",
                    validation_rules="Comma-separated list of companies or terms to avoid"
                )
            ],
            examples=[
                "Create a search for Python developer jobs in Berlin with full-time contracts",
                "I want to set up alerts for remote data scientist positions - check every hour",
                "Create a search for React developer jobs in London - hybrid or remote preferred",
                "Set up alerts for marketing manager roles - part-time or contract work"
            ],
            confirmation_required=True
        )
    
    def __init__(self, job_search_manager: JobSearchManager, **kwargs):
        """Initialize the tool with JobSearchManager dependency."""
        super().__init__(job_search_manager=job_search_manager, **kwargs)
    
    def _parse_job_types(self, job_types: Optional[List[str]]) -> List[JobType]:
        """Parse job type strings to JobType instances."""
        if not job_types:
            return [JobType.parse(get_default_job_type())]  # Default to full-time
        
        parsed_types = []
        for jt in job_types:
            try:
                # Try to parse directly using the JobType.parse method
                parsed_types.append(JobType.parse(jt))
            except ValueError:
                logger.warning(f"Invalid job type: {jt}")
                continue
        
        return parsed_types if parsed_types else [JobType.parse(get_default_job_type())]
    
    def _parse_remote_types(self, remote_types: Optional[List[str]]) -> List[RemoteType]:
        """Parse remote type strings to RemoteType instances."""
        if not remote_types:
            # Default to all available remote types
            return [RemoteType.parse(rt) for rt in get_all_remote_types()]
        
        parsed_types = []
        for rt in remote_types:
            try:
                # Try to parse directly using the RemoteType.parse method
                parsed_types.append(RemoteType.parse(rt))
            except ValueError:
                logger.warning(f"Invalid remote type: {rt}")
                continue
        
        return parsed_types if parsed_types else [RemoteType.parse(rt) for rt in get_all_remote_types()]
    
    def _parse_time_period(self, time_period: Optional[str]) -> TimePeriod:
        """Parse time period string to TimePeriod instance."""
        if not time_period:
            return TimePeriod.parse(get_default_time_period())  # Default to 1 hour
        
        try:
            # Try to parse directly using the TimePeriod.parse method
            return TimePeriod.parse(time_period)
        except ValueError:
            logger.warning(f"Invalid time period: {time_period}, defaulting to {get_default_time_period()}")
            return TimePeriod.parse(get_default_time_period())
    
    async def _arun(
        self,
        user_id: int,
        job_title: str,
        location: str,
        job_types: Optional[List[str]] = None,
        remote_types: Optional[List[str]] = None,
        time_period: Optional[str] = None,
        filter_text: Optional[str] = None,
        blacklist: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async implementation of the tool."""
        try:
            logger.info(f"Creating job search for user {user_id}: {job_title}")
            
            # Parse and validate inputs
            parsed_job_types = self._parse_job_types(job_types)
            parsed_remote_types = self._parse_remote_types(remote_types)
            parsed_time_period = self._parse_time_period(time_period)
            
            # Create JobSearchIn object
            job_search_in = JobSearchIn(
                job_title=job_title,
                location=location,
                job_types=parsed_job_types,
                remote_types=parsed_remote_types,
                time_period=parsed_time_period,
                user_id=user_id,
                filter_text=filter_text,
                blacklist=blacklist or []
            )
            
            # Create the search
            search_id = await self.job_search_manager.add_search(job_search_in)
            
            # Format success response
            job_types_str = ", ".join([jt.label for jt in parsed_job_types])
            remote_types_str = ", ".join([rt.label for rt in parsed_remote_types])
            
            result = f"""✅ **Job Search Created Successfully!**

🆔 **Search ID:** `{search_id}`
🔍 **Keywords:** {job_title}
📍 **Location:** {location}
💼 **Job Types:** {job_types_str}
🏠 **Remote Options:** {remote_types_str}
📅 **Search Frequency:** {parsed_time_period.display_name}
"""
            
            if filter_text:
                result += f"🔍 **Additional Filters:** {filter_text}\n"
            
            if blacklist:
                result += f"🚫 **Excluded Terms:** {', '.join(blacklist)}\n"
            
            result += f"""
**What happens next:**
- I'll automatically check for new jobs matching your criteria every {parsed_time_period.display_name.lower()}
- You'll receive notifications when new matching jobs are found
- The search will find jobs posted recently based on your search frequency

**Manage your search:**
- View all searches: "Show my job searches"
- Delete this search: "Delete search {search_id}"
- Get details: "Show details for search {search_id}"
"""
            
            logger.info(f"Successfully created job search {search_id} for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating job search for user {user_id}: {e}")
            
            # Generate contextual error response
            error_str = str(e).lower()
            
            if "duplicate" in error_str or "already exists" in error_str:
                return f"""❌ **Duplicate Job Search**

It looks like you already have a similar job search set up.

**What you can do:**
• Use "Show my job searches" to see your existing alerts
• Try modifying the job title or location to make it unique
• Delete an existing similar search first if you want to replace it

**Your request:** {job_title} in {location}"""
            
            elif "invalid" in error_str or "validation" in error_str:
                return f"""❌ **Invalid Information**

There's an issue with the job search details you provided.

**Please check:**
• **Job Title:** "{job_title}" - Make sure this describes a real job role
• **Location:** "{location}" - Use a specific city/country or "Remote"
• **Job Types:** {job_types if job_types else "All types"} - Use valid employment types
• **Remote Options:** {remote_types if remote_types else "All arrangements"} - Use valid remote preferences

Try rephrasing your request with clearer information."""
            
            elif "permission" in error_str or "auth" in error_str:
                return """❌ **Permission Error**

I don't have permission to create job searches for you right now.

**What you can do:**
• Try again in a moment
• Contact support if this continues
• Use /start to reinitialize our conversation"""
            
            elif "database" in error_str or "connection" in error_str:
                return """❌ **Service Temporarily Unavailable**

I'm having trouble saving your job search right now.

**What you can do:**
• Try again in a few moments
• The service may be temporarily busy
• Your request will be processed as soon as the connection is restored

I'll remember your conversation when you try again!"""
            
            else:
                return f"""❌ **Job Search Creation Failed**

I encountered an unexpected issue while creating your job search.

**Your details:**
• **Job Title:** {job_title}
• **Location:** {location}
• **Types:** {job_types if job_types else "All types"}

**What you can do:**
• Try rephrasing your request
• Use simpler terms for the job title
• Try creating the search again in a moment
• Use /help to see examples of successful requests

I'm here to help when you're ready to try again! 🤖"""
    
    def _run(
        self,
        user_id: int,
        job_title: str,
        location: str,
        job_types: Optional[List[str]] = None,
        remote_types: Optional[List[str]] = None,
        time_period: Optional[str] = None,
        filter_text: Optional[str] = None,
        blacklist: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Sync implementation (not used in async context)."""
        raise NotImplementedError("This tool only supports async execution") 