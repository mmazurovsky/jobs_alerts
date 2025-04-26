"""
Telegram bot implementation for job search notifications.
"""
import logging
from typing import List, Optional, Tuple

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.error import TelegramError

from src.data.data import (
    JobSearchIn,
    JobSearchOut,
    JobListing,
    JobType,
    RemoteType,
    TimePeriod
)
from src.user.job_search import job_search_manager

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        """Initialize the Telegram bot.
        
        Args:
            token: Telegram bot token
        """
        self.token = token
        self.application = Application.builder().token(token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up command and message handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("add", self._handle_add))
        self.application.add_handler(CommandHandler("list", self._handle_list))
        self.application.add_handler(CommandHandler("remove", self._handle_remove))
        
        # Error handler
        self.application.add_error_handler(self._handle_error)
    
    def _get_command_help(self) -> str:
        """Get formatted help text with available options and example.
        
        Returns:
            Formatted help text with command usage, available options, and example.
        """
        # Format enum values with descriptions
        job_types = "\n".join(f"• {t.name} ({t.value})" for t in JobType)
        remote_types = "\n".join(f"• {t.name} ({t.value})" for t in RemoteType)
        time_periods = "\n".join(f"• {t.name} ({t.seconds//60} minutes)" for t in TimePeriod)
        
        return (
            "Command format:\n"
            "/add <job_title>;<location>;<job_types>;<remote_types>;<time_period>\n\n"
            "Example:\n"
            "/add Software Engineer;San Francisco;FULL_TIME,PART_TIME;REMOTE,HYBRID;MINUTES_30\n\n"
            "Available options:\n\n"
            "Job Types:\n"
            f"{job_types}\n\n"
            "Remote Types:\n"
            f"{remote_types}\n\n"
            "Time Periods:\n"
            f"{time_periods}\n\n"
            "Note: Use commas (,) to separate multiple values for job types and remote types."
        )
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} started the bot")
        
        welcome_message = (
            "👋 Welcome to the LinkedIn Job Alerts Bot!\n\n"
            "I can help you track job opportunities on LinkedIn. Here are the available commands:\n\n"
            "/add - Add a new job search\n"
            "/list - List your active job searches\n"
            "/remove <job_title> - Remove a job search\n\n"
            f"{self._get_command_help()}"
        )
        
        await update.message.reply_text(welcome_message)
    
    def _parse_job_types(self, job_types_str: str) -> Tuple[List[JobType], str]:
        """Parse job types from string input.
        
        Args:
            job_types_str: Comma-separated list of job types
            
        Returns:
            Tuple of (list of job types, error message if any)
        """
        job_types = []
        errors = []
        
        for job_type_str in job_types_str.split(','):
            job_type_str = job_type_str.strip()
            try:
                job_type = JobType[job_type_str]
                job_types.append(job_type)
            except KeyError:
                errors.append(f"Invalid job type: {job_type_str}")
        
        return job_types, ", ".join(errors) if errors else ""
    
    def _parse_remote_types(self, remote_types_str: str) -> Tuple[List[RemoteType], str]:
        """Parse remote types from string input.
        
        Args:
            remote_types_str: Comma-separated list of remote types
            
        Returns:
            Tuple of (list of remote types, error message if any)
        """
        remote_types = []
        errors = []
        
        for remote_type_str in remote_types_str.split(','):
            remote_type_str = remote_type_str.strip()
            try:
                remote_type = RemoteType[remote_type_str]
                remote_types.append(remote_type)
            except KeyError:
                errors.append(f"Invalid remote type: {remote_type_str}")
        
        return remote_types, ", ".join(errors) if errors else ""
    
    def _parse_time_period(self, time_period_str: str) -> Tuple[Optional[TimePeriod], str]:
        """Parse time period from string input.
        
        Args:
            time_period_str: Time period string
            
        Returns:
            Tuple of (time period if valid, error message if any)
        """
        try:
            time_period = TimePeriod[time_period_str]
            return time_period, ""
        except KeyError:
            return None, f"Invalid time period: {time_period_str}"
    
    async def _handle_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /add command."""
        user_id = update.effective_user.id
        
        # Check if command has arguments
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide all required parameters:\n\n"
                f"{self._get_command_help()}"
            )
            return
        
        # Join arguments and split by semicolon
        args = " ".join(context.args)
        parts = [part.strip() for part in args.split(';')]
        
        if len(parts) != 5:
            await update.message.reply_text(
                "❌ Please provide all required parameters separated by semicolons (;):\n\n"
                f"{self._get_command_help()}"
            )
            return
        
        job_title, location, job_types_str, remote_types_str, time_period_str = parts
        
        # Validate job types
        job_types, job_types_error = self._parse_job_types(job_types_str)
        if job_types_error:
            await update.message.reply_text(
                f"❌ Error parsing job types: {job_types_error}\n"
                f"Valid job types are: {', '.join(t.name for t in JobType)}"
            )
            return
        
        # Validate remote types
        remote_types, remote_types_error = self._parse_remote_types(remote_types_str)
        if remote_types_error:
            await update.message.reply_text(
                f"❌ Error parsing remote types: {remote_types_error}\n"
                f"Valid remote types are: {', '.join(t.name for t in RemoteType)}"
            )
            return
        
        # Validate time period
        time_period, time_period_error = self._parse_time_period(time_period_str)
        if time_period_error:
            await update.message.reply_text(
                f"❌ {time_period_error}\n"
                f"Valid time periods are: {', '.join(t.name for t in TimePeriod)}"
            )
            return
        
        # Create new job search
        new_search = JobSearchIn(
            user_id=user_id,
            job_title=job_title,
            location=location,
            job_types=job_types,
            remote_types=remote_types,
            time_period=time_period
        )
        
        # Add job search
        job_search_manager.add_job_search(new_search)
        
        # Send confirmation
        await update.message.reply_text(
            f"✅ Added job search:\n"
            f"Title: {job_title}\n"
            f"Location: {location}\n"
            f"Job Types: {', '.join(t.name for t in job_types)}\n"
            f"Remote Types: {', '.join(t.name for t in remote_types)}\n"
            f"Time Period: {time_period.name}"
        )
    
    async def _handle_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /list command."""
        user_id = update.effective_user.id
        searches = job_search_manager.get_user_job_searches(user_id)
        
        if not searches:
            await update.message.reply_text("You don't have any job searches configured.")
            return
        
        message = "Your job searches:\n\n"
        for search in searches:
            message += (
                f"🔍 ID: {search.id}\n"
                f"Title: {search.job_title}\n"
                f"Location: {search.location}\n"
                f"Job Types: {', '.join(t.name for t in search.job_types)}\n"
                f"Remote Types: {', '.join(t.name for t in search.remote_types)}\n"
                f"Time Period: {search.time_period.name}\n\n"
            )
        
        await update.message.reply_text(message)
    
    async def _handle_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /remove command."""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a search ID to remove:\n"
                "/remove <search_id>"
            )
            return
        
        search_id = context.args[0]
        
        if job_search_manager.remove_job_search(user_id, search_id):
            await update.message.reply_text(f"✅ Removed job search with ID '{search_id}'")
        else:
            await update.message.reply_text(f"❌ Job search with ID '{search_id}' not found")
    
    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the bot."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, an error occurred while processing your request."
            )
    
    async def initialize(self):
        """Initialize the bot."""
        logger.info("Initializing Telegram bot...")
        await self.application.initialize()
        logger.info("Telegram bot initialized")
    
    async def start_polling(self):
        """Start the bot's polling."""
        logger.info("Starting Telegram bot polling...")
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram bot polling started")
    
    async def stop(self):
        """Stop the bot."""
        logger.info("Stopping Telegram bot...")
        await self.application.stop()
        logger.info("Telegram bot stopped")
    
    async def send_job_listings(self, user_id: int, jobs: List[JobListing]):
        """Send job listings to a user.
        
        Args:
            user_id: Telegram user ID
            jobs: List of job listings to send
        """
        if not jobs:
            return
        
        # Format all job listings
        formatted_jobs = [self._format_job_listing(job) for job in jobs]
        
        # Try to send all jobs in one message
        message = "🔔 New job listings found!\n\n" + "\n\n".join(formatted_jobs)
        
        try:
            # Check if message is too long
            if len(message) > 4096:  # Telegram's message length limit
                # Split into multiple messages
                current_message = "🔔 New job listings found!\n\n"
                
                for job in formatted_jobs:
                    # Check if adding this job would exceed the limit
                    if len(current_message) + len(job) + 3 > 4096:  # +3 for "\n\n"
                        # Send current message and start a new one
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=current_message
                        )
                        current_message = "📄 Continued...\n\n" + job + "\n\n"
                    else:
                        current_message += job + "\n\n"
                
                # Send the last message if it's not empty
                if current_message:
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=current_message
                    )
            else:
                # Send all jobs in one message
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message
                )
        except TelegramError as e:
            logger.error(f"Failed to send job listings to user {user_id}: {e}")
    
    def _format_job_listing(self, job: JobListing) -> str:
        """Format a job listing for display.
        
        Args:
            job: Job listing to format
            
        Returns:
            Formatted job listing string
        """
        return (
            f"🏢 {job.company}\n"
            f"💼 {job.title}\n"
            f"📍 {job.location}\n"
            f"💼 {job.job_type}\n"
            f"🔗 {job.link}"
        ) 