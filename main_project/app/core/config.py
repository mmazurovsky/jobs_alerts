"""
Simple configuration management for Jobs Alerts.
"""
import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Simple configuration class that loads from environment variables.
    
    This is a singleton class - only one instance will be created and shared across the application.
    """
    
    def __init__(self):
        # Load .env from main_project directory before accessing environment variables
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env'))
        load_dotenv(dotenv_path=env_path)
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

# Create a singleton instance
config = Config() 