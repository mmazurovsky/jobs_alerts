#!/usr/bin/env python3
"""
Simple test script to verify job description truncation logic.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from shared.data import ShortJobListing

# Constants from LiteLLMClient
JOB_DESCRIPTION_MAX_LENGTH = 4000
ESTIMATED_TOKENS_PER_CHAR = 0.25
MAX_INPUT_TOKENS = 8000

def format_job_for_prompt(job: ShortJobListing, job_index: int, max_length: int = JOB_DESCRIPTION_MAX_LENGTH) -> str:
    """Format a single job for inclusion in the LLM prompt - simplified version."""
    original_desc_length = len(job.description) if job.description else 0
    description = job.description[:max_length] if job.description else "No description available"
    truncated_desc_length = len(description)
    
    # Log truncation details for verification
    if original_desc_length > max_length:
        print(f"  Job {job_index} description truncated from {original_desc_length} to {truncated_desc_length} chars (max: {max_length})")
    
    formatted_job = f"""
Job ID: {job_index}
Title: {job.title}
Company: {job.company}
Location: {job.location}
Posted: {job.created_ago}
Description: {description}
---"""
    
    # Log formatted job details for verification
    job_char_count = len(formatted_job)
    estimated_tokens = job_char_count * ESTIMATED_TOKENS_PER_CHAR
    print(f"  Job {job_index} formatted: {job_char_count} chars, estimated {estimated_tokens:.1f} tokens")
    
    return formatted_job

def create_test_jobs():
    """Create test jobs with varying description lengths."""
    return [
        ShortJobListing(
            title='Python Developer',
            company='Test Corp',
            location='Remote',
            link='https://test.com/1',
            created_ago='1 day ago',
            description='A' * 2000  # 2000 chars (under 4000 limit)
        ),
        ShortJobListing(
            title='Senior Python Developer',
            company='Big Corp', 
            location='New York',
            link='https://test.com/2',
            created_ago='2 days ago',
            description='B' * 6000  # 6000 chars (over 4000 limit - should be truncated)
        ),
        ShortJobListing(
            title='Data Scientist',
            company='Data Corp',
            location='Remote',
            link='https://test.com/3', 
            created_ago='3 days ago',
            description='C' * 3500  # 3500 chars (under limit)
        ),
        ShortJobListing(
            title='Full Stack Developer',
            company='Startup Inc',
            location='San Francisco',
            link='https://test.com/4',
            created_ago='1 week ago',
            description='D' * 5000  # 5000 chars (over 4000 limit - should be truncated)
        ),
        ShortJobListing(
            title='Machine Learning Engineer',
            company='AI Corp',
            location='Remote',
            link='https://test.com/5',
            created_ago='2 days ago',
            description='E' * 1500  # 1500 chars (under limit)
        )
    ]

def test_job_description_truncation():
    """Test that job descriptions are properly truncated to job_description_max_length."""
    print("=" * 60)
    print("TESTING JOB DESCRIPTION TRUNCATION")
    print("=" * 60)
    
    jobs = create_test_jobs()
    
    print(f"job_description_max_length = {JOB_DESCRIPTION_MAX_LENGTH} characters")
    print()
    
    print("Original job description lengths:")
    for i, job in enumerate(jobs):
        original_length = len(job.description)
        print(f"  Job {i} ({job.title}): {original_length} chars")
    
    print("\nFormatted job descriptions (after truncation):")
    all_truncated_correctly = True
    
    for i, job in enumerate(jobs):
        formatted = format_job_for_prompt(job, i)
        
        # Extract description from formatted output
        desc_start = formatted.find('Description: ') + len('Description: ')
        desc_end = formatted.find('\n---', desc_start)
        if desc_end == -1:
            desc_end = formatted.find('---', desc_start)
        
        desc_in_prompt = formatted[desc_start:desc_end].strip()
        desc_length = len(desc_in_prompt)
        
        original_length = len(job.description)
        expected_length = min(original_length, JOB_DESCRIPTION_MAX_LENGTH)
        
        status = "✅ PASS" if desc_length == expected_length else "❌ FAIL"
        print(f"  Job {i} ({job.title}): {desc_length} chars (expected: {expected_length}) {status}")
        
        if desc_length != expected_length:
            all_truncated_correctly = False
            print(f"    ERROR: Expected {expected_length} chars but got {desc_length}")
    
    print(f"\nTruncation test result: {'✅ ALL PASSED' if all_truncated_correctly else '❌ SOME FAILED'}")
    return all_truncated_correctly

def test_realistic_job():
    """Test with a realistic job description."""
    print("\n" + "=" * 60)
    print("TESTING REALISTIC JOB DESCRIPTION")
    print("=" * 60)
    
    # Create a job with a realistic description that exceeds the limit
    long_description = """Experience Level: Mid-Senior level, Job Type: Full-time, Remote: Remote
We are looking for a Senior Python Developer with experience in Django, Flask, and AWS. Must have 5+ years of Python development experience.

