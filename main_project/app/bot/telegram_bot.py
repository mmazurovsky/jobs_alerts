"""
Refactored Telegram bot module with LLM agent integration.
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
        
        try:
            # Get dynamic content from tool registry if available
            if hasattr(self.llm_agent, 'tool_registry') and self.llm_agent.tool_registry:
                # Generate dynamic start message from tool capabilities
                start_message = self._generate_start_message(user.first_name)
            else:
                # Minimal fallback
                start_message = f"👋 Hi {user.first_name}! I'm your AI-powered job search assistant.\n\n" \
                               "🤖 Just talk to me naturally about what you want to do with job searches!\n\n" \
                               "📚 Use /help to see what I can help you with."
            
            await update.message.reply_text(start_message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            # Ultimate fallback
            await update.message.reply_text(
                f"👋 Hi {user.first_name}! I'm your job search assistant. Use /help to see what I can do!"
            )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send comprehensive help message with detailed guidance."""
        try:
            # Get dynamic help from tool registry with enhanced presentation
            if hasattr(self.llm_agent, 'tool_registry') and self.llm_agent.tool_registry:
                enhanced_help = """🤖 **AI Job Search Assistant - Complete Guide**

I'm your intelligent job search companion! I understand natural language and can help you with all aspects of job searching.

🎯 **How I Work:**
• **Natural Conversation**: Talk to me like you would a human assistant
• **Smart Understanding**: I interpret your intent from casual language  
• **Guided Process**: I'll ask for any missing information step-by-step
• **Confirmation Safety**: I always confirm before making changes
• **Memory**: I remember our conversation context

💬 **Communication Tips:**
• Be conversational: "I need help finding Python jobs"
• Ask questions: "What job searches do I have active?"
• Request help: "Help me create a new search"
• Give feedback: "That's not what I meant, let me clarify..."

📚 **Detailed Help:**
Say "help with [topic]" for specific guidance:
• "help with creating searches" - Learn about setting up job alerts
• "help with finding jobs" - Understand immediate job searching
• "help with managing searches" - Learn to view, edit, and delete alerts

🔧 **Troubleshooting:**
• If I misunderstand, just clarify: "No, I meant..."
• For complex requests, break them into smaller parts
• I'll guide you if you're missing required information

"""
                # Get tool-specific help
                tool_help = self.llm_agent.get_tool_help()
                full_help = enhanced_help + "\n" + tool_help
                
                # Add footer with more guidance
                full_help += """\n
💡 **Pro Tips:**
• I learn from context - reference previous messages
• I can handle typos and informal language
• Feel free to change your mind or ask follow-up questions
• Use /start to see the welcome message again

**Ready to start?** Just tell me what you want to do with job searching!"""
                
                await self._send_message_with_splitting(update.effective_user.id, full_help)
            else:
                # Enhanced fallback with more context
                fallback_help = self._generate_enhanced_fallback_help()
                await self._send_message_with_splitting(update.effective_user.id, fallback_help)
        except Exception as e:
            logger.error(f"Error showing help: {e}")
            # Generate minimal help without hardcoded tool descriptions
            fallback_help = self._generate_fallback_help()
            await update.message.reply_text(fallback_help, parse_mode=ParseMode.MARKDOWN)

    # Message handlers
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all non-command messages with LLM agent."""
        progress_message = None
        try:
            user_message = update.message.text
            user_id = update.effective_user.id
            
            # IMMEDIATE RESPONSE: Send instant acknowledgment
            await update.message.reply_chat_action("typing")
            progress_message = await update.message.reply_text("💭 Got it! Processing...")
            
            # FAST PATH: Check for simple, direct operations that don't need LLM
            fast_response = await self._try_fast_path(user_message, user_id)
            if fast_response:
                await progress_message.edit_text("✅ Ready!")
                await self._send_message_with_splitting(user_id, fast_response)
                return
            
            # Check for specific help requests first (quick path)
            if self._is_help_request(user_message):
                tool_name = self._extract_tool_name_from_help(user_message)
                if tool_name and hasattr(self.llm_agent, 'tool_registry') and self.llm_agent.tool_registry:
                    await progress_message.edit_text("📚 Getting help information...")
                    help_response = self.llm_agent.get_tool_help(tool_name)
                    await progress_message.edit_text("✅ Ready!")
                    await self._send_message_with_splitting(user_id, help_response)
                    return
            
            # Initialize LLM agent if not already done
            if not hasattr(self.llm_agent, 'agent_executor') or self.llm_agent.agent_executor is None:
                await progress_message.edit_text("🤖 Initializing AI assistant...")
                try:
                    await self.llm_agent.initialize()
                    await progress_message.edit_text("✅ AI ready! Thinking...")
                except Exception as init_error:
                    await progress_message.edit_text("❌ Failed to initialize AI assistant.")
                    raise init_error
            
            # Update progress and start processing
            await progress_message.edit_text("🧠 Thinking...")
            
            # Start periodic status updates
            status_task = asyncio.create_task(self._show_processing_status(progress_message))
            
            try:
                # Process with LLM agent
                response = await self.llm_agent.chat(user_id, user_message)
                
                # Cancel status updates
                status_task.cancel()
                
                # Quick final update
                await progress_message.edit_text("✅ Response ready!")
                
                # Send response immediately
                await self._send_message_with_splitting(user_id, response)
                
            except Exception as processing_error:
                status_task.cancel()
                await progress_message.edit_text("❌ Error processing request.")
                raise processing_error
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_response = self._generate_error_response(e, user_message)
            if progress_message:
                try:
                    await progress_message.edit_text(error_response)
                except:
                    await update.message.reply_text(error_response)
            else:
                await update.message.reply_text(error_response)

    async def _try_fast_path(self, message: str, user_id: int) -> Optional[str]:
        """Try to handle simple requests without LLM processing for speed.
        
        Returns:
            str: Fast response if handled, None if LLM processing needed
        """
        message_lower = message.lower().strip()
        
        # Simple greetings
        if message_lower in ['hi', 'hello', 'hey', 'start']:
            return ("👋 Hello! I'm your AI job search assistant.\n\n"
                   "I can help you:\n"
                   "• List your job searches\n" 
                   "• Create new searches\n"
                   "• Delete old searches\n"
                   "• Find jobs immediately\n\n"
                   "Just tell me what you'd like to do!")
        
        # Status/list requests
        if any(phrase in message_lower for phrase in ['show my searches', 'list searches', 'my searches', 'show searches']):
            try:
                searches = await self.job_search_manager.get_user_searches(user_id)
                if not searches:
                    return ("📋 **Your Job Searches**\n\n"
                           "You don't have any active job searches yet.\n\n"
                           "Would you like to create your first search? Just tell me what job you're looking for!")
                
                # Format searches quickly
                search_list = ["📋 **Your Active Job Searches:**\n"]
                for i, search in enumerate(searches, 1):
                    search_list.append(f"{i}. 🔍 {search.job_title} in {search.location}")
                
                search_list.append(f"\n💬 Total: {len(searches)} active searches")
                search_list.append("\nTo get details about a specific search, just ask: \"Show details for [job title]\"")
                
                return "\n".join(search_list)
            except Exception as e:
                logger.error(f"Error in fast path list: {e}")
                return None
        
        # Quick help
        if message_lower in ['help', '?', 'what can you do']:
            return ("🤖 **I'm your AI Job Search Assistant!**\n\n"
                   "**What I can do:**\n"
                   "• 📋 List your job searches\n"
                   "• ➕ Create new job search alerts\n" 
                   "• 🗑️ Delete unwanted searches\n"
                   "• 📊 Show details about specific searches\n"
                   "• 🔍 Find jobs immediately (one-time search)\n\n"
                   "**Just talk to me naturally!**\n"
                   "Examples:\n"
                   "• \"Show my searches\"\n"
                   "• \"Create a search for Python jobs in Berlin\"\n"
                   "• \"Find React developer jobs right now\"\n"
                   "• \"Delete my old marketing search\"\n\n"
                   "What would you like to do?")
        
        # Not a fast path case
        return None

    async def _show_processing_status(self, message: Message):
        """Show rotating processing status to keep user engaged."""
        statuses = [
            "🧠 Thinking...",
            "🔍 Analyzing your request...",
            "⚡ Processing...",
            "🤔 Working on it...",
            "🎯 Almost ready..."
        ]
        
        try:
            for i in range(30):  # Show status for up to 30 seconds
                status = statuses[i % len(statuses)]
                await message.edit_text(status)
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            # Normal cancellation when processing is done
            pass
        except Exception as e:
            logger.warning(f"Error updating status: {e}")

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
            # Generate examples from tools if available
            examples_text = self._get_command_examples()
            await update.message.reply_text(
                f"❌ I don't recognize the command `{update.message.text}`. "
                f"Please try describing what you want to do in natural language instead!\n\n{examples_text}"
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
    
    def _is_help_request(self, message: str) -> bool:
        """Check if message is a help request for a specific operation."""
        message_lower = message.lower()
        help_patterns = [
            "help with",
            "how to",
            "how do i",
            "what is",
            "explain",
            "show me how to",
            "guide me",
            "instructions for"
        ]
        return any(pattern in message_lower for pattern in help_patterns)
    
    def _extract_tool_name_from_help(self, message: str) -> Optional[str]:
        """Extract tool name from a help request message."""
        message_lower = message.lower()
        
        # Map common phrases to tool names
        tool_mappings = {
            "list": "list_job_searches",
            "listing": "list_job_searches", 
            "show": "list_job_searches",
            "display": "list_job_searches",
            "view": "list_job_searches",
            "create": "create_job_search",
            "creating": "create_job_search",
            "add": "create_job_search",
            "set up": "create_job_search",
            "setup": "create_job_search",
            "delete": "delete_job_search",
            "deleting": "delete_job_search", 
            "remove": "delete_job_search",
            "cancel": "delete_job_search",
            "details": "get_job_search_details",
            "detail": "get_job_search_details",
            "info": "get_job_search_details",
            "information": "get_job_search_details",
            "search": "one_time_search",
            "searching": "one_time_search",
            "find": "one_time_search",
            "one time": "one_time_search",
            "immediate": "one_time_search"
        }
        
        for phrase, tool_name in tool_mappings.items():
            if phrase in message_lower:
                return tool_name
        
        return None 

    def _generate_start_message(self, user_name: str) -> str:
        """Generate comprehensive welcoming start message using tool registry."""
        try:
            # Create a more welcoming and comprehensive onboarding message
            base_message = f"👋 **Welcome {user_name}!** I'm your AI-powered job search assistant.\n\n"
            
            # Explain AI capabilities clearly
            base_message += "🤖 **What makes me special:**\n" \
                           "• I understand **natural language** - just talk to me like a person!\n" \
                           "• I'll guide you through each step and ask for confirmation\n" \
                           "• I remember our conversation and provide contextual help\n" \
                           "• No need to learn complex commands - I speak human! 😊\n\n"
            
            # Get capabilities from tools with better formatting
            if hasattr(self.llm_agent, 'tool_registry') and self.llm_agent.tool_registry:
                base_message += "🎯 **What I can help you with:**\n"
                tools_summary = self._get_tools_summary()
                if tools_summary:
                    base_message += tools_summary
                
                # Add conversation examples with more context
                examples = self._get_tool_examples()
                if examples:
                    base_message += f"\n\n💬 **Try saying things like:**\n{examples}\n"
            
            # Add onboarding tips and next steps
            base_message += "\n\n✨ **Getting Started Tips:**\n" \
                           "• Ask me questions naturally: \"Can you show me my searches?\"\n" \
                           "• I'll ask for any missing information I need\n" \
                           "• Say \"help with [topic]\" for detailed guidance\n" \
                           "• I'll always confirm before making changes\n\n" \
                           "📚 Use /help anytime for detailed information.\n\n" \
                           "**Ready to get started?** What would you like to do with job searching today?"
            
            return base_message
            
        except Exception as e:
            logger.error(f"Error generating start message: {e}")
            # Enhanced fallback with onboarding context
            return f"👋 Welcome {user_name}! I'm your AI-powered job search assistant.\n\n" \
                   "🤖 **I understand natural language** - just talk to me normally!\n\n" \
                   "I can help you create job search alerts, find jobs immediately, manage your searches, and more.\n\n" \
                   "Just tell me what you want to do, like: \"I want to search for Python jobs in Berlin\"\n\n" \
                   "📚 Use /help to see what I can help you with. What would you like to do?"

    def _get_tools_summary(self) -> str:
        """Get a brief summary of all tool capabilities."""
        try:
            if not hasattr(self.llm_agent, 'tool_registry') or not self.llm_agent.tool_registry:
                return ""
            
            summaries = []
            for tool_name, tool in self.llm_agent.tool_registry.tools.items():
                doc = tool.get_documentation()
                if doc and doc.purpose:
                    # Create a bullet point from the purpose
                    purpose = doc.purpose.strip()
                    if not purpose.startswith('•'):
                        purpose = f"• {purpose}"
                    summaries.append(purpose)
            
            return "\n".join(summaries) if summaries else ""
            
        except Exception as e:
            logger.error(f"Error getting tools summary: {e}")
            return ""

    def _get_tool_examples(self) -> str:
        """Get examples from all tools."""
        try:
            if not hasattr(self.llm_agent, 'tool_registry') or not self.llm_agent.tool_registry:
                return ""
            
            all_examples = []
            for tool_name, tool in self.llm_agent.tool_registry.tools.items():
                doc = tool.get_documentation()
                if doc and doc.examples:
                    # Take first 2 examples from each tool
                    for example in doc.examples[:2]:
                        all_examples.append(f"- \"{example}\"")
            
            return "\n".join(all_examples) if all_examples else ""
            
        except Exception as e:
            logger.error(f"Error getting tool examples: {e}")
            return ""

    def _generate_enhanced_fallback_help(self) -> str:
        """Generate enhanced fallback help with comprehensive guidance."""
        return """🤖 **AI Job Search Assistant - Guide**

