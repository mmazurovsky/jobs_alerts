import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True, scope="session")
def patch_scraper_functions():
    with patch("main_project.app.scraper_client.search_jobs_via_scraper", new_callable=AsyncMock) as mock_search, \
         patch("main_project.app.scraper_client.check_proxy_connection_via_scraper", new_callable=AsyncMock) as mock_check:
        mock_search.return_value = []  # or whatever mock data you want
        mock_check.return_value = True
        yield 