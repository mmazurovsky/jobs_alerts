"""
Telegram bot for job search management and notifications.
"""
import logging
from typing import List, Optional, Tuple
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.data.data import JobListing, JobSearchIn, JobType, RemoteType, TimePeriod
from src.user.job_search import job_search_manager

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot for job search management."""
    
    def __init__(self, token: str):
        """Initialize the bot with the given token."""
        self.application = Application.builder().token(token).build()
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Set up command handlers."""
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("add", self._handle_add))
        self.application.add_handler(CommandHandler("list", self._handle_list))
        self.application.add_handler(CommandHandler("remove", self._handle_remove))
    
    async def start(self) -> None:
        """Start the bot."""
        await self.application.initialize()
        await self.application.start()
        await self.application.run_polling()
    
    async def stop(self) -> None:
        """Stop the bot."""
        await self.application.stop()
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        user = update.effective_user
        welcome_message = (
            f"Welcome {user.first_name}! 👋\n\n"
            "I can help you manage your LinkedIn job searches. Here are the available commands:\n\n"
            "/add - Add a new job search\n"
            "/list - List your job searches\n"
            "/remove - Remove a job search"
        )
        await update.message.reply_text(welcome_message)
    
    def _parse_job_types(self, job_types_str: str) -> Tuple[List[JobType], str]:
        """Parse job types from string input."""
        job_types = []
        errors = []
        
        for job_type_str in job_types_str.split(','):
            job_type_str = job_type_str.strip()
            try:
                job_type = JobType(job_type_str)
                job_types.append(job_type)
            except ValueError:
                errors.append(f"Invalid job type: {job_type_str}")
        
        return job_types, ", ".join(errors) if errors else ""
    
    def _parse_remote_types(self, remote_types_str: str) -> Tuple[List[RemoteType], str]:
        """Parse remote types from string input."""
        remote_types = []
        errors = []
        
        for remote_type_str in remote_types_str.split(','):
            remote_type_str = remote_type_str.strip()
            try:
                remote_type = RemoteType(remote_type_str)
                remote_types.append(remote_type)
            except ValueError:
                errors.append(f"Invalid remote type: {remote_type_str}")
        
        return remote_types, ", ".join(errors) if errors else ""
    
    def _parse_time_period(self, time_period_str: str) -> Tuple[Optional[TimePeriod], str]:
        """Parse time period from string input."""
        try:
            time_period = TimePeriod[time_period_str.upper()]
            return time_period, ""
        except (KeyError, ValueError):
            return None, f"Invalid time period: {time_period_str}"
    
    async def _handle_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /add command."""
        try:
            # Check if we have all required arguments
            if len(context.args) < 5:
                await update.message.reply_text(
                    "Please provide all required parameters.\n"
                    "Usage: /add \"Job Title\" \"Location\" \"Job Types\" \"Remote Types\" \"Time Period\"\n\n"
                    "Job Types (comma-separated): Full-time, Part-time, Contract, Temporary, Internship\n"
                    "Remote Types (comma-separated): On-site, Remote, Hybrid\n"
                    "Time Period: MINUTES_5, MINUTES_10, MINUTES_15, MINUTES_30, MINUTES_60, HOURS_4\n\n"
                    "Example: /add \"Software Engineer\" \"San Francisco\" \"Full-time,Contract\" \"Remote,Hybrid\" \"MINUTES_15\""
                )
                return
            
            # Parse arguments
            job_title = context.args[0].strip('"')
            location = context.args[1].strip('"')
            job_types_str = context.args[2].strip('"')
            remote_types_str = context.args[3].strip('"')
            time_period_str = context.args[4].strip('"')
            
            # Validate job types
            job_types, job_types_error = self._parse_job_types(job_types_str)
            if job_types_error:
                await update.message.reply_text(
                    f"Error parsing job types: {job_types_error}\n"
                    "Valid job types are: Full-time, Part-time, Contract, Temporary, Internship"
                )
                return
            
            # Validate remote types
            remote_types, remote_types_error = self._parse_remote_types(remote_types_str)
            if remote_types_error:
                await update.message.reply_text(
                    f"Error parsing remote types: {remote_types_error}\n"
                    "Valid remote types are: On-site, Remote, Hybrid"
                )
                return
            
            # Validate time period
            time_period, time_period_error = self._parse_time_period(time_period_str)
            if time_period_error:
                await update.message.reply_text(
                    f"Error parsing time period: {time_period_error}\n"
                    "Valid time periods are: MINUTES_5, MINUTES_10, MINUTES_15, MINUTES_30, MINUTES_60, HOURS_4"
                )
                return
            
            # Create new job search
            new_search = JobSearchIn(
                job_title=job_title,
                location=location,
                job_types=job_types,
                remote_types=remote_types,
                time_period=time_period,
                user_id=update.effective_user.id
            )
            
            # Add job search
            job_search = job_search_manager.add_job_search(new_search)
            
            # Send confirmation message
            await update.message.reply_text(
                f"Added new job search:\n"
                f"Title: {job_search.job_title}\n"
                f"Location: {job_search.location}\n"
                f"Job Types: {', '.join(jt.value for jt in job_search.job_types)}\n"
                f"Remote Types: {', '.join(rt.value for rt in job_search.remote_types)}\n"
                f"Time Period: {job_search.time_period.name}\n"
                f"ID: {job_search.id}"
            )
            
        except Exception as e:
            logger.error(f"Error adding job search: {e}")
            await update.message.reply_text("Sorry, there was an error adding your job search.")
    
    async def _handle_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /list command."""
        try:
            user_id = update.effective_user.id
            job_searches = job_search_manager.get_user_job_searches(user_id)
            
            if not job_searches:
                await update.message.reply_text("You don't have any job searches yet.")
                return
            
            message = "Your job searches:\n\n"
            for search in job_searches:
                message += (
                    f"Title: {search.job_title}\n"
                    f"Location: {search.location}\n"
                    f"Job Types: {', '.join(jt.value for jt in search.job_types)}\n"
                    f"Remote Types: {', '.join(rt.value for rt in search.remote_types)}\n"
                    f"Time Period: {search.time_period.name}\n"
                    f"ID: {search.id}\n\n"
                )
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error listing job searches: {e}")
            await update.message.reply_text("Sorry, there was an error listing your job searches.")
    
    async def _handle_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /remove command."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Please provide the job search ID.\n"
                    "Usage: /remove <job_search_id>"
                )
                return
            
            search_id = context.args[0]
            user_id = update.effective_user.id
            
            if job_search_manager.remove_job_search(user_id, search_id):
                await update.message.reply_text(f"Removed job search with ID: {search_id}")
            else:
                await update.message.reply_text("Job search not found.")
            
        except Exception as e:
            logger.error(f"Error removing job search: {e}")
            await update.message.reply_text("Sorry, there was an error removing your job search.")
    
    def _format_job_listing(self, job: JobListing) -> str:
        """Format a single job listing as a string."""
        return (
            f"Title: {job.title}\n"
            f"Company: {job.company}\n"
            f"Location: {job.location}\n"
            f"Type: {job.job_type}\n"
            f"Link: {job.link}\n\n"
        )
    
    async def send_job_listings(self, user_id: int, jobs: List[JobListing]) -> None:
        """Send job listings to a user."""
        if not jobs:
            return
        
        try:
            # Maximum message length (Telegram has a 4096 character limit)
            MAX_MESSAGE_LENGTH = 4000
            
            # Prepare messages
            messages = []
            current_message = "New jobs found:\n\n"
            
            for job in jobs:
                job_text = self._format_job_listing(job)
                
                # Check if adding this job would exceed the limit
                if len(current_message) + len(job_text) > MAX_MESSAGE_LENGTH:
                    # Add current message to the list and start a new one
                    messages.append(current_message)
                    current_message = "New jobs found (continued):\n\n"
                
                # Add the job to the current message
                current_message += job_text
            
            # Add the last message if it contains any jobs
            if len(current_message) > len("New jobs found:\n\n"):
                messages.append(current_message)
            
            # Send all messages
            for message in messages:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    disable_web_page_preview=True
                )
                
        except Exception as e:
            logger.error(f"Error sending job listings to user {user_id}: {e}") 