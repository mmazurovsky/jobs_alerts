"""
LangChain tool for creating new job searches.
"""
import logging
from typing import Type, Optional, List, Any
from pydantic import BaseModel, Field, field_validator
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
    job_types: Optional[List[str]] = Field(default=None, description=f"List of job types. Valid options: {', '.join(get_job_types())}. Leave empty for all types.")
    remote_types: Optional[List[str]] = Field(default=None, description=f"Remote work preferences. Valid options: {', '.join(get_remote_types())}. Leave empty for all types.")
    time_period: Optional[str] = Field(default=None, description=f"How frequently to check for new jobs. Valid options: {', '.join(get_time_periods())}. Default is '{get_default_time_period()}' if not specified.")
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
    
    @field_validator('time_period')
    @classmethod
    def validate_time_period(cls, v):
        if v is None:
            return v
        valid_periods = get_time_periods()
        if v not in valid_periods:
            raise ValueError(f"Invalid time period: '{v}'. Valid options are: {', '.join(valid_periods)}")
        return v


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
    - filter_text: 🌟 Our unique AI-powered smart filter! Use natural language to describe what you want to EXCLUDE from results
    
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
                    example=get_default_job_type(),
                    validation_rules=f"Must choose from: {', '.join(get_job_types())}. Leave empty to include all types."
                ),
                ParameterInfo(
                    name="remote_types",
                    description="Remote work preferences",
                    type=InputType.MULTISELECT,
                    required=False,
                    options=get_remote_types(),
                    example="Remote",
                    validation_rules=f"Must choose from: {', '.join(get_remote_types())}. Leave empty to include all arrangements."
                ),
                ParameterInfo(
                    name="time_period",
                    description="How frequently to search for new jobs",
                    type=InputType.SELECT,
                    required=False,
                    options=get_time_periods(),
                    example=get_default_time_period(),
                    validation_rules=f"Must choose from: {', '.join(get_time_periods())}. Defaults to '{get_default_time_period()}' if not specified."
                ),
                ParameterInfo(
                    name="filter_text",
                    description="🌟 Our unique AI-powered smart filter! Use natural language to describe what you want to EXCLUDE from results",
                    type=InputType.TEXT,
                    required=False,
                    example="No entry level positions, no travel required, no security clearance needed, exclude startups",
                    validation_rules="This is our signature feature - use natural language to describe what you DON'T want. The AI understands context and filters accordingly. Examples: 'No entry level', 'Avoid companies with less than 100 employees', 'No weekend work'"
                )
            ],
            examples=[
                "Create a search for Python developer jobs in Berlin with full-time contracts",
                "I want to set up alerts for remote data scientist positions - check every hour",
                "Create a search for React developer jobs in London - hybrid or remote preferred, filter out entry level positions",
                "Set up alerts for marketing manager roles - part-time or contract work, exclude travel requirements"
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
        
        return parsed_types if parsed_types else [JobType.parse(get_default_job_type())]
    
    def _parse_remote_types(self, remote_types: Optional[List[str]]) -> List[RemoteType]:
        """Parse remote type strings to RemoteType instances."""
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
    
    def _parse_time_period(self, time_period: Optional[str]) -> TimePeriod:
        """Parse time period string to TimePeriod instance."""
        if not time_period:
            return TimePeriod.parse(get_default_time_period())  # Default to 1 hour
        
        valid_periods = get_time_periods()
        if time_period not in valid_periods:
            raise ValueError(f"Invalid time period: '{time_period}'. Valid options are: {', '.join(valid_periods)}")
        
        try:
            return TimePeriod.parse(time_period)
        except ValueError:
            raise ValueError(f"Invalid time period: '{time_period}'. Valid options are: {', '.join(valid_periods)}")
    
    async def _arun(
        self,
        user_id: int,
        job_title: str,
        location: str,
        job_types: Optional[List[str]] = None,
        remote_types: Optional[List[str]] = None,
        time_period: Optional[str] = None,
        filter_text: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async implementation of the tool."""
        try:
            logger.info(f"Creating job search for user {user_id}: {job_title}")
            
            # Parse and validate inputs
            try:
                parsed_job_types = self._parse_job_types(job_types)
                parsed_remote_types = self._parse_remote_types(remote_types)
                parsed_time_period = self._parse_time_period(time_period)
            except ValueError as e:
                # Return validation error with helpful information
                error_msg = str(e)
                return f"""❌ **Invalid Input**

{error_msg}

**Please specify valid values:**
• **Job Types:** {', '.join(get_job_types())}
• **Remote Types:** {', '.join(get_remote_types())}
• **Time Periods:** {', '.join(get_time_periods())}

❓ Would you like to try again with the correct values?"""
            
            # Create JobSearchIn object
            job_search_in = JobSearchIn(
                job_title=job_title,
                location=location,
                job_types=parsed_job_types,
                remote_types=parsed_remote_types,
                time_period=parsed_time_period,
                user_id=user_id,
                filter_text=filter_text,
            )
            
            # Add search via manager
            search_id = await self.job_search_manager.add_search(job_search_in)
            
            # Format successful response
            job_types_str = ", ".join([jt.label for jt in parsed_job_types])
            remote_types_str = ", ".join([rt.label for rt in parsed_remote_types])
            
            result = f"""✅ **Job Search Created Successfully!**

**Search Details:**
🔍 **Job:** {job_title}
📍 **Location:** {location}
💼 **Types:** {job_types_str}
🏠 **Remote:** {remote_types_str}
⏰ **Frequency:** Every {parsed_time_period.display_name.lower()}
"""
            
            if filter_text:
                result += f"🔍 **Additional Filters:** {filter_text}\n"
            
            result += f"""
**What happens next:**
✅ I'll automatically check for new jobs every {parsed_time_period.display_name.lower()}
✅ You'll receive notifications when relevant positions are found
✅ Only jobs matching your criteria will be sent to you

**Manage your search:**
• View details: "Show my job searches"
• Modify: "Update my {job_title} search"
• Delete: "Delete my {job_title} search"
"""
            
            logger.info(f"Successfully created job search {search_id} for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating job search for user {user_id}: {e}")
            return f"""❌ **Failed to Create Job Search**

Sorry, I couldn't create your job search due to a technical issue.

**Error:** {str(e)}

**What you can do:**
• Try again in a few moments
• Simplify your search parameters
• Contact support if the problem persists

❓ Would you like to try creating the search again?"""
    
    def _run(
        self,
        user_id: int,
        job_title: str,
        location: str,
        job_types: Optional[List[str]] = None,
        remote_types: Optional[List[str]] = None,
        time_period: Optional[str] = None,
        filter_text: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Sync implementation (not used in async context)."""
        raise NotImplementedError("This tool only supports async execution") 