Key Responsibilities:
- Develop and maintain Python applications using Django and Flask frameworks
- Design and implement RESTful APIs  
- Work with AWS services including EC2, S3, RDS, and Lambda
- Collaborate with cross-functional teams to deliver high-quality software
- Write unit tests and integration tests
- Participate in code reviews and technical discussions
- Optimize application performance and scalability

Required Skills:
- 5+ years of Python development experience
- Strong knowledge of Django and Flask frameworks
- Experience with AWS cloud services
- Proficiency in SQL and database design
- Experience with version control systems (Git)
- Knowledge of RESTful API design principles
- Understanding of software development best practices
- Experience with testing frameworks (pytest, unittest)

Nice to Have:
- Experience with Docker and containerization
- Knowledge of microservices architecture
- Familiarity with CI/CD pipelines
- Experience with React or other frontend frameworks
- Knowledge of machine learning libraries (scikit-learn, pandas)

Benefits:
- Competitive salary and equity package
- Health, dental, and vision insurance
- Flexible working hours and remote work options
- Professional development budget
- Modern tech stack and tools"""
    
    job = ShortJobListing(
        title='Senior Python Developer',
        company='Tech Corp',
        location='Remote',
        link='https://example.com/job',
        created_ago='2 days ago',
        description=long_description
    )
    
    print(f"Original description length: {len(job.description)} chars")
    
    formatted = format_job_for_prompt(job, 0)
    
    # Extract description from formatted output
    desc_start = formatted.find('Description: ') + len('Description: ')
    desc_end = formatted.find('\n---', desc_start)
    if desc_end == -1:
        desc_end = formatted.find('---', desc_start)
    
    desc_in_prompt = formatted[desc_start:desc_end].strip()
    
    print(f"Formatted description length: {len(desc_in_prompt)} chars")
    print(f"Max allowed length: {JOB_DESCRIPTION_MAX_LENGTH} chars")
    
    print(f"\nFormatted description preview (first 200 chars):")
    print(f"'{desc_in_prompt[:200]}...'")
    
    if len(desc_in_prompt) > 100:
        print(f"\nFormatted description end (last 100 chars):")
        print(f"'...{desc_in_prompt[-100:]}'")
    
    is_truncated_correctly = len(desc_in_prompt) <= JOB_DESCRIPTION_MAX_LENGTH
    status = "✅ PASS" if is_truncated_correctly else "❌ FAIL"
    print(f"\nRealistic job formatting test: {status}")
    
    return is_truncated_correctly

def estimate_batching():
    """Estimate how many jobs would fit in a batch."""
    print("\n" + "=" * 60) 
    print("ESTIMATING BATCHING BEHAVIOR")
    print("=" * 60)
    
    jobs = create_test_jobs()
    
    # Simulate base prompt
    base_prompt = "You are a recruiter. Evaluate these jobs based on criteria..."
    base_tokens = len(base_prompt) * ESTIMATED_TOKENS_PER_CHAR
    
    estimated_max_jobs = min(15, MAX_INPUT_TOKENS // 800)
    available_tokens = MAX_INPUT_TOKENS - base_tokens - (estimated_max_jobs * 80)
    
    print(f"Max input tokens: {MAX_INPUT_TOKENS}")
    print(f"Base prompt tokens: {base_tokens:.1f}")
    print(f"Available tokens for jobs: {available_tokens:.1f}")
    print(f"Estimated max jobs per batch: {estimated_max_jobs}")
    
    print(f"\nJob token usage:")
    total_tokens = 0
    for i, job in enumerate(jobs):
        formatted = format_job_for_prompt(job, i)
        job_tokens = len(formatted) * ESTIMATED_TOKENS_PER_CHAR
        total_tokens += job_tokens
        print(f"  Job {i}: {job_tokens:.1f} tokens")
    
    print(f"\nTotal tokens for all {len(jobs)} jobs: {total_tokens:.1f}")
    print(f"Would all jobs fit in one batch? {'✅ YES' if total_tokens <= available_tokens else '❌ NO'}")
    
    if total_tokens > available_tokens:
        # Estimate how many batches needed
        estimated_batches = int(total_tokens / available_tokens) + 1
        print(f"Estimated batches needed: {estimated_batches}")

def main():
    """Run all tests."""
    print("Job Description Truncation & Batching Test")
    print("Testing the core logic for job description handling.\n")
    
    try:
        # Run tests
        test1_passed = test_job_description_truncation()
        test2_passed = test_realistic_job()
        
        estimate_batching()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"1. Job Description Truncation: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"2. Realistic Job Formatting: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        
        all_passed = test1_passed and test2_passed
        print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        
        if not all_passed:
            print("\nRecommendations:")
            if not test1_passed:
                print("- Check job description truncation logic")
            if not test2_passed:
                print("- Verify realistic job description handling")
        
        print(f"\nCurrent Configuration:")
        print(f"- job_description_max_length: {JOB_DESCRIPTION_MAX_LENGTH} chars")
        print(f"- estimated_tokens_per_char: {ESTIMATED_TOKENS_PER_CHAR}")
        print(f"- max_input_tokens: {MAX_INPUT_TOKENS}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 