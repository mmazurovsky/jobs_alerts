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
        # Get the absolute path to the .env file in the project root
        # This assumes the project structure is:
        # /project_root/
        #   ├── .env
        #   ├── src/
        #   │   ├── core/
        #   │   │   ├── config.py
        #   │   │   └── ...
        #   │   └── ...
        #   └── ...
        project_root = Path(__file__).resolve().parent.parent.parent
        env_path = project_root / '.env'
        
        logger.info(f"Looking for .env file at: {env_path}")
        
        if not env_path.exists():
            logger.warning(f".env file not found at {env_path}, proceeding with environment variables only.")
        else:
            logger.info(f"Loading .env file from: {env_path}")
            load_dotenv(env_path, override=True)
            
        # LinkedIn credentials
        self.linkedin_email = os.getenv('LINKEDIN_EMAIL')
        if not self.linkedin_email:
            logger.error(f"LINKEDIN_EMAIL not found in environment variables")
            exit()
        else:
            logger.info(f"Loaded LINKEDIN_EMAIL: {self.linkedin_email}")
            
        self.linkedin_password = os.getenv('LINKEDIN_PASSWORD')
        if not self.linkedin_password:
            logger.error("LINKEDIN_PASSWORD not found in environment variables")
        else:
            logger.info("Loaded LINKEDIN_PASSWORD: [MASKED]")
        
        # Scraping settings
        self.max_jobs_per_search = int(os.getenv('MAX_JOBS_PER_SEARCH', '100'))
        self.search_interval_minutes = int(os.getenv('SEARCH_INTERVAL_MINUTES', '60'))
        self.save_path = Path(os.getenv('SAVE_PATH', './data/jobs'))
        
        # Notification settings
        self.enable_notifications = os.getenv('ENABLE_NOTIFICATIONS', 'false').lower() == 'true'
        self.notification_email = os.getenv('NOTIFICATION_EMAIL')
        
        # Telegram bot settings
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        else:
            logger.info("Loaded TELEGRAM_BOT_TOKEN")
        
        # Create save directory
        self.save_path.mkdir(parents=True, exist_ok=True)
        
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
        if not self.linkedin_email or not self.linkedin_password:
            logger.error("LinkedIn credentials are not configured")
            return False
            
        if not self.telegram_bot_token:
            logger.error("Telegram bot token is not configured")
            return False
            
        return True
    
    def _log_config(self):
        """Log the current configuration, masking sensitive values."""
        logger.info("Current configuration:")
        logger.info(f"LinkedIn Email: {self.linkedin_email}")
        logger.info(f"Max Jobs Per Search: {self.max_jobs_per_search}")
        logger.info(f"Search Interval: {self.search_interval_minutes} minutes")
        logger.info(f"Save Path: {self.save_path}")
        logger.info(f"Notifications Enabled: {self.enable_notifications}")
        if self.enable_notifications:
            logger.info(f"Notification Email: {self.notification_email}")

# Create a singleton instance
config = Config() 