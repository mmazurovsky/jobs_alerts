"""
Simple test for LLM integration.
Run with: python test_llm_integration.py
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env in the linkedin_scraper_service directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from llm.litellm_client import LiteLLMClient
from shared.data import JobType, RemoteType, ShortJobListing

async def test_llm_client():
    """Test the LiteLLM client with sample job data."""

    keywords = "Senior Python Developer"
    filter_text = "Looking for senior backend developer role, no hybrid or on-site option, no entry level, no internship. Job should not have requirement to know German language"
    
    # Create sample jobs
    jobs = [
        ShortJobListing(
            title="Senior Python Developer",
            company="Tech Corp",
            location="Remote",
            link="https://example.com/job1",
            created_ago="2 days ago",
            description="Experience Level: Mid-Senior level, Job Type: Full-time, Remote: Remote\nWe are looking for a Senior Python Developer with experience in Django, Flask, and AWS. Must have 5+ years of Python development experience."
        ),
        ShortJobListing(
            title="Frontend React Developer",
            company="Startup Inc",
            location="New York, NY",
            link="https://example.com/job2",
            created_ago="1 day ago",
            description="Experience Level: Mid-Senior level, Job Type: Full-time, Remote: On-site\nSeeking a Frontend Developer skilled in React, TypeScript, and modern CSS. 3+ years experience required."
        ),
        ShortJobListing(
            title="Data Analyst",
            company="Analytics Co",
            location="San Francisco, CA",
            link="https://example.com/job3",
            created_ago="3 hours ago",
            description="Experience Level: Entry level, Job Type: Full-time, Remote: Hybrid\nEntry-level Data Analyst position. SQL, Python, and Tableau experience preferred."
        ),
        ShortJobListing(
            title="Junior Python Developer",
            company="Analytics Co",
            location="San Francisco, CA",
            link="https://example.com/job4",
            created_ago="3 hours ago",
            description="Experience Level: Entry level, Job Type: Full-time, Remote: Remote\nEntry-level Data Analyst position. SQL, Python, and Tableau experience preferred."
        ),
                ShortJobListing(
            title="Middle Python Developer",
            company="Analytics Co",
            location="San Francisco, CA",
            link="https://example.com/job5",
            created_ago="3 hours ago",
            description="Experience Level: Mid-Senior level, Job Type: Full-time, Remote: Remote\nWe are looking for a Senior Python Developer with experience in Django, Flask, and AWS. Must have 5+ years of Python development experience."
        ),
                ShortJobListing(
            title="Senior Python Developer",
            company="Analytics Co",
            location="San Francisco, CA",
            link="https://example.com/job6",
            created_ago="3 hours ago",
            description="Experience Level: Mid-Senior level, Job Type: Full-time, Remote: Hybrid\nWe are looking for a Senior Python Developer with experience in Django, Flask, and AWS. Must have 5+ years of Python development experience."
        ),
                ShortJobListing(
            title="Senior Python Developer",
            company="Some Corp",
            location="Remote",
            link="https://example.com/job7",
            created_ago="6 days ago",
            description=f"Erfahrungsstufe: Mittleres bis Senior-Level. Beschäftigungsart: Vollzeit. Remote: Remote möglich. Wir suchen einen Senior Python Entwickler mit Erfahrung in Django, Flask und AWS. Mindestens 5 Jahre Erfahrung in der Python-Entwicklung sind erforderlich. Deutschkenntnisse auf C1-Niveau sind obligatorisch."
        ),
    ]
    
    # Initialize LLM client
    client = LiteLLMClient()
    
    # Create JobType and RemoteType objects for testing
    full_time_job_type = JobType("Full-time")
    remote_type = RemoteType("Remote")
    
    # Test filtering
    try:
        results = await client.enrich_jobs(
            jobs=jobs,
            keywords=keywords,
            job_types=[full_time_job_type],
            remote_types=[remote_type],
            location="Remote",
            filter_text=keywords,
        )
        
        print("LLM filtering results:")
        for result in results:
            print(f"  Job: {result.title}")
            print(f"    Company: {result.company}")
            print(f"    Score: {result.compatibility_score}")
            print(f"    Filter Reason: {result.filter_reason}")
            print(f"    Tech Stack: {result.techstack}")
            print(f"    Link: {result.link}")
            print()
        
        if not results:
            print("❌ No results returned from filter_jobs! Test failed.")
            return False
        else:
            print(f"✅ {len(results)} results returned from filter_jobs.")
            return True
        
    except Exception as e:
        print(f"LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    print("Testing LLM Integration...")
    
    # Check if API key is set
    if not os.getenv('DEEPSEEK_API_KEY'):
        print("⚠️  DEEPSEEK_API_KEY not set - LLM will use fallback mode")
    
    success = await test_llm_client()
    
    if success:
        print("✅ LLM integration test passed!")
    else:
        print("❌ LLM integration test failed!")

if __name__ == "__main__":
    asyncio.run(main()) 