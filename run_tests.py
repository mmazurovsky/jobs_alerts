"""
Test runner script for LinkedIn job scraper tests.
"""
import unittest
import sys
import argparse
from tests.test_linkedin_scraper import TestLinkedInScraper

def run_tests(test_names=None):
    """Run specified tests or all tests if none specified."""
    # Create test suite
    suite = unittest.TestSuite()
    
    if test_names:
        # Add only specified tests
        for test_name in test_names:
            if hasattr(TestLinkedInScraper, test_name):
                suite.addTest(TestLinkedInScraper(test_name))
            else:
                print(f"Warning: Test '{test_name}' not found")
    else:
        # Add all tests
        suite.addTest(unittest.makeTestsFromTestCase(TestLinkedInScraper))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run LinkedIn scraper tests')
    parser.add_argument('tests', nargs='*', help='Specific tests to run (e.g., test_count_jobs test_scrape_jobs)')
    args = parser.parse_args()
    
    sys.exit(run_tests(args.tests)) 