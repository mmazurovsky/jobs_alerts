"""
Simple configuration management for Jobs Alerts.
"""
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class Config:
    """Simple configuration class that loads from environment variables.
    
    This is a singleton class - only one instance will be created and shared across the application.
    """
    
    def __init__(self):
        # Optionally, print debug info
        # print(f"DEBUG: Loaded .env from {env_path}")
        # print(f"DEBUG: MONGO_URL = {os.getenv('MONGO_URL')}")
        
        # Environment variables are assumed to be loaded by main.py
        
        # Telegram bot settings
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        else:
            logger.info("Loaded TELEGRAM_BOT_TOKEN")
        
        # MongoDB settings
        self.mongo_uri = os.getenv('MONGO_URL')
        if not self.mongo_uri:
            logger.error('MONGO_URL not found in environment variables')
            raise RuntimeError('MONGO_URL not set in environment')
        
        # DeepSeek API settings for LLM integration
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.deepseek_api_key:
            logger.warning("DEEPSEEK_API_KEY not found in environment variables - LLM features will be disabled")
        else:
            logger.info("Loaded DEEPSEEK_API_KEY")
        
        # Log the configuration (safely)
        self._log_config()
    
    def validate(self) -> bool:
        """Validate the configuration.
        
        Returns:
            bool: True if the configuration is valid, False otherwise.
        """
            
        if not self.telegram_bot_token:
            logger.error("Telegram bot token is not configured")
            return False
            
        return True
    
    def _log_config(self):
        """Log the current configuration, masking sensitive values."""
        logger.info("Current configuration:")
        logger.info(f"  - Telegram Bot Token: {'***' if self.telegram_bot_token else 'NOT SET'}")
        logger.info(f"  - MongoDB URI: {'***' if self.mongo_uri else 'NOT SET'}")
        logger.info(f"  - DeepSeek API Key: {'***' if self.deepseek_api_key else 'NOT SET'}")

# Create a singleton instance
config = Config() 