I'm your intelligent job search companion! I understand natural language and can help you with job searching.

🎯 **How I Work:**
• **Natural Conversation**: Talk to me like you would a human assistant
• **Smart Understanding**: I interpret your intent from casual language  
• **Guided Process**: I'll ask for any missing information step-by-step
• **Confirmation Safety**: I always confirm before making changes

💬 **What You Can Say:**
• "Show me my job searches"
• "Create a new search for Python developer jobs in Berlin"
• "Find React developer jobs for me now"
• "Delete my old job alert"
• "Help me set up a new search"

📚 **Getting Help:**
• Say "help with [topic]" for specific guidance
• I'll guide you through each process step-by-step
• Just ask naturally: "How do I create a search?"

💡 **Tips:**
• Be conversational and natural
• I can handle typos and informal language
• Feel free to ask follow-up questions
• I'll remember our conversation context

**Ready to start?** Just tell me what you want to do with job searching!"""

    def _generate_fallback_help(self) -> str:
        """Generate minimal fallback help without hardcoded tool descriptions."""
        return """🤖 **AI Job Search Assistant**

I'm your natural language job search assistant! Just talk to me like you would talk to a person.

I understand natural language, so you don't need to use specific commands. Just tell me what you want to do!

For example, you can say things like:
- "Show me my searches"
- "Create a new job alert"
- "Find jobs for me now"

Use /help for more detailed assistance."""

    def _get_command_examples(self) -> str:
        """Get examples for unknown command responses."""
        try:
            if hasattr(self.llm_agent, 'tool_registry') and self.llm_agent.tool_registry:
                examples = self._get_tool_examples()
                if examples:
                    return f"**For example:**\n{examples}"
            
            # Minimal fallback examples
            return """**For example:**
- "Show me my searches"
- "Create a new search for Python jobs"
- "Find jobs for me now\""""
            
        except Exception as e:
            logger.error(f"Error getting command examples: {e}")
            return """**For example:**
- "Show me my searches"
- "Create a new job alert"
- "Find jobs for me now\""""

    def _generate_error_response(self, error: Exception, user_message: str) -> str:
        """Generate contextual error response based on the error and user message."""
        error_str = str(error).lower()
        
        # Categorize errors and provide helpful responses
        if "api" in error_str or "connection" in error_str:
            return """❌ **Connection Issue**

I'm having trouble connecting to my AI service. This is usually temporary.

**What you can do:**
• Try your request again in a moment
• Check if the message is clear and specific
• Use /help to see what I can assist with

Please try again in a few seconds!"""
        
        elif "timeout" in error_str:
            return """⏱️ **Processing Timeout**

Your request took too long to process. This can happen with complex queries.

**What you can do:**
• Try breaking your request into smaller parts
• Be more specific about what you want
• Try again - the system may be busy

Please try a simpler version of your request!"""
        
        elif "invalid" in error_str or "validation" in error_str:
            return f"""❌ **Input Validation Issue**

There seems to be an issue with your request: "{user_message[:100]}..."

**What you can do:**
• Check if you've provided all required information
• Make sure job titles and locations are specific
• Use /help to see examples of valid requests

Would you like to try rephrasing your request?"""
        
        elif "not found" in error_str:
            return """🔍 **Not Found**

I couldn't find what you're looking for.

**What you can do:**
• Use "list my searches" to see your existing job alerts
• Check if the search ID or details are correct
• Try a different way to describe what you want

Need help finding something specific?"""
        
        else:
            return f"""❌ **Oops! Something went wrong**

I encountered an unexpected issue while processing your request.

**What you can do:**
• Try rephrasing your request differently
• Use simpler language or break down complex requests  
• Use /help to see examples of what I can do
• Try again in a moment

Your request: "{user_message[:100]}{"..." if len(user_message) > 100 else ""}"

I'm here to help when you're ready to try again! 🤖"""