#!/usr/bin/env python3
"""
Test runner for premium features integration tests.

Usage:
    python test_integration/run_tests.py --help
    python test_integration/run_tests.py --automated
    python test_integration/run_tests.py --manual
    python test_integration/run_tests.py --setup
"""
import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """Setup test environment and check prerequisites."""
    print("🔧 Setting up test environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check MongoDB connection
    try:
        import pymongo
        mongo_url = os.getenv("MONGO_URL")
        client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        client.server_info()
        print(f"✅ MongoDB connection successful: {mongo_url}")
    except Exception as e:
        print(f"⚠️  MongoDB connection failed: {e}")
        print("💡 Make sure MongoDB is running or update MONGO_URL")
        print("🐳 Quick start: docker run -d -p 27017:27017 mongo:latest")
    
    # Install test dependencies
    test_deps = ["pytest", "pytest-asyncio"]
    for dep in test_deps:
        try:
            __import__(dep.replace("-", "_"))
        except ImportError:
            print(f"📦 Installing {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep])
    
    print("✅ Test environment setup complete!")
    return True

def run_automated_tests():
    """Run automated integration tests."""
    print("🧪 Running automated integration tests...")
    
    if not setup_environment():
        return False
    
    # Run pytest
    test_file = project_root / "test_integration" / "test_premium_integration.py"
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-v",
        "--tb=short",
        "--capture=no"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False

async def run_manual_tests():
    """Run manual test bot."""
    print("🤖 Starting manual test bot...")
    
    if not setup_environment():
        return False
    
    # Import and run test bot
    try:
        from main_project.test_integration.test_bot_manual import TestBotController
        
        controller = TestBotController()
        await controller.start()
        
    except KeyboardInterrupt:
        print("\n👋 Manual testing stopped by user")
    except Exception as e:
        print(f"❌ Error running manual test bot: {e}")
        return False
    
    return True

def run_specific_tests(test_pattern: str):
    """Run specific test patterns."""
    print(f"🎯 Running tests matching: {test_pattern}")
    
    if not setup_environment():
        return False
    
    test_file = project_root / "test_integration" / "test_premium_integration.py"
    cmd = [
        sys.executable, "-m", "pytest",
        f"{test_file}::{test_pattern}",
        "-v",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd)
    return result.returncode == 0

def show_status():
    """Show test environment status."""
    print("📊 Test Environment Status")
    print("=" * 40)
    
    # Python version
    print(f"🐍 Python: {sys.version.split()[0]}")
    
    # Environment file
    env_file = project_root / ".env.test"
    if env_file.exists():
        print(f"📁 Environment: {env_file} ✅")
    else:
        print(f"📁 Environment: {env_file} ❌")
    
    # Required packages
    required_packages = ["pytest", "pytest-asyncio", "pymongo", "python-telegram-bot"]
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"📦 {package}: ✅")
        except ImportError:
            print(f"📦 {package}: ❌")
    
    # Environment variables
    env_vars = ["TELEGRAM_BOT_TOKEN", "MONGO_URL", "ADMIN_USER_ID"]
    for var in env_vars:
        value = os.getenv(var)
        if value and not value.startswith("your_"):
            print(f"🔧 {var}: ✅")
        else:
            print(f"🔧 {var}: ❌")
    
    # MongoDB connection
    try:
        import pymongo
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/jobs_alerts_test")
        client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        client.server_info()
        print(f"🗄️  MongoDB: ✅ ({mongo_url})")
    except Exception as e:
        print(f"🗄️  MongoDB: ❌ ({e})")

def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Test runner for premium features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_integration/run_tests.py --automated
  python test_integration/run_tests.py --manual
  python test_integration/run_tests.py --setup
  python test_integration/run_tests.py --specific TestTrialSubscription
  python test_integration/run_tests.py --status
        """
    )
    
    parser.add_argument("--automated", action="store_true",
                       help="Run automated integration tests")
    parser.add_argument("--manual", action="store_true",
                       help="Start interactive test bot")
    parser.add_argument("--setup", action="store_true",
                       help="Setup test environment")
    parser.add_argument("--specific", type=str,
                       help="Run specific test class or method")
    parser.add_argument("--status", action="store_true",
                       help="Show test environment status")
    
    args = parser.parse_args()
    
    if not any([args.automated, args.manual, args.setup, args.specific, args.status]):
        parser.print_help()
        return
    
    if args.status:
        show_status()
    elif args.setup:
        setup_environment()
    elif args.automated:
        success = run_automated_tests()
        sys.exit(0 if success else 1)
    elif args.manual:
        asyncio.run(run_manual_tests())
    elif args.specific:
        success = run_specific_tests(args.specific)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 