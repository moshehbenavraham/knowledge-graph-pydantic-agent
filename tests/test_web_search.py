import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys

# Mock environment variables before importing modules that use them
with patch.dict(os.environ, {
    'BRAVE_API_KEY': 'test-brave-key',
    'SEARXNG_BASE_URL': 'http://test-searxng-url.com'
}):
    # Add src directory to path to import the tools module
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
    from tools.web_search import (
        brave_web_search,
        searxng_web_search,
        web_search_tool,
    )


class TestWebSearchTools:
    @pytest.mark.asyncio
    async def test_brave_web_search_success(self):
        # Mock HTTP client and response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Test Title 1",
                        "description": "Test Description 1",
                        "url": "https://example.com/1"
                    },
                    {
                        "title": "Test Title 2",
                        "description": "Test Description 2",
                        "url": "https://example.com/2"
                    }
                ]
            }
        }
        mock_client.get.return_value = mock_response
        
        # Test the function
        result = await brave_web_search("test query", mock_client, "test-api-key")
        
        # Verify the HTTP request was made correctly
        mock_client.get.assert_called_once_with(
            'https://api.search.brave.com/res/v1/web/search',
            params={
                'q': "test query",
                'count': 5,
                'text_decorations': True,
                'search_lang': 'en'
            },
            headers={
                'X-Subscription-Token': 'test-api-key',
                'Accept': 'application/json',
            }
        )
        
        # Verify the response was processed correctly
        assert "Test Title 1" in result
        assert "Test Description 1" in result
        assert "https://example.com/1" in result
        assert "Test Title 2" in result
        assert "Test Description 2" in result
        assert "https://example.com/2" in result

    @pytest.mark.asyncio
    async def test_brave_web_search_no_results(self):
        # Mock HTTP client and response with no results
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_client.get.return_value = mock_response
        
        # Test the function
        result = await brave_web_search("test query", mock_client, "test-api-key")
        
        # Verify the response for no results
        assert result == "No results found for the query."

    @pytest.mark.asyncio
    async def test_searxng_web_search_success(self):
        # Mock HTTP client and response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "SearXNG Result 1",
                    "url": "https://example.com/searxng1",
                    "content": "SearXNG Content 1"
                },
                {
                    "title": "SearXNG Result 2",
                    "url": "https://example.com/searxng2",
                    "content": "SearXNG Content 2"
                }
            ]
        }
        mock_client.get.return_value = mock_response
        
        # Test the function
        result = await searxng_web_search("test query", mock_client, "https://searxng.example.com")
        
        # Verify the HTTP request was made correctly
        mock_client.get.assert_called_once_with(
            "https://searxng.example.com/search",
            params={'q': "test query", 'format': 'json'}
        )
        
        # Verify the response was processed correctly
        assert "SearXNG Result 1" in result
        assert "https://example.com/searxng1" in result
        assert "SearXNG Content 1" in result
        assert "SearXNG Result 2" in result
        assert "https://example.com/searxng2" in result
        assert "SearXNG Content 2" in result

    @pytest.mark.asyncio
    async def test_searxng_web_search_no_results(self):
        # Mock HTTP client and response with no results
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_client.get.return_value = mock_response
        
        # Test the function
        result = await searxng_web_search("test query", mock_client, "https://searxng.example.com")
        
        # Verify the response for no results
        assert result == "No results found for the query."

    @pytest.mark.asyncio
    @patch('tools.web_search.brave_web_search')
    async def test_web_search_tool_with_brave(self, mock_brave_search):
        # Setup mock for brave search
        mock_brave_search.return_value = "Brave search results"
        
        # Create a specific mock client to pass to the function
        mock_client = AsyncMock()
        
        # Test with Brave API key provided
        result = await web_search_tool(
            "test query", 
            mock_client, 
            "brave-api-key", 
            "https://searxng.example.com"
        )
        
        # Verify Brave search was called with the right parameters
        # Use ANY for the client parameter since we can't directly compare AsyncMock instances
        from unittest.mock import ANY
        mock_brave_search.assert_called_once_with("test query", ANY, "brave-api-key")
        assert result == "Brave search results"

    @pytest.mark.asyncio
    @patch('tools.web_search.searxng_web_search')
    async def test_web_search_tool_with_searxng(self, mock_searxng_search):
        # Setup mock for SearXNG search
        mock_searxng_search.return_value = "SearXNG search results"
        
        # Create a specific mock client to pass to the function
        mock_client = AsyncMock()
        
        # Test with no Brave API key (should use SearXNG)
        result = await web_search_tool(
            "test query", 
            mock_client, 
            "", 
            "https://searxng.example.com"
        )
        
        # Verify SearXNG search was called with the right parameters
        # Use ANY for the client parameter since we can't directly compare AsyncMock instances
        from unittest.mock import ANY
        mock_searxng_search.assert_called_once_with("test query", ANY, "https://searxng.example.com")
        assert result == "SearXNG search results"

    @pytest.mark.asyncio
    async def test_web_search_tool_exception(self):
        # Mock HTTP client that raises an exception
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Test exception")
        
        # Test with both API keys to ensure exception handling
        result = await web_search_tool(
            "test query", 
            mock_client, 
            "brave-api-key", 
            "https://searxng.example.com"
        )
        
        # Verify exception was handled
        assert "Test exception" in result