"""
LangChain Agent for job search operations via natural language.
"""
import logging
from typing import Optional, Dict, Any, List
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import BaseMessage
import time
from dataclasses import dataclass

from main_project.app.llm.deepseek_client import ChatDeepSeekClient
from main_project.app.llm.tools import (
    ListJobSearchesTool,
    CreateJobSearchTool,
    DeleteJobSearchTool,
    GetJobSearchDetailsTool,
    OneTimeSearchTool
)
from main_project.app.llm.tools.tool_registry import create_tool_registry
from main_project.app.core.job_search_manager import JobSearchManager

logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    """Rate limiting data for a user."""
    requests: List[float]  # Timestamps of recent requests
    max_requests_per_minute: int = 10
    max_requests_per_hour: int = 50

class JobSearchAgent:
    """LangChain agent for natural language job search operations."""
    
    def __init__(self, job_search_manager: JobSearchManager):
        """Initialize the JobSearchAgent.
        
        Args:
            job_search_manager: Instance of JobSearchManager for data operations
        """
        self.job_search_manager = job_search_manager
        self.llm_client = None
        self.llm = None
        self.tools = None
        self.tool_registry = None
        self.agent_executor = None
        self.user_sessions: Dict[int, Dict] = {}
        self.rate_limits: Dict[int, RateLimit] = {}  # Rate limiting per user
        logger.info("JobSearchAgent created, ready for initialization")
        
    async def initialize(self):
        """Initialize the agent with LLM and tools."""
        try:
            # Initialize DeepSeek client
            self.llm = ChatDeepSeekClient()
            
            # Test connection
            if not await self.llm.test_connection():
                raise Exception("Failed to connect to DeepSeek API")
            
            # Initialize tools and registry
            self.tools = [
                ListJobSearchesTool(self.job_search_manager),
                CreateJobSearchTool(self.job_search_manager),
                DeleteJobSearchTool(self.job_search_manager),
                GetJobSearchDetailsTool(self.job_search_manager),
                OneTimeSearchTool(self.job_search_manager)
            ]
            
            # Create tool registry for documentation access
            self.tool_registry = create_tool_registry(self.job_search_manager)
            
            # Create system prompt
            system_prompt = self._create_system_prompt()
            
            # Create agent
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            # Create OpenAI tools agent (compatible with DeepSeek)
            agent = create_openai_tools_agent(
                llm=self.llm.llm,  # Use the LangChain ChatOpenAI instance
                tools=self.tools,
                prompt=prompt
            )
            
            # Create agent executor
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                max_iterations=3,
                early_stopping_method="generate"
            )
            
            logger.info("JobSearchAgent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize JobSearchAgent: {e}")
            raise
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        return """You are a specialized job search assistant for this application only. Your sole purpose is helping users manage their job search alerts.

**🔒 SECURITY & SCOPE RESTRICTIONS:**

**STRICT BOUNDARIES - YOU MUST ONLY:**
1. Help with job search management (create, list, delete, search)
2. Answer questions about job search features and functionality
3. Provide guidance on using this job search system
4. Discuss job search best practices related to this app

**❌ YOU MUST NEVER:**
- Answer general questions unrelated to job searching
- Provide programming help, coding advice, or technical tutorials
- Discuss politics, personal topics, or current events
- Help with homework, writing, or other non-job-search tasks
- Access or discuss user data beyond their own job searches
- Provide information about other users or system internals
- Explain how the AI system works or discuss AI topics
- Act as a general chatbot or assistant for non-job-search matters

**🛡️ UNAUTHORIZED ACCESS PREVENTION:**
- Users can ONLY access their own job searches (user_id is automatically enforced)
- Never reveal system information, API keys, or internal processes
- If asked about system architecture, redirect to job search functionality
- Users cannot access admin functions or other users' data

**💬 COMMUNICATION STYLE:**
- Be concise and direct - avoid lengthy explanations
- Focus responses specifically on job search functionality
- Use bullet points and clear formatting for readability
- Keep responses under 200 words unless detailed confirmation is needed
- If user asks off-topic questions, politely redirect to job search topics

**🎯 SCOPE ENFORCEMENT:**
If users ask about non-job-search topics, respond with:
"I'm a specialized job search assistant. I can only help with creating, managing, and finding job search alerts. How can I help you with your job search today?"

**YOUR CORE CAPABILITIES:**

1. **List job searches** - Show users their existing job search alerts
2. **Create job searches** - Set up new recurring job alerts 
3. **Delete job searches** - Remove unwanted job alerts
4. **Get search details** - Show detailed information about specific searches
5. **One-time searches** - Execute immediate job searches without creating alerts

**CRITICAL: CONFIRMATION WORKFLOW**

**ALWAYS ask for confirmation before executing any tool** that creates, deletes, or modifies data. Use this structured confirmation process:

**For CREATE operations:**
1. Collect all necessary information first
2. Present a clear summary in this format:
   ```
   📋 **Job Search Summary**
   • **Job Title:** [what they're looking for]
   • **Location:** [where they want to work]
   • **Job Types:** [employment types or "All types"]
   • **Remote Options:** [remote preferences or "All arrangements"]
   • **Check Frequency:** [how often to search]
   • **Additional Filters:** [any special requirements]
   
   ✅ **Should I create this job search alert?** (Reply 'yes' to confirm or 'no' to cancel)
   ```
3. Wait for explicit user confirmation ("yes", "confirm", "do it", etc.)
4. Only then execute the tool

**For DELETE operations:**
1. First show what they want to delete:
   ```
   🗑️ **Deletion Confirmation**
   You want to delete: [search details]
   
   ⚠️ **This cannot be undone.** Are you sure? (Reply 'yes' to confirm or 'no' to cancel)
   ```
2. Wait for explicit confirmation
3. Only then execute the deletion

**For ONE-TIME SEARCH operations:**
Present a summary:
```
🔍 **Immediate Job Search**
I'll search for: [job details]
Location: [location]
Filters: [any filters]

This will show immediate results without creating an ongoing alert.
**Should I proceed?** (Reply 'yes' to confirm)
```

**Information Gathering Guidelines:**

**Required for creating searches:**
- job_title (what kind of job)
- location (where to search - REQUIRED, cannot be empty)
- user_id (automatically provided)

**Optional for creating searches:**
- job_types: full_time, part_time, contract, temporary, internship
- remote_types: remote, hybrid, on_site  
- time_period: 1 hour, 3 hours, 6 hours, 12 hours, 1 day, 3 days, 1 week, 1 month
- filter_text: negative filters like "No entry level, No Spanish required"
- blacklist: companies to exclude

**Conversation Flow:**
1. Understand user intent (job search related only)
2. If off-topic, redirect politely to job search functionality
3. Gather required information (ask for missing details)
4. Suggest sensible defaults for optional parameters
5. **Present concise confirmation summary**
6. Wait for approval
7. Execute tool
8. Provide brief success/failure feedback with next steps

**Remember: Stay focused, be concise, maintain security, and ALWAYS confirm before taking action.**"""

    async def chat(self, user_id: int, message: str) -> str:
        """Process a chat message from a user.
        
        Args:
            user_id: Telegram user ID
            message: User's message
            
        Returns:
            Agent's response
        """
        try:
            logger.info(f"Processing message from user {user_id}: {message}")
            
            # Rate limiting check
            if not self._check_rate_limit(user_id):
                return """⚠️ **Rate Limit Exceeded**

You're sending requests too quickly. Please wait a moment before trying again.

**Limits:**
• Maximum 10 requests per minute
• Maximum 50 requests per hour

This helps ensure the service remains responsive for all users."""
            
            # Security check: Filter obviously off-topic requests
            if self._is_off_topic_request(message):
                return self._get_redirect_response()
            
            # Ensure agent is initialized
            if not self.agent_executor:
                await self.initialize()
            
            # Get or create user session
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = {
                    "pending_action": None,
                    "pending_data": None,
                    "conversation_history": []
                }
            
            session = self.user_sessions[user_id]
            
            # Add user_id context to the message
            contextualized_message = f"[User ID: {user_id}] {message}"
            
            # Process with agent
            response = await self.agent_executor.ainvoke({
                "input": contextualized_message,
                "chat_history": session.get("conversation_history", [])
            })
            
            # Extract the response
            agent_response = response.get("output", "I'm sorry, I couldn't process that request.")
            
            # Security check: Ensure response stays on topic
            if self._response_contains_off_topic_content(agent_response):
                logger.warning(f"Detected off-topic response for user {user_id}, redirecting")
                agent_response = self._get_redirect_response()
            
            # Update conversation history
            session["conversation_history"].append(HumanMessage(content=message))
            session["conversation_history"].append(AIMessage(content=agent_response))
            
            # Keep only last 20 messages to prevent memory overflow
            if len(session["conversation_history"]) > 20:
                session["conversation_history"] = session["conversation_history"][-20:]
            
            logger.info(f"Generated response for user {user_id}")
            return agent_response
            
        except Exception as e:
            logger.error(f"Error processing chat for user {user_id}: {e}")
            return """❌ I'm sorry, I encountered an error while processing your request. 

This could be due to:
- Temporary system issues
- API connectivity problems
- Invalid request format

Please try again, or contact support if the problem persists. You can also use the traditional bot commands as a fallback."""
    
    def _is_off_topic_request(self, message: str) -> bool:
        """Check if a message is clearly off-topic and should be blocked."""
        message_lower = message.lower().strip()
        
        # Keywords that indicate off-topic requests (be more specific to avoid false positives)
        off_topic_keywords = [
            # Programming/technical help (but avoid job-related terms)
            'debug this', 'programming language', 'write code', 'coding help', 'syntax error',
            'variable assignment', 'algorithm implementation', 'database design', 'api documentation',
            
            # General assistance
            'weather', 'news', 'politics', 'sports', 'recipes', 'homework', 'essay',
            'translate', 'math problem', 'calculation', 'convert units', 'history facts',
            
            # Personal/entertainment
            'tell me a joke', 'write a story', 'write a poem', 'sing a song', 'movie recommendation',
            'book recommendation', 'game recommendation', 'relationship advice',
            
            # Philosophical/general questions
            'meaning of life', 'explain quantum', 'theory of relativity'
        ]
        
        # Common off-topic phrases (more specific)
        off_topic_phrases = [
            'write a poem', 'write a story', 'can you write code', 'solve this math',
            'what do you think about politics', 'how to code in', 'explain how the universe',
            'what is the capital of', 'who is the president', 'when did world war',
            'why does the sun', 'how does gravity work', 'what ai model are you',
            'how do you work', 'who created you', 'are you chatgpt'
        ]
        
        # Simple word matching for some phrases
        simple_off_topic_checks = [
            ('how do you work', 'how do you work'),
            ('what ai model', 'what ai model are you'),
            ('who created you', 'who created you'),
            ('are you chatgpt', 'are you chatgpt')
        ]
        
        # Check for off-topic keywords
        for keyword in off_topic_keywords:
            if keyword in message_lower:
                return True
        
        # Check for off-topic phrases
        for phrase in off_topic_phrases:
            if phrase in message_lower:
                return True
        
        # Check simple off-topic patterns
        for pattern, _ in simple_off_topic_checks:
            if pattern in message_lower:
                return True
        
        return False
    
    def _response_contains_off_topic_content(self, response: str) -> bool:
        """Check if a response contains off-topic content that should be filtered."""
        response_lower = response.lower()
        
        # Red flags in responses that suggest off-topic content
        off_topic_indicators = [
            'i can help you with programming',
            'here\'s how to code',
            'the weather is',
            'in politics',
            'here\'s a joke',
            'i can assist with homework',
            'here\'s the recipe',
            'let me explain quantum',
            'as an ai model'
        ]
        
        return any(indicator in response_lower for indicator in off_topic_indicators)
    
    def _get_redirect_response(self) -> str:
        """Get the standard redirect response for off-topic requests."""
        return """🎯 **I'm a specialized job search assistant**

I can only help with creating, managing, and finding job search alerts. 

**What I can help you with:**
• Create new job search alerts
• Show your existing searches  
• Delete unwanted alerts
• Find jobs immediately
• Get details about your searches

**How can I help you with your job search today?** 🔍"""
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits."""
        current_time = time.time()
        
        # Initialize rate limit for new users
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = RateLimit(requests=[])
        
        rate_limit = self.rate_limits[user_id]
        
        # Clean old requests (older than 1 hour)
        rate_limit.requests = [req_time for req_time in rate_limit.requests 
                               if current_time - req_time < 3600]
        
        # Check minute limit (last 60 seconds)
        recent_requests = [req_time for req_time in rate_limit.requests 
                          if current_time - req_time < 60]
        
        if len(recent_requests) >= rate_limit.max_requests_per_minute:
            logger.warning(f"User {user_id} exceeded minute rate limit")
            return False
        
        # Check hour limit
        if len(rate_limit.requests) >= rate_limit.max_requests_per_hour:
            logger.warning(f"User {user_id} exceeded hour rate limit")
            return False
        
        # Add current request
        rate_limit.requests.append(current_time)
        return True
    
    async def reset_conversation(self, user_id: int):
        """Reset conversation history for a user.
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.user_sessions:
            self.user_sessions[user_id]["conversation_history"] = []
            logger.info(f"Reset conversation history for user {user_id}")
    
    def get_tool_help(self, tool_name: Optional[str] = None) -> str:
        """Get help for tools.
        
        Args:
            tool_name: Specific tool name, or None for all tools
            
        Returns:
            Formatted help text
        """
        if not self.tool_registry:
            return "Tool registry not initialized. Please try again."
        
        if tool_name:
            help_text = self.tool_registry.get_tool_help(tool_name)
            if help_text:
                return help_text
            else:
                return f"No help found for tool '{tool_name}'. Available tools: {list(self.tool_registry.tools.keys())}"
        else:
            return self.tool_registry.get_all_tools_help()
    
    def get_available_commands_help(self) -> str:
        """Get help text explaining what the agent can do."""
        return """🤖 **Natural Language Job Search Assistant**

I can help you manage your job searches using natural language! Just talk to me like you would talk to a person.

**What I can help you with:**

🔍 **View Your Searches**
- "Show me my job searches"
- "What searches do I have?"
- "List my alerts"

➕ **Create New Searches** 
- "I want to create a job search for Python developer jobs in Berlin"
- "Set up alerts for remote data scientist positions"
- "Create a search for full-time React jobs"

️ **Delete Searches**
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

**Note:** I'll always ask for confirmation before creating, updating, or deleting anything to make sure I understand correctly."""
    
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status information.
        
        Returns:
            Status dictionary with agent information
        """
        return {
            "initialized": self.agent_executor is not None,
            "llm_connected": self.llm is not None and await self.llm.test_connection() if self.llm else False,
            "tools_count": len(self.tools),
            "active_sessions": len(self.user_sessions),
            "model_info": self.llm.get_model_info() if self.llm else None
        } 