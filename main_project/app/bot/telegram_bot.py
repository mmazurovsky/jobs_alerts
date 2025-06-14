"""
Telegram bot module.
"""
import logging
import os
from typing import Dict, List, Optional
from telegram import Update, Message
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

from shared.data import (
    JobSearchOut, JobListing, JobSearchIn, JobType, RemoteType, TimePeriod,
    StreamType, StreamEvent, StreamManager, JobSearchRemove,
    job_types_list, remote_types_list, time_periods_list
)
from main_project.app.core.job_search_manager import JobSearchManager

logger = logging.getLogger(__name__)

# Conversation states
TITLE, LOCATION, JOB_TYPES, REMOTE_TYPES, TIME_PERIOD, FILTER_TEXT, CONFIRM = range(7)

try:
    ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
except (TypeError, ValueError):
    raise RuntimeError("ADMIN_USER_ID environment variable must be set and be an integer.")

class TelegramBot:
    """Telegram bot for managing job searches."""
    
    def __init__(self, token: str, stream_manager: StreamManager, job_search_manager: JobSearchManager):
        """Initialize the bot with token and MongoDB manager."""
        self.token = token
        self.stream_manager = stream_manager
        self.job_search_manager = job_search_manager
        self.application = Application.builder().token(token).build()
        self._setup_handlers()

        # Subscribe to send message stream
        self.stream_manager.get_stream(StreamType.SEND_MESSAGE).subscribe(
            lambda event: asyncio.create_task(self._handle_send_message(event))
        )
        self.stream_manager.get_stream(StreamType.SEND_LOG).subscribe(
            lambda event: asyncio.create_task(self._handle_send_log(event))
        )
    
    def _setup_handlers(self):
        """Set up all command and conversation handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("list", self.list_searches))
        self.application.add_handler(CommandHandler("delete", self.delete_search))
        self.application.add_handler(CommandHandler("newRaw", self.new_raw_search))
        self.application.add_handler(CommandHandler("oneTimeDeepSearch", self.one_time_deep_search))
        
        # Message handler for one-time search confirmations
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_one_time_search_confirmation
        ), group=1)
        
        # Conversation handler for creating new job searches
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("new", self.new_search)],
            states={
                TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.title)],
                LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.location)],
                JOB_TYPES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.job_types)],
                REMOTE_TYPES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.remote_types)],
                TIME_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.time_period)],
                FILTER_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.filter_text)],
                CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm)],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler("new", self.new_search),
                CommandHandler("list", self.list_searches),
                CommandHandler("delete", self.delete_search),
                CommandHandler("help", self.help),
                CommandHandler("start", self.start),
                CommandHandler("oneTimeDeepSearch", self.one_time_deep_search)
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
            "/newRaw - Create a new job search with a single command (advanced)\n"
            "/oneTimeDeepSearch - Perform immediate deep search with LLM filtering\n"
            "/list - List your job searches\n"
            "/delete - Delete a job search\n"
            "/help - Show this help message\n\n"
            "*Advanced: /newRaw usage*\n"
            "/newRaw <job_title>;<location>;<job_type>;<remote_type>;<time_period>[;<filter_prompt>]\n"
            "Example: /newRaw Software Engineer;Germany;Full-time;Remote;5 minutes;Senior level no German required\n\n"
            "*One-time deep search: /oneTimeDeepSearch usage*\n"
            "/oneTimeDeepSearch <job_title>;<location>;<job_type>;<remote_type>;<filter_prompt>\n"
            "Example: /oneTimeDeepSearch Python Developer;Remote;Full-time;Remote;Don't include hybrid options, don't include jobs that require German language, don't include analyst jobs\n\n"
            "Available values:\n"
            "- Job types: Full-time, Part-time, Contract, Temporary, Internship\n"
            "- Remote types: On-site, Remote, Hybrid\n"
            "- Time periods: 5 minutes, 10 minutes, 15 minutes, 30 minutes, 1 hour, 4 hours, 24 hours\n"
            "- Filter prompt: Optional freeform text (max 300 chars) for LLM-based job filtering"
        )
        await update.message.reply_text(help_text)
    
    async def list_searches(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List all job searches for the user."""
        self._clear_conversation_state(context)
        try:
            searches: List[JobSearchOut] = await self.job_search_manager.get_user_searches(update.effective_user.id)
            
            if not searches:
                await update.message.reply_text("You don't have any job searches yet.")
                return
                
            message = "Your job searches:\n\n"
            for search in searches:
                job_types = ", ".join(t.label for t in search.job_types)
                remote_types = ", ".join(t.label for t in search.remote_types)
                message += (
                    f"ID: {search.id}\n"
                    f"Title: {search.job_title}\n"
                    f"Location: {search.location}\n"
                    f"Job Types: {job_types}\n"
                    f"Remote Types: {remote_types}\n"
                    f"Check Frequency: {search.time_period.display_name}\n"
                )
                if hasattr(search, 'filter_text') and search.filter_text:
                    message += f"Filter: {search.filter_text}\n"
                message += f"Created At: {search.created_at}\n\n"
                
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
        await update.message.reply_text(
            "Select job types (you can choose multiple).\n\n"
            f"Available job types:\n{job_types_list()}\n\n"
            "Enter job types separated by commas, e.g.:\n"
            "Full-time, Part-time, Contract"
        )
        return JOB_TYPES
    
    def _parse_job_types(self, job_types_str: str) -> List[JobType]:
        return [JobType.parse(jt.strip()) for jt in job_types_str.split(',') if jt.strip()]

    def _parse_remote_types(self, remote_types_str: str) -> List[RemoteType]:
        return [RemoteType.parse(rt.strip()) for rt in remote_types_str.split(',') if rt.strip()]

    def _parse_blacklist(self, blacklist_str: str) -> List[str]:
        return [s.strip() for s in blacklist_str.split(',') if s.strip()]

    def _format_confirmation_message(self, title, location, job_types, remote_types, time_period, blacklist, search_id=None, filter_text=None):
        msg = ""
        if search_id:
            msg += f"Search ID: {search_id}\n"
        msg += (
            f"Job: {title}\n"
            f"Location: {location}\n"
            f"Type: {', '.join(jt.label for jt in job_types)}\n"
            f"Remote: {', '.join(rt.label for rt in remote_types)}\n"
            f"Check every: {time_period.display_name}\n"
        )
        if filter_text:
            msg += f"Filter: {filter_text}\n"
        return msg

    async def job_types(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        input_text = update.message.text.strip()
        selected_types = []
        try:
            selected_types = self._parse_job_types(input_text)
        except Exception:
            pass
        context.user_data['job_types'] = selected_types
        if not context.user_data['job_types']:
            await update.message.reply_text(
                "No valid job types selected. Please try again with valid job types.\n\n"
                f"Available job types:\n{job_types_list()}\n\n"
                "Enter job types separated by commas, e.g.:\nFull-time, Part-time, Contract"
            )
            return JOB_TYPES
        await update.message.reply_text(
            "Select remote work types (you can choose multiple).\n\n"
            f"Available remote types:\n{remote_types_list()}\n\n"
            "Enter remote types separated by commas, e.g.:\nRemote, Hybrid, On-site"
        )
        return REMOTE_TYPES
    
    async def remote_types(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        input_text = update.message.text.strip()
        selected_types = []
        try:
            selected_types = self._parse_remote_types(input_text)
        except Exception:
            pass
        context.user_data['remote_types'] = selected_types
        if not context.user_data['remote_types']:
            await update.message.reply_text(
                "No valid remote types selected. Please try again with valid remote types.\n\n"
                f"Available remote types:\n{remote_types_list()}\n\n"
                "Enter remote types separated by commas, e.g.:\nRemote, Hybrid, On-site"
            )
            return REMOTE_TYPES
        await update.message.reply_text(
            "Select how often to check for new jobs.\n\n"
            f"Available time periods:\n{time_periods_list()}\n\n"
            "Enter one of the time periods above, e.g.:\n5 minutes"
        )
        return TIME_PERIOD
    
    async def time_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle time period selection."""
        input_text = update.message.text.strip()
        try:
            selected_period = TimePeriod.parse(input_text)
        except ValueError:
            selected_period = None
        if not selected_period:
            await update.message.reply_text(
                "No valid time period selected. Please try again with a valid time period.\n\n"
                f"Available time periods:\n{time_periods_list()}\n\n"
                "Enter one of the time periods above, e.g.:\n5 minutes"
            )
            return TIME_PERIOD
        context.user_data['time_period'] = selected_period
        await update.message.reply_text(
            "Optional: Enter a filter prompt for LLM-based job filtering (max 300 characters).\n"
            "This allows you to specify requirements like seniority, technologies, or restrictions.\n"
            "For example: Don't include junior level jobs, no German should berequired\n\n"
            "Or just type '-' to skip."
        )
        return FILTER_TEXT
    
    async def filter_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle filter text input."""
        input_text = update.message.text.strip()
        if input_text == '-' or not input_text:
            context.user_data['filter_text'] = None
        else:
            if len(input_text) > 300:
                await update.message.reply_text(
                    "❌ Filter prompt is too long. Maximum 300 characters allowed. Please try again."
                )
                return FILTER_TEXT
            context.user_data['filter_text'] = input_text
        
        # Show job search summary and ask for confirmation
        job_title = context.user_data['title']
        location = context.user_data['location']
        job_types = context.user_data['job_types']
        remote_types = context.user_data['remote_types']
        time_period = context.user_data['time_period']
        filter_text = context.user_data.get('filter_text')
        msg = self._format_confirmation_message(job_title, location, job_types, remote_types, time_period, [], None, filter_text)
        msg += "\nPlease confirm your job search by typing 'yes' or cancel by typing 'no'."
        await update.message.reply_text(msg)
        return CONFIRM
    
    async def confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        input_text = update.message.text.strip().lower()
        if input_text == 'no':
            await update.message.reply_text("Job search creation cancelled.")
            return ConversationHandler.END
        if input_text != 'yes':
            await update.message.reply_text("Please type 'yes' to confirm or 'no' to cancel.")
            return CONFIRM
        
        try:
            # Regular job search creation
            job_title = context.user_data['title']
            location = context.user_data['location']
            job_types = context.user_data['job_types']
            remote_types = context.user_data['remote_types']
            time_period = context.user_data['time_period']
            filter_text = context.user_data.get('filter_text')
            job_search_in = JobSearchIn(
                job_title=job_title,
                location=location,
                job_types=job_types,
                remote_types=remote_types,
                time_period=time_period,
                user_id=update.effective_user.id,
                blacklist=[],
                filter_text=filter_text
            )
            search_id = await self.job_search_manager.add_search(job_search_in)
            msg = self._format_confirmation_message(job_title, location, job_types, remote_types, time_period, [], search_id, filter_text)
            await update.message.reply_text(msg)
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

    async def _handle_send_log(self, event: StreamEvent) -> None:
        try:
            message = event.data.get("message")
            image_path = event.data.get("image_path")
            if not message:
                logger.error("No message provided in log event data")
                return
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as img:
                    await self.application.bot.send_photo(
                        chat_id=ADMIN_USER_ID,
                        photo=img,
                        caption=message
                    )
            else:
                await self.application.bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=message
                )
        except Exception as e:
            logger.error(f"Failed to send log to admin: {e}")

    async def _handle_send_message(self, event: StreamEvent):
        """Handle message sending requests from other components"""
        try:
            message_data = event.data
            user_id = message_data.get("user_id")
            message = message_data.get("message")
            image_path = message_data.get("image_path")
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as img:
                    await self.application.bot.send_photo(
                        chat_id=user_id,
                        photo=img,
                        caption=message
                    )
            else:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message, 
                    parse_mode=None
                )
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def new_raw_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            raw_input = update.message.text.split('/newRaw ')[1].strip()
            parts = raw_input.split(';')
            if len(parts) < 5 or len(parts) > 6:
                await update.message.reply_text(
                    "Invalid format. Please use:\n"
                    "/newRaw <job_title>;<location>;<job_type>;<remote_type>;<time_period>[;<filter_prompt>]\n\n"
                    "Example: /newRaw Software Engineer;Germany;Full-time,Part-time;Remote,Hybrid;5 minutes;No requirement about German language\n\n"
                    "Available values:\n"
                    "- Job types: Full-time, Part-time, Contract, Temporary, Internship\n"
                    "- Remote types: On-site, Remote, Hybrid\n"
                    "- Time periods: 5 minutes, 15 minutes, 30 minutes, 1 hour, 4 hours, 24 hours\n"
                    "- Filter prompt: Optional freeform text (max 300 chars) for LLM-based job filtering"
                )
                return
            title, location, job_type, remote_types, time_period = parts[:5]
            filter_text = None
            if len(parts) == 6:
                filter_text = parts[5].strip()
                if len(filter_text) > 300:
                    await update.message.reply_text(
                        "❌ Filter prompt is too long. Maximum 300 characters allowed."
                    )
                    return
            job_type_enums = self._parse_job_types(job_type)
            remote_type_enums = self._parse_remote_types(remote_types)
            time_period_enum = TimePeriod.parse(time_period.strip())
            job_search_in = JobSearchIn(
                job_title=title.strip(),
                location=location.strip(),
                job_types=job_type_enums,
                remote_types=remote_type_enums,
                time_period=time_period_enum,
                user_id=update.effective_user.id,
                blacklist=[],
                filter_text=filter_text
            )
            search_id = await self.job_search_manager.add_search(job_search_in)
            msg = self._format_confirmation_message(title, location, job_type_enums, remote_type_enums, time_period_enum, [], search_id, filter_text)
            await update.message.reply_text(msg)
        except ValueError as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}\n\n"
                "Please use the correct format:\n"
                "/newRaw <job_title>;<location>;<job_type(s)>;<remote_type(s)>;<time_period>[;<filter_prompt>]\n\n"
                "Example: /newRaw Software Engineer;Germany;Full-time,Part-time;Remote,Hybrid;5 minutes;Senior level no German required\n\n"
                "Available values:\n"
                "- Job types: Full-time, Part-time, Contract, Temporary, Internship\n"
                "- Remote types: On-site, Remote, Hybrid\n"
                "- Time periods: 5 minutes, 15 minutes, 30 minutes, 1 hour, 4 hours, 24 hours\n"
                "- Filter prompt: Optional freeform text (max 300 chars) for LLM-based job filtering"
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error creating job search: {str(e)}\n\n"
                "Please use the correct format:\n"
                "/newRaw <job_title>;<location>;<job_type(s)>;<remote_type(s)>;<time_period>[;<filter_prompt>]\n\n"
                "Example: /newRaw Software Engineer;Germany;Full-time,Part-time;Remote,Hybrid;5 minutes;Senior level no German required\n\n"
                "Available values:\n"
                "- Job types: Full-time, Part-time, Contract, Temporary, Internship\n"
                "- Remote types: On-site, Remote, Hybrid\n"
                "- Time periods: 5 minutes, 15 minutes, 30 minutes, 1 hour, 4 hours, 24 hours\n"
                "- Filter prompt: Optional freeform text (max 300 chars) for LLM-based job filtering"
            )

    async def handle_one_time_search_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle confirmations for one-time deep search outside conversation flow."""
        if 'one_time_search_pending' not in context.user_data:
            return  # Not a one-time search confirmation
        
        input_text = update.message.text.strip().lower()
        if input_text == 'no':
            context.user_data.pop('one_time_search_pending', None)
            await update.message.reply_text("One-time deep search cancelled.")
            return
        
        if input_text == 'yes':
            job_search_data = context.user_data.pop('one_time_search_pending', None)
            if job_search_data:
                try:
                    # Execute one-time search
                    await self.job_search_manager.execute_one_time_search(job_search_data, update.effective_user.id)
                except Exception as e:
                    logger.error(f"Error executing one-time search: {e}")
                    await update.message.reply_text(
                        "Sorry, there was an error executing your deep search. Please try again."
                    )
                await update.message.reply_text("🔍 Starting deep search... This may take a moment. Except results within few minutes.")
            return
        
        # Invalid response
        await update.message.reply_text("Please type 'yes' to confirm or 'no' to cancel the deep search.")

    async def one_time_deep_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle one-time deep search command with required filter prompt."""
        # Clear any existing conversation state
        self._clear_conversation_state(context)
        
        try:
            raw_input = update.message.text.split('/oneTimeDeepSearch ')[1].strip()
            parts = raw_input.split(';')
            if len(parts) != 5:
                await update.message.reply_text(
                    "Invalid format. Please use:\n"
                    "/oneTimeDeepSearch <job_title>;<location>;<job_type>;<remote_type>;<filter_prompt>\n\n"
                    "Example: /oneTimeDeepSearch Python Developer;Switzerland;Full-time;Remote;Senior backend role no hybrid\n\n"
                    "Available values:\n"
                    "- Job types: Full-time, Part-time, Contract, Temporary, Internship\n"
                    "- Remote types: On-site, Remote, Hybrid\n"
                    "- Filter prompt: Required freeform text (max 300 chars) for LLM-based job filtering"
                )
                return
            
            title, location, job_type, remote_types, filter_text = parts
            
            # Validate filter text
            filter_text = filter_text.strip()
            if not filter_text:
                await update.message.reply_text(
                    "❌ Filter prompt is required for deep search."
                )
                return
            if len(filter_text) > 300:
                await update.message.reply_text(
                    "❌ Filter prompt is too long. Maximum 300 characters allowed."
                )
                return
            
            # Parse job parameters
            job_type_enums = self._parse_job_types(job_type)
            remote_type_enums = self._parse_remote_types(remote_types)
            
            # Create JobSearchIn for confirmation
            job_search_data = JobSearchIn(
                job_title=title.strip(),
                location=location.strip(),
                job_types=job_type_enums,
                remote_types=remote_type_enums,
                time_period=TimePeriod.parse("1 month"),  #TODO: parse it too from user
                user_id=update.effective_user.id,
                blacklist=[],
                filter_text=filter_text
            )
            
            # Show confirmation
            msg = (
                "🔍 One-time Deep Search Confirmation:\n\n"
                f"Job Title: {job_search_data.job_title}\n"
                f"Location: {job_search_data.location}\n"
                f"Job Types: {', '.join(jt.label for jt in job_search_data.job_types)}\n"
                f"Remote Types: {', '.join(rt.label for rt in job_search_data.remote_types)}\n"
                f"Filter Prompt: {job_search_data.filter_text}\n\n"
                "This will search immediately and return results. Confirm with 'yes' or cancel with 'no'."
            )
            await update.message.reply_text(msg)
            
            # Store search data for confirmation
            context.user_data['one_time_search_pending'] = job_search_data
            
        except ValueError as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}\n\n"
                "Please use the correct format:\n"
                "/oneTimeDeepSearch <job_title>;<location>;<job_type(s)>;<remote_type(s)>;<filter_prompt>\n\n"
                "Example: /oneTimeDeepSearch Python Developer;Switzerland;Full-time;Remote;No hybrid, no German required"
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}\n\n"
                "Please use the correct format:\n"
                "/oneTimeDeepSearch <job_title>;<location>;<job_type(s)>;<remote_type(s)>;<filter_prompt>"
                "Example: /oneTimeDeepSearch Python Developer;Switzerland;Full-time;Remote;No hybrid, no German required"
            ) 