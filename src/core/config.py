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
    """Simple configuration class that loads from environment variables."""
    
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
            logger.error(f"No .env file found at {env_path}")
        else:
            logger.info(f"Loading .env file from: {env_path}")
            # Force reload the .env file from the specified path
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
        
        # AgentQL settings
        self.agentql_api_key = os.getenv('AGENTQL_API_KEY')
        if not self.agentql_api_key:
            logger.error("AGENTQL_API_KEY not found in environment variables")
        else:
            logger.info(f"Loaded AGENTQL_API_KEY: {self.agentql_api_key[:5]}...")
        
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
            logger.warning("TELEGRAM_BOT_TOKEN not found in environment variables")
        else:
            logger.info("Loaded TELEGRAM_BOT_TOKEN")
        
        # Create save directory
        self.save_path.mkdir(parents=True, exist_ok=True)
        
        # Log the configuration (safely)
        self._log_config()
    
    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.linkedin_email or not self.linkedin_password:
            logger.error("LinkedIn credentials are not configured")
            return False
        if not self.agentql_api_key:
            logger.error("AgentQL API key is not configured")
            return False
        return True
    
    def _log_config(self):
        """Log the current configuration, masking sensitive values."""
        logger.info("Current configuration:")
        logger.info(f"LinkedIn Email: {self.linkedin_email}")
        logger.info(f"AgentQL API Key: {self.agentql_api_key[:5]}..." if self.agentql_api_key else "AgentQL API Key: Not set")
        logger.info(f"Max Jobs Per Search: {self.max_jobs_per_search}")
        logger.info(f"Search Interval: {self.search_interval_minutes} minutes")
        logger.info(f"Save Path: {self.save_path}")
        logger.info(f"Notifications Enabled: {self.enable_notifications}")
        if self.enable_notifications:
            logger.info(f"Notification Email: {self.notification_email}")

# Create a global instance
config = Config() 