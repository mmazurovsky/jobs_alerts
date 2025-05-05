"""
Telegram bot module.
"""
import logging
import os
from typing import Dict, List, Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode
from datetime import datetime
import asyncio

from src.core.config import Config
from src.core.linkedin_scraper import LinkedInScraper
from src.data.data import (
    JobSearchOut, JobListing, JobSearchIn, JobType, RemoteType, TimePeriod,
    StreamType, StreamEvent, StreamManager, JobSearchRemove
)
from src.data.mongo_manager import MongoManager
from src.user.job_search_manager import JobSearchManager

logger = logging.getLogger(__name__)

# Conversation states
TITLE, LOCATION, JOB_TYPES, REMOTE_TYPES, TIME_PERIOD, CONFIRM = range(6)

class TelegramBot:
    """Telegram bot for managing job searches."""
    
    def __init__(self, token: str, mongo_manager: MongoManager, stream_manager: StreamManager, job_search_manager: JobSearchManager):
        """Initialize the bot with token and MongoDB manager."""
        self.token = token
        self.mongo_manager = mongo_manager
        self.stream_manager = stream_manager
        self.job_search_manager = job_search_manager
        self.application = Application.builder().token(token).build()
        self._setup_handlers()

        # Subscribe to send message stream
        self.stream_manager.get_stream(StreamType.SEND_MESSAGE).subscribe(
            lambda event: asyncio.create_task(self._handle_send_message(event))
        )
    
    def _setup_handlers(self):
        """Set up all command and conversation handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("list", self.list_searches))
        self.application.add_handler(CommandHandler("delete", self.delete_search))
        self.application.add_handler(CommandHandler("newRaw", self.new_raw_search))
        
        # Conversation handler for creating new job searches
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("new", self.new_search)],
            states={
                TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.title)],
                LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.location)],
                JOB_TYPES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.job_types)],
                REMOTE_TYPES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.remote_types)],
                TIME_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.time_period)],
                CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm)],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler("new", self.new_search),
                CommandHandler("list", self.list_searches),
                CommandHandler("delete", self.delete_search),
                CommandHandler("help", self.help),
                CommandHandler("start", self.start)
            ],
            per_message=False
        )
        self.application.add_handler(conv_handler)
    
    # Command handlers
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        self._clear_conversation_state(context)
        user = update.effective_user
        await update.message.reply_text(
            f"Hi {user.first_name}! I'm your job search assistant. "
            "Use /help to see available commands."
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        self._clear_conversation_state(context)
        help_text = (
            "Available commands:\n"
            "/new - Create a new job search\n"
            "/list - List your job searches\n"
            "/delete - Delete a job search\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_text)
    
    async def list_searches(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List all job searches for the user."""
        self._clear_conversation_state(context)
        try:
            from src.core.container import get_container
            container = get_container()
            searches: List[JobSearchOut] = await container.job_search_manager.get_user_searches(update.effective_user.id)
            
            if not searches:
                await update.message.reply_text("You don't have any job searches yet.")
                return
                
            message = "Your job searches:\n\n"
            for search in searches:
                job_types = ", ".join(t.value for t in search.job_types)
                remote_types = ", ".join(t.value for t in search.remote_types)
                message += (
                    f"Title: {search.job_title}\n"
                    f"Location: {search.location}\n"
                    f"Job Types: {job_types}\n"
                    f"Remote Types: {remote_types}\n"
                    f"Check Frequency: {search.time_period.display_name}\n"
                    f"Created At: {search.created_at}\n\n"
                )
                
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error listing job searches: {e}")
            await update.message.reply_text(
                "Sorry, there was an error listing your job searches. Please try again."
            )
    
    async def delete_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Delete a job search."""
        self._clear_conversation_state(context)
        try:
            args = context.args
            if not args:
                await update.message.reply_text(
                    "Please provide a job search ID to delete. Usage: /delete <search_id>"
                )
                return
                
            search_id = args[0]
            
            # Create JobSearchRemove instance and pass it directly
            job_search_remove = JobSearchRemove(
                user_id=update.effective_user.id,
                search_id=search_id
            )

            await self.job_search_manager.delete_search(job_search_remove)
            await update.message.reply_text("Your job search will be removed shortly.")
            
        except Exception as e:
            logger.error(f"Error deleting job search: {e}")
            await update.message.reply_text(
                "Sorry, there was an error deleting your job search. Please try again."
            )
    
    # Conversation handlers
    async def new_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the conversation for creating a new job search."""
        self._clear_conversation_state(context)
        await update.message.reply_text(
            "Let's create a new job search! Please enter the job title.\n\n"
            "Examples:\n"
            "• Software Engineer\n"
            "• Data Scientist"
        )
        return TITLE
    
    async def title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle job title input."""
        context.user_data['title'] = update.message.text
        await update.message.reply_text(
            "Now enter the location where you want to search for jobs.\n\n"
            "Examples:\n"
            "• United States\n"
            "• New York City\n"
            "• Europe"
        )
        return LOCATION
    
    async def location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle location input."""
        context.user_data['location'] = update.message.text
        
        # Show available job types and instructions
        job_types_list = "\n".join(f"• {job_type.value}" for job_type in JobType)
        await update.message.reply_text(
            "Select job types (you can choose multiple).\n\n"
            "Available job types:\n"
            f"{job_types_list}\n\n"
            "Enter job types separated by commas, e.g.:\n"
            "Full-time, Part-time, Contract"
        )
        return JOB_TYPES
    
    async def job_types(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle job types selection."""
        # Parse job types from input
        input_text = update.message.text.strip()
        job_types = [t.strip() for t in input_text.split(',')]
        
        # Convert input to JobType enum by matching against values
        selected_types = []
        for job_type in job_types:
            for enum_type in JobType:
                if job_type.lower() == enum_type.value.lower():
                    selected_types.append(enum_type)
                    break
        
        context.user_data['job_types'] = selected_types
        
        if not context.user_data['job_types']:
            # Show available job types for reference
            job_types_list = "\n".join(f"• {job_type.value}" for job_type in JobType)
            await update.message.reply_text(
                "No valid job types selected. Please try again with valid job types.\n\n"
                "Available job types:\n"
                f"{job_types_list}\n\n"
                "Enter job types separated by commas, e.g.:\n"
                "Full-time, Part-time, Contract"
            )
            return JOB_TYPES
            
        # Show available remote types and instructions
        remote_types_list = "\n".join(f"• {remote_type.value}" for remote_type in RemoteType)
        await update.message.reply_text(
            "Select remote work types (you can choose multiple).\n\n"
            "Available remote types:\n"
            f"{remote_types_list}\n\n"
            "Enter remote types separated by commas, e.g.:\n"
            "Remote, Hybrid, On-site"
        )
        return REMOTE_TYPES
    
    async def remote_types(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle remote types selection."""
        # Parse remote types from input
        input_text = update.message.text.strip()
        remote_types = [t.strip() for t in input_text.split(',')]
        
        # Convert input to RemoteType enum by matching against values
        selected_types = []
        for remote_type in remote_types:
            for enum_type in RemoteType:
                if remote_type.lower() == enum_type.value.lower():
                    selected_types.append(enum_type)
                    break
        
        context.user_data['remote_types'] = selected_types
        
        if not context.user_data['remote_types']:
            # Show available remote types for reference
            remote_types_list = "\n".join(f"• {remote_type.value}" for remote_type in RemoteType)
            await update.message.reply_text(
                "No valid remote types selected. Please try again with valid remote types.\n\n"
                "Available remote types:\n"
                f"{remote_types_list}\n\n"
                "Enter remote types separated by commas, e.g.:\n"
                "Remote, Hybrid, On-site"
            )
            return REMOTE_TYPES
            
        # Show available time periods and instructions
        time_periods_list = "\n".join(f"• {period.display_name}" for period in TimePeriod)
        await update.message.reply_text(
            "Select how often to check for new jobs.\n\n"
            "Available time periods:\n"
            f"{time_periods_list}\n\n"
            "Enter one of the time periods above, e.g.:\n"
            "Daily"
        )
        return TIME_PERIOD
    
    async def time_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle time period selection."""
        # Parse time period from input
        input_text = update.message.text.strip()
        
        # Convert input to TimePeriod enum by matching against display names
        selected_period = None
        for period in TimePeriod:
            if input_text.lower() == period.display_name.lower():
                selected_period = period
                break
        
        if not selected_period:
            # Show available time periods for reference
            time_periods_list = "\n".join(f"• {period.display_name}" for period in TimePeriod)
            await update.message.reply_text(
                "No valid time period selected. Please try again with a valid time period.\n\n"
                "Available time periods:\n"
                f"{time_periods_list}\n\n"
                "Enter one of the time periods above, e.g.:\n"
                "5 minutes"
            )
            return TIME_PERIOD
            
        context.user_data['time_period'] = selected_period
        
        # Show confirmation message
        await update.message.reply_text(
            "Please confirm your job search by typing 'yes' or cancel by typing 'no'."
        )
        
        return CONFIRM
    
    async def confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle confirmation of job search creation."""
        input_text = update.message.text.strip().lower()
        
        if input_text == 'no':
            await update.message.reply_text("Job search creation cancelled.")
            return ConversationHandler.END
            
        if input_text != 'yes':
            await update.message.reply_text("Please type 'yes' to confirm or 'no' to cancel.")
            return CONFIRM
            
        try:
            # Create JobSearchIn instance and pass it directly
            job_search_in = JobSearchIn(
                job_title=context.user_data['title'],
                location=context.user_data['location'],
                job_types=context.user_data['job_types'],
                remote_types=context.user_data['remote_types'],
                time_period=context.user_data['time_period'],
                user_id=update.effective_user.id
            )

            await self.job_search_manager.add_search(job_search_in)
            
            await update.message.reply_text("Your job search has been created and will be processed shortly.")
            
        except Exception as e:
            logger.error(f"Error creating job search: {e}")
            await update.message.reply_text(
                "Sorry, there was an error creating your job search. Please try again."
            )
            
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation."""
        self._clear_conversation_state(context)
        await update.message.reply_text("Job search creation cancelled.")
        return ConversationHandler.END
    
    # Utility methods
    def _clear_conversation_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear the conversation state."""
        if hasattr(context, 'user_data'):
            context.user_data.clear()
    
    # Bot lifecycle methods
    def run(self):
        """Run the bot."""
        self.application.run_polling()
    
    async def initialize(self) -> None:
        """Initialize the bot."""
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            raise
            
    async def stop(self) -> None:
        """Stop the bot."""
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot stopped")
        except Exception as e:
            logger.error(f"Failed to stop Telegram bot: {e}")
            raise

    async def send_job_listings(self, user_id: int, jobs: List[JobListing]) -> None:
        """Send job listings to a user."""
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
        except Exception as e:
            logger.error(f"Error sending job listings to user {user_id}: {e}")
    
    def _format_job_listing(self, job: JobListing) -> str:
        """Format a job listing for display."""
        return (
            f"🏢 {job.company}\n"
            f"💼 {job.title}\n"
            f"📍 {job.location}\n"
            f"💼 {job.job_type}\n"
            f"🔗 {job.link}"
        )

    async def _handle_send_message(self, event: StreamEvent):
        """Handle message sending requests from other components"""
        try:
            message_data = event.data
            await self.application.bot.send_message(
                chat_id=message_data["user_id"],
                text=message_data["message"]
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def new_raw_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle raw job search creation with format: /newRaw title;location;job_type;remote_types;time_period"""
        try:
            # Get the full message text and remove the command
            message_text = update.message.text
            if not message_text.startswith('/newRaw '):
                await update.message.reply_text(
                    "Please provide job search details in format:\n"
                    "/newRaw title;location;job_type;remote_types;time_period\n\n"
                    "Example:\n"
                    "/newRaw Solution Architect;Germany;FULL_TIME;REMOTE,HYBRID;MINUTES_5"
                )
                return

            # Extract the data part after the command
            raw_data = message_text[len('/newRaw '):].split(';')
            if len(raw_data) != 5:
                await update.message.reply_text(
                    "Invalid format. Please use:\n"
                    "/newRaw title;location;job_type;remote_types;time_period"
                )
                return

            title, location, job_type, remote_types, time_period = raw_data

            # Parse enums
            try:
                job_types = [JobType.parse(job_type.strip())]
                remote_types_list = [RemoteType.parse(rt.strip()) for rt in remote_types.split(',')]
                time_period_enum = TimePeriod.parse(time_period.strip())
            except ValueError as e:
                await update.message.reply_text(f"Error parsing input: {str(e)}")
                return

            # Create JobSearchIn instance and pass it directly
            job_search_in = JobSearchIn(
                job_title=title,
                location=location,
                job_types=job_types,
                remote_types=remote_types_list,
                time_period=time_period_enum,
                user_id=update.effective_user.id
            )

            await self.job_search_manager.add_search(job_search_in)

            await update.message.reply_text("Your job search has been created and will be processed shortly.")

        except Exception as e:
            logger.error(f"Error creating raw job search: {e}")
            await update.message.reply_text(
                "Sorry, there was an error creating your job search. Please check the format and try again."
            ) 