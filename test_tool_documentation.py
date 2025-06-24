#!/usr/bin/env python3
"""
Test script to verify tool documentation and help system.
"""
import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from main_project.app.llm.tools.tool_registry import create_tool_registry
from main_project.app.core.job_search_manager import JobSearchManager

async def test_tool_documentation():
    """Test the tool documentation system."""
    print("🧪 Testing Tool Documentation System\n")
    
    # Create a mock job search manager (we don't need real MongoDB for this test)
    class MockJobSearchManager:
        def __init__(self):
            pass
    
    job_search_manager = MockJobSearchManager()
    
    # Create tool registry
    tool_registry = create_tool_registry(job_search_manager)
    
    print("✅ Tool Registry Created Successfully\n")
    print(f"📋 Available tools: {list(tool_registry.tools.keys())}\n")
    
    # Test getting all tools help
    print("🔍 Testing All Tools Help:")
    print("=" * 50)
    all_help = tool_registry.get_all_tools_help()
    print(all_help)
    print("\n" + "=" * 50 + "\n")
    
    # Test specific tool help
    print("🔍 Testing Specific Tool Help (Create Job Search):")
    print("=" * 50)
    create_help = tool_registry.get_tool_help("create_job_search")
    if create_help:
        print(create_help)
    else:
        print("❌ No help found for create_job_search")
    print("\n" + "=" * 50 + "\n")
    
    # Test parameter help
    print("🔍 Testing Parameter Help:")
    print("=" * 50)
    param_help = tool_registry.get_parameter_help("create_job_search", "job_title")
    if param_help:
        print(f"Parameter help for 'job_title':\n{param_help}")
    else:
        print("❌ No parameter help found")
    print("\n" + "=" * 50 + "\n")
    
    # Test missing parameter prompt
    print("🔍 Testing Missing Parameter Prompt:")
    print("=" * 50)
    missing_prompt = tool_registry.get_missing_parameter_prompt("create_job_search", ["job_title", "location"])
    print(f"Missing parameters prompt:\n{missing_prompt}")
    print("\n" + "=" * 50 + "\n")
    
    # Test operation discovery
    print("🔍 Testing Operation Discovery:")
    print("=" * 50)
    test_queries = [
        "I want to create a search",
        "list my searches",
        "delete search abc123",
        "show me details",
        "find jobs now"
    ]
    
    for query in test_queries:
        tool = tool_registry.get_tool_by_operation(query)
        tool_name = tool.name if tool else "Not found"
        print(f"'{query}' -> {tool_name}")
    
    print("\n" + "=" * 50 + "\n")
    print("✅ All tests completed successfully!")

def test_telegram_help_detection():
    """Test the Telegram bot's help detection system."""
    print("\n🧪 Testing Telegram Help Detection\n")
    
    # Skip telegram bot import since it requires environment variables
    # from main_project.app.bot.telegram_bot import TelegramBot
    
    # Create a mock bot instance just to access the helper methods
    class MockBot:
        def _is_help_request(self, message: str) -> bool:
            """Copied from telegram_bot.py for testing."""
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
        
        def _extract_tool_name_from_help(self, message: str):
            """Copied from telegram_bot.py for testing."""
            message_lower = message.lower()
            
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
    
    bot = MockBot()
    
    test_messages = [
        "help with creating searches",
        "how to delete a search",
        "show me how to list my searches",
        "what is a one time search",
        "explain search details",
        "just a regular message",
        "help with finding jobs"
    ]
    
    print("🔍 Testing Help Request Detection:")
    print("=" * 50)
    for msg in test_messages:
        is_help = bot._is_help_request(msg)
        tool_name = bot._extract_tool_name_from_help(msg) if is_help else None
        print(f"'{msg}' -> Help: {is_help}, Tool: {tool_name}")
    
    print("\n✅ Help detection tests completed!")

if __name__ == "__main__":
    async def main():
        await test_tool_documentation()
        test_telegram_help_detection()
    
    asyncio.run(main()) 