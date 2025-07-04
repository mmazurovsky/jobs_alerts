#!/usr/bin/env python3
"""
Test script for LLM Agent integration.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main_project.app.llm.job_search_agent import JobSearchAgent
from main_project.app.core.job_search_manager import JobSearchManager
from main_project.app.core.stores.job_search_store import JobSearchStore
from main_project.app.core.stores.sent_jobs_store import SentJobsStore
from main_project.app.core.mongo_connection import MongoConnection
from main_project.app.core.config import Config

async def test_llm_agent():
    """Test the LLM Agent with sample interactions."""
    print("🧪 Testing LLM Agent Integration...")
    
    try:
        # Load configuration
        config = Config()
        
        # Initialize MongoDB connection (mock for testing)
        print("📦 Initializing mock dependencies...")
        mongo_connection = MongoConnection(config)
        job_search_store = JobSearchStore(mongo_connection)
        sent_jobs_store = SentJobsStore(mongo_connection)
        
        # Initialize JobSearchManager
        job_search_manager = JobSearchManager(job_search_store, sent_jobs_store, None)
        
        # Initialize LLM Agent
        print("🤖 Initializing LLM Agent...")
        llm_agent = JobSearchAgent(job_search_manager)
        await llm_agent.initialize()
        
        print("✅ LLM Agent initialized successfully!")
        
        # Test user ID
        test_user_id = 12345
        
        # Test cases
        test_messages = [
            "Hello! Can you help me with job searches?",
            "Show me my job searches",
            "I want to create a new job search for Python developer jobs in Berlin",
            "What can you help me with?",
        ]
        
        print("\n🗣️ Testing conversations...")
        for i, message in enumerate(test_messages, 1):
            print(f"\n--- Test {i} ---")
            print(f"👤 User: {message}")
            
            try:
                response = await llm_agent.chat(test_user_id, message)
                print(f"🤖 Agent: {response[:200]}{'...' if len(response) > 200 else ''}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting LLM Agent Test...")
    asyncio.run(test_llm_agent()) 