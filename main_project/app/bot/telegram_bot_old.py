"""
Telegram bot module with LLM agent integration.
"""
import logging
import os
from typing import Dict, List, Optional
from telegram import Update, Message
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode
from datetime import datetime
import asyncio

from shared.data import (
    JobListing, StreamType, StreamEvent, StreamManager
)
from main_project.app.core.job_search_manager import JobSearchManager
from main_project.app.llm.job_search_agent import JobSearchAgent

logger = logging.getLogger(__name__)

try:
    ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
except (TypeError, ValueError):
    raise RuntimeError("ADMIN_USER_ID environment variable must be set and be an integer.")

class TelegramBot:
    """Telegram bot for managing job searches with LLM agent."""
    
    def __init__(self, token: str, stream_manager: StreamManager, job_search_manager: JobSearchManager):
        """Initialize the bot with token and MongoDB manager."""
        self.token = token
        self.stream_manager = stream_manager
        self.job_search_manager = job_search_manager
        self.application = Application.builder().token(token).build()
        
        # Initialize LLM agent
        self.llm_agent = JobSearchAgent(job_search_manager)
        
        self._setup_handlers()

        # Subscribe to send message stream
        self.stream_manager.get_stream(StreamType.SEND_MESSAGE).subscribe(
            lambda event: asyncio.create_task(self._handle_send_message(event))
        )
        self.stream_manager.get_stream(StreamType.SEND_LOG).subscribe(
            lambda event: asyncio.create_task(self._handle_send_log(event))
        )
    
    def _setup_handlers(self):
        """Set up all command and message handlers."""
        # Basic command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        
        # Handle all non-command messages with LLM agent
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Handle unknown commands by redirecting to LLM
        self.application.add_handler(
            MessageHandler(filters.COMMAND, self.handle_unknown_command)
        )
    
    # Basic command handlers
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hi {user.first_name}! I'm your AI-powered job search assistant.\n\n"
            "🤖 **Just talk to me naturally!** I can help you:\n"
            "• Create new job search alerts\n"
            "• List your existing searches\n"
            "• Delete unwanted searches\n"
            "• Get details about specific searches\n"
            "• Perform one-time job searches\n\n"
            "💬 **Examples of what you can say:**\n"
            "- \"Show me my job searches\"\n"
            "- \"Create a search for Python jobs in Berlin\"\n"
            "- \"Delete my old marketing search\"\n"
            "- \"Find remote React developer positions\"\n\n"
            "📚 Use /help to see more information.\n\n"
            "What would you like to do?",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        try:
            # Get help from LLM agent
            help_text = self.llm_agent.get_available_commands_help()
            await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error showing help: {e}")
            fallback_help = """🤖 **AI Job Search Assistant**

I'm your natural language job search assistant! Just talk to me like you would talk to a person.

**What I can help you with:**

🔍 **View Your Searches**
- "Show me my job searches"
- "What searches do I have?"
- "List my alerts"

➕ **Create New Searches** 
- "I want to create a job search for Python developer jobs in Berlin"
- "Set up alerts for remote data scientist positions"
- "Create a search for full-time React jobs"

🗑️ **Delete Searches**
- "Delete my search for marketing jobs"
- "Remove search abc123"
- "Cancel the alert for data analyst positions"

📋 **Get Search Details**
- "Show me details for search abc123"
- "Tell me about my Python developer search"

🔎 **One-Time Searches**
- "Search for JavaScript jobs in London right now"
- "Find me available remote Python positions"
- "Show me current data science jobs"

**I understand natural language**, so you don't need to use specific commands. Just tell me what you want to do!

**Note:** I'll always ask for confirmation before creating, updating, or deleting anything."""
            await update.message.reply_text(fallback_help, parse_mode=ParseMode.MARKDOWN)

    # Message handlers
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all non-command messages with LLM agent."""
        try:
            user_message = update.message.text
            user_id = update.effective_user.id
            
            # Show typing indicator
            await update.message.reply_chat_action("typing")
            
            # Initialize LLM agent if not already done
            if not hasattr(self.llm_agent, 'agent_executor') or self.llm_agent.agent_executor is None:
                await update.message.reply_text("🤖 Initializing AI assistant... Please wait a moment.")
                await self.llm_agent.initialize()
            
            # Process with LLM agent
            response = await self.llm_agent.chat(user_id, user_message)
            
            # Send response
            await self._send_message_with_splitting(user_id, response)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(
                "❌ Sorry, I encountered an error processing your request. "
                "Please try rephrasing or try again in a moment."
            )

    async def handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle unknown commands by redirecting to LLM agent."""
        try:
            command = update.message.text
            user_id = update.effective_user.id
            
            # Show typing indicator
            await update.message.reply_chat_action("typing")
            
            # Convert command to natural language and process with LLM
            natural_message = f"I tried to use the command: {command}. Can you help me with what I'm trying to do?"
            
            # Initialize LLM agent if not already done
            if not hasattr(self.llm_agent, 'agent_executor') or self.llm_agent.agent_executor is None:
                await update.message.reply_text("🤖 Initializing AI assistant... Please wait a moment.")
                await self.llm_agent.initialize()
            
            # Process with LLM agent
            response = await self.llm_agent.chat(user_id, natural_message)
            
            # Send response with a note about natural language
            intro_message = f"ℹ️ I don't recognize the command `{command}`, but I can help you with natural language!\n\n"
            full_response = intro_message + response
            
            await self._send_message_with_splitting(user_id, full_response)
            
        except Exception as e:
            logger.error(f"Error handling unknown command: {e}")
            await update.message.reply_text(
                f"❌ I don't recognize the command `{update.message.text}`. "
                "Please try describing what you want to do in natural language instead!\n\n"
                "For example: \"Show me my job searches\" or \"Create a new search for Python jobs\""
            )
    
    # Bot lifecycle methods
    def run(self):
        """Run the bot."""
        self.application.run_polling()
    
    async def initialize(self) -> None:
        """Initialize the bot."""
        try:
            await self.application.initialize()
            await self.application.start()
            # Initialize LLM agent in background (don't wait for it)
            asyncio.create_task(self._initialize_llm_agent())
            await self.application.updater.start_polling()
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            raise
    
    async def _initialize_llm_agent(self) -> None:
        """Initialize the LLM agent in background."""
        try:
            await self.llm_agent.initialize()
            logger.info("LLM agent initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM agent: {e}")
            # Don't raise - bot should still work without LLM
            
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

    # Job notification methods (preserved for system notifications)
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

    # Stream event handlers (preserved for system notifications)
    async def _handle_send_log(self, event: StreamEvent) -> None:
        """Handle log messages to admin."""
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
        """Handle message sending requests from other components."""
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
                # Check if message is too long and split if needed
                await self._send_message_with_splitting(user_id, message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    # Message utilities (preserved for response handling)
    async def _send_message_with_splitting(self, user_id: int, message: str):
        """Send a message with automatic splitting if it's too long."""
        try:
            # Telegram's message length limit is 4096 characters
            if len(message) <= 4096:
                # Send message as-is if it's within the limit
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Split the message into multiple parts
                await self._send_long_message_in_parts(user_id, message)
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
    
    async def _send_long_message_in_parts(self, user_id: int, message: str):
        """Split a long message into multiple parts and send them."""
        lines = message.split('\n')
        current_message = ""
        part_number = 1
        
        for line in lines:
            # Check if adding this line would exceed the limit
            test_message = current_message + line + '\n'
            
            if len(test_message) > 4096:
                # Send current message if it's not empty
                if current_message.strip():
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=current_message.rstrip(),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    part_number += 1
                
                # Start new message with current line, add part indicator for subsequent parts
                if part_number > 1:
                    header = f"📄 Part {part_number}:\n\n"
                    current_message = header + line + '\n'
                    
                    # If even with header it's too long, truncate the line
                    if len(current_message) > 4096:
                        max_line_length = 4096 - len(header) - 1  # -1 for newline
                        truncated_line = line[:max_line_length - 3] + "..."
                        current_message = header + truncated_line + '\n'
                else:
                    current_message = line + '\n'
                    
                    # If even a single line is too long, truncate it
                    if len(current_message) > 4096:
                        truncated_line = line[:4090] + "..."
                        current_message = truncated_line + '\n'
            else:
                current_message = test_message
        
        # Send the last part if it's not empty
        if current_message.strip():
            await self.application.bot.send_message(
                chat_id=user_id,
                text=current_message.rstrip(),
                parse_mode=ParseMode.MARKDOWN
            )  