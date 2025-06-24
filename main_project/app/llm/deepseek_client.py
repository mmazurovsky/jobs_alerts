"""
DeepSeek LLM client wrapper using LangChain.
"""
import logging
from typing import Optional, Dict, Any, List
import httpx
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.callbacks.base import BaseCallbackHandler

from main_project.app.core.config import config

logger = logging.getLogger(__name__)


class DeepSeekCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for DeepSeek API calls."""
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Log when LLM starts processing."""
        logger.info("DeepSeek LLM processing started")
    
    def on_llm_end(self, response, **kwargs) -> None:
        """Log when LLM finishes processing."""
        logger.info("DeepSeek LLM processing completed")
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Log LLM errors."""
        logger.error(f"DeepSeek LLM error: {error}")


class ChatDeepSeekClient:
    """Wrapper for DeepSeek LLM using LangChain ChatOpenAI interface."""
    
    def __init__(self, api_key: Optional[str] = None, temperature: float = 0.7, max_tokens: Optional[int] = None):
        """Initialize the DeepSeek client.
        
        Args:
            api_key: DeepSeek API key (defaults to config value)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key or config.deepseek_api_key
        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable.")
        
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize ChatOpenAI with DeepSeek endpoint
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=self.api_key,
            openai_api_base="https://api.deepseek.com/v1",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            callbacks=[DeepSeekCallbackHandler()]
        )
        
        logger.info(f"Initialized ChatDeepSeek client with temperature={temperature}")
    
    async def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """Send a chat completion request to DeepSeek.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            str: The assistant's response
        """
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                role = msg.get('role', '')
                content = msg.get('content', '')
                
                if role == 'system':
                    langchain_messages.append(SystemMessage(content=content))
                elif role == 'human' or role == 'user':
                    langchain_messages.append(HumanMessage(content=content))
                elif role == 'assistant':
                    langchain_messages.append(AIMessage(content=content))
                else:
                    logger.warning(f"Unknown message role: {role}, treating as human message")
                    langchain_messages.append(HumanMessage(content=content))
            
            # Call the LLM
            response = await self.llm.ainvoke(langchain_messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    async def simple_chat(self, prompt: str, system_message: Optional[str] = None) -> str:
        """Simple chat interface for single prompts.
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            
        Returns:
            str: The assistant's response
        """
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        return await self.chat_completion(messages)
    
    async def test_connection(self) -> bool:
        """Test the connection to DeepSeek API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            test_prompt = "Hello! Please respond with 'Connection successful' to confirm the API is working."
            response = await self.simple_chat(test_prompt)
            
            logger.info(f"DeepSeek API test response: {response}")
            return "connection successful" in response.lower() or len(response) > 0
            
        except Exception as e:
            logger.error(f"DeepSeek API connection test failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model configuration information.
        
        Returns:
            Dict: Model configuration details
        """
        return {
            "model": "deepseek-chat",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_base": "https://api.deepseek.com/v1",
            "has_api_key": bool(self.api_key)
        }


# Global instance for easy access
_deepseek_client: Optional[ChatDeepSeekClient] = None


def get_deepseek_client() -> ChatDeepSeekClient:
    """Get or create the global DeepSeek client instance.
    
    Returns:
        ChatDeepSeekClient: The global client instance
    """
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = ChatDeepSeekClient()
    return _deepseek_client


async def test_deepseek_connection() -> bool:
    """Test the DeepSeek API connection.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client = get_deepseek_client()
        return await client.test_connection()
    except Exception as e:
        logger.error(f"Failed to test DeepSeek connection: {e}")
        return False 