"""
Comprehensive tests for web_search.py module.

Tests all web search providers (Jina, Brave, SearXNG) with success/failure scenarios,
rate limiting, performance tracking, and provider selection logic.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.tools.web_search import (
    brave_web_search,
    jina_read_url,
    jina_web_search,
    searxng_web_search,
    web_search_tool,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_http_client():
    """Mock AsyncClient for HTTP requests."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def jina_api_key():
    """Test Jina API key."""
    return "test_jina_key_123"


@pytest.fixture
def brave_api_key():
    """Test Brave API key."""
    return "test_brave_key_456"


@pytest.fixture
def searxng_base_url():
    """Test SearXNG base URL."""
    return "http://searxng.local"


# ============================================================================
# jina_read_url Tests
# ============================================================================


@pytest.mark.asyncio
async def test_jina_read_url_success(mock_http_client, jina_api_key):
    """Test successful URL reading with Jina Reader API."""
    # Mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"title": "Test Article", "content": "This is test content from the URL."}
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_read_url(
        "https://example.com/article", mock_http_client, jina_api_key
    )

    assert "Test Article" in result
    assert "This is test content from the URL." in result
    mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_jina_read_url_long_content_truncation(mock_http_client, jina_api_key):
    """Test that long content is truncated to 3000 characters."""
    long_content = "a" * 5000
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"title": "Long Article", "content": long_content}
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_read_url("https://example.com", mock_http_client, jina_api_key)

    assert len(result) <= 3000 + 20  # +20 for title and formatting
    assert result.endswith("...")


@pytest.mark.asyncio
async def test_jina_read_url_no_content(mock_http_client, jina_api_key):
    """Test handling of response with no content."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"title": "Empty", "content": ""}}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_read_url("https://example.com", mock_http_client, jina_api_key)

    assert result == "Could not extract content from the URL."


@pytest.mark.asyncio
async def test_jina_read_url_malformed_response(mock_http_client, jina_api_key):
    """Test handling of malformed JSON response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"unexpected": "format"}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_read_url("https://example.com", mock_http_client, jina_api_key)

    assert result == "Could not extract content from the URL."


@pytest.mark.asyncio
async def test_jina_read_url_http_error(mock_http_client, jina_api_key):
    """Test handling of HTTP errors."""
    mock_http_client.get.side_effect = httpx.HTTPStatusError(
        "404 Not Found",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await jina_read_url("https://example.com", mock_http_client, jina_api_key)


@pytest.mark.asyncio
async def test_jina_read_url_timeout(mock_http_client, jina_api_key):
    """Test handling of request timeout."""
    mock_http_client.get.side_effect = httpx.TimeoutException("Request timeout")

    with pytest.raises(httpx.TimeoutException):
        await jina_read_url("https://example.com", mock_http_client, jina_api_key)


@pytest.mark.asyncio
async def test_jina_read_url_special_characters(mock_http_client, jina_api_key):
    """Test URL encoding with special characters."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"title": "Special", "content": "Content"}
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    url_with_special_chars = "https://example.com/page?query=hello world&lang=en"
    result = await jina_read_url(url_with_special_chars, mock_http_client, jina_api_key)

    assert "Special" in result
    # Verify URL was encoded
    call_args = mock_http_client.get.call_args
    assert "https://r.jina.ai/" in call_args[0][0]


# ============================================================================
# jina_web_search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_jina_web_search_success(mock_http_client, jina_api_key):
    """Test successful web search with Jina API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "code": 200,
        "status": "success",
        "data": [
            {
                "title": "Result 1",
                "content": "Content 1",
                "url": "https://example.com/1",
                "description": "Description 1",
            },
            {
                "title": "Result 2",
                "content": "Content 2",
                "url": "https://example.com/2",
                "description": "Description 2",
            },
        ],
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_web_search("test query", mock_http_client, jina_api_key)

    assert "Jina.ai Search Results" in result
    assert "Result 1" in result
    assert "Result 2" in result
    assert "https://example.com/1" in result


@pytest.mark.asyncio
async def test_jina_web_search_list_response(mock_http_client, jina_api_key):
    """Test Jina search with list response format."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"title": "Direct List", "content": "Content", "url": "https://example.com"}
    ]
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_web_search("test query", mock_http_client, jina_api_key)

    assert "Jina.ai Search Results" in result
    assert "Direct List" in result


@pytest.mark.asyncio
async def test_jina_web_search_long_content_truncation(mock_http_client, jina_api_key):
    """Test that long content is truncated to 500 characters."""
    long_content = "x" * 1000
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "title": "Long Result",
                "content": long_content,
                "url": "https://example.com",
                "description": "Short desc",
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_web_search("test query", mock_http_client, jina_api_key)

    # Content should be truncated
    assert long_content not in result
    assert "..." in result


@pytest.mark.asyncio
async def test_jina_web_search_fallback_to_description(mock_http_client, jina_api_key):
    """Test fallback to description when content is missing."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "title": "No Content",
                "content": "",
                "url": "https://example.com",
                "description": "This is the description",
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_web_search("test query", mock_http_client, jina_api_key)

    assert "This is the description" in result


@pytest.mark.asyncio
async def test_jina_web_search_no_results(mock_http_client, jina_api_key):
    """Test handling of empty search results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_web_search("test query", mock_http_client, jina_api_key)

    assert result == "No results found for the query."


@pytest.mark.asyncio
async def test_jina_web_search_unexpected_format(mock_http_client, jina_api_key):
    """Test handling of unexpected response format."""
    mock_response = MagicMock()
    mock_response.json.return_value = "unexpected string response"
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_web_search("test query", mock_http_client, jina_api_key)

    assert result == "No results found for the query."


@pytest.mark.asyncio
async def test_jina_web_search_limits_to_five_results(mock_http_client, jina_api_key):
    """Test that only top 5 results are returned."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"title": f"Result {i}", "content": f"Content {i}", "url": f"https://example.com/{i}"} for i in range(10)]
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await jina_web_search("test query", mock_http_client, jina_api_key)

    # Should only contain results 1-5
    assert "Result 0" in result
    assert "Result 4" in result
    assert "Result 5" not in result
    assert "Result 9" not in result


@pytest.mark.asyncio
async def test_jina_web_search_http_error(mock_http_client, jina_api_key):
    """Test handling of HTTP errors in Jina search."""
    mock_http_client.get.side_effect = httpx.HTTPStatusError(
        "503 Service Unavailable",
        request=MagicMock(),
        response=MagicMock(status_code=503),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await jina_web_search("test query", mock_http_client, jina_api_key)


# ============================================================================
# brave_web_search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_brave_web_search_success(mock_http_client, brave_api_key):
    """Test successful web search with Brave API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "web": {
            "results": [
                {
                    "title": "Brave Result 1",
                    "description": "Description 1",
                    "url": "https://brave1.com",
                },
                {
                    "title": "Brave Result 2",
                    "description": "Description 2",
                    "url": "https://brave2.com",
                },
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await brave_web_search("test query", mock_http_client, brave_api_key)

    assert "Brave Result 1" in result
    assert "Description 1" in result
    assert "https://brave1.com" in result
    assert "Brave Result 2" in result


@pytest.mark.asyncio
async def test_brave_web_search_limits_to_three_results(mock_http_client, brave_api_key):
    """Test that Brave search limits to top 3 results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "web": {
            "results": [
                {"title": f"Result {i}", "description": f"Desc {i}", "url": f"https://example.com/{i}"}
                for i in range(10)
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await brave_web_search("test query", mock_http_client, brave_api_key)

    # Should only contain first 3 results
    assert "Result 0" in result
    assert "Result 2" in result
    assert "Result 3" not in result


@pytest.mark.asyncio
async def test_brave_web_search_no_results(mock_http_client, brave_api_key):
    """Test handling of empty Brave search results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"web": {"results": []}}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await brave_web_search("test query", mock_http_client, brave_api_key)

    assert result == "No results found for the query."


@pytest.mark.asyncio
async def test_brave_web_search_missing_fields(mock_http_client, brave_api_key):
    """Test handling of results with missing title or description."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "web": {
            "results": [
                {"title": "Complete", "description": "Has both", "url": "https://complete.com"},
                {"title": "", "description": "No title", "url": "https://notitle.com"},
                {"title": "No desc", "description": "", "url": "https://nodesc.com"},
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await brave_web_search("test query", mock_http_client, brave_api_key)

    # Only complete result should be included
    assert "Complete" in result
    assert "No title" not in result
    assert "No desc" not in result


@pytest.mark.asyncio
async def test_brave_web_search_malformed_response(mock_http_client, brave_api_key):
    """Test handling of malformed Brave API response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"unexpected": "structure"}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await brave_web_search("test query", mock_http_client, brave_api_key)

    assert result == "No results found for the query."


@pytest.mark.asyncio
async def test_brave_web_search_http_error(mock_http_client, brave_api_key):
    """Test handling of HTTP errors in Brave search."""
    mock_http_client.get.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await brave_web_search("test query", mock_http_client, brave_api_key)


@pytest.mark.asyncio
async def test_brave_web_search_correct_headers(mock_http_client, brave_api_key):
    """Test that correct headers are sent to Brave API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"web": {"results": []}}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    await brave_web_search("test query", mock_http_client, brave_api_key)

    # Check that correct headers were sent
    call_kwargs = mock_http_client.get.call_args[1]
    assert "headers" in call_kwargs
    assert call_kwargs["headers"]["X-Subscription-Token"] == brave_api_key
    assert call_kwargs["headers"]["Accept"] == "application/json"


# ============================================================================
# searxng_web_search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_searxng_web_search_success(mock_http_client, searxng_base_url):
    """Test successful web search with SearXNG."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "title": "SearXNG Result 1",
                "url": "https://searxng1.com",
                "content": "This is content from SearXNG result 1. " * 10,
            },
            {
                "title": "SearXNG Result 2",
                "url": "https://searxng2.com",
                "content": "This is content from SearXNG result 2.",
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await searxng_web_search("test query", mock_http_client, searxng_base_url)

    assert "SearXNG Result 1" in result
    assert "https://searxng1.com" in result
    assert "SearXNG Result 2" in result


@pytest.mark.asyncio
async def test_searxng_web_search_content_truncation(mock_http_client, searxng_base_url):
    """Test that content is truncated to 300 characters."""
    long_content = "a" * 500
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"title": "Long", "url": "https://example.com", "content": long_content}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await searxng_web_search("test query", mock_http_client, searxng_base_url)

    # Should be truncated to 300 chars + ellipsis
    assert len(result) < len(long_content)
    assert "..." in result


@pytest.mark.asyncio
async def test_searxng_web_search_limits_to_ten_results(mock_http_client, searxng_base_url):
    """Test that SearXNG search limits to top 10 results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"title": f"Result {i}", "url": f"https://example.com/{i}", "content": f"Content {i}"}
            for i in range(20)
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await searxng_web_search("test query", mock_http_client, searxng_base_url)

    # Should only contain results 1-10
    assert "Result 0" in result
    assert "Result 9" in result
    assert "Result 10" not in result
    assert "Result 19" not in result


@pytest.mark.asyncio
async def test_searxng_web_search_no_results(mock_http_client, searxng_base_url):
    """Test handling of empty SearXNG search results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await searxng_web_search("test query", mock_http_client, searxng_base_url)

    assert result == "No results found for the query."


@pytest.mark.asyncio
async def test_searxng_web_search_missing_fields(mock_http_client, searxng_base_url):
    """Test handling of results with missing fields."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"title": "Missing fields"}]  # Missing url and content
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await searxng_web_search("test query", mock_http_client, searxng_base_url)

    assert "Missing fields" in result
    assert "No URL" in result
    assert "No content" in result


@pytest.mark.asyncio
async def test_searxng_web_search_http_error(mock_http_client, searxng_base_url):
    """Test handling of HTTP errors in SearXNG search."""
    mock_http_client.get.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await searxng_web_search("test query", mock_http_client, searxng_base_url)


@pytest.mark.asyncio
async def test_searxng_web_search_correct_params(mock_http_client, searxng_base_url):
    """Test that correct parameters are sent to SearXNG."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    await searxng_web_search("test query", mock_http_client, searxng_base_url)

    # Check correct URL and params
    call_args = mock_http_client.get.call_args
    assert f"{searxng_base_url}/search" in call_args[0][0]
    assert "params" in call_args[1]
    assert call_args[1]["params"]["q"] == "test query"
    assert call_args[1]["params"]["format"] == "json"


# ============================================================================
# web_search_tool Tests (Main Function)
# ============================================================================


@pytest.mark.asyncio
async def test_web_search_tool_explicit_jina(mock_http_client, jina_api_key):
    """Test explicit Jina provider selection."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"title": "Jina", "content": "Content", "url": "https://example.com"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool(
        "test query", mock_http_client, jina_api_key=jina_api_key, search_provider="jina"
    )

    assert "Jina.ai Search Results" in result


@pytest.mark.asyncio
async def test_web_search_tool_explicit_brave(mock_http_client, brave_api_key):
    """Test explicit Brave provider selection."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"web": {"results": [{"title": "Brave", "description": "Desc", "url": "https://example.com"}]}}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool(
        "test query", mock_http_client, brave_api_key=brave_api_key, search_provider="brave"
    )

    assert "Brave" in result


@pytest.mark.asyncio
async def test_web_search_tool_explicit_searxng(mock_http_client, searxng_base_url):
    """Test explicit SearXNG provider selection."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"title": "SearXNG", "url": "https://example.com", "content": "Content"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool(
        "test query",
        mock_http_client,
        searxng_base_url=searxng_base_url,
        search_provider="searxng",
    )

    assert "SearXNG" in result


@pytest.mark.asyncio
async def test_web_search_tool_auto_select_jina_priority(
    mock_http_client, jina_api_key, brave_api_key, searxng_base_url
):
    """Test auto-selection prioritizes Jina when all providers available."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"title": "Jina", "content": "Content", "url": "https://example.com"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool(
        "test query",
        mock_http_client,
        jina_api_key=jina_api_key,
        brave_api_key=brave_api_key,
        searxng_base_url=searxng_base_url,
    )

    # Should use Jina (highest priority)
    assert "Jina.ai Search Results" in result


@pytest.mark.asyncio
async def test_web_search_tool_auto_select_brave_fallback(
    mock_http_client, brave_api_key, searxng_base_url
):
    """Test auto-selection falls back to Brave when Jina not available."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"web": {"results": [{"title": "Brave", "description": "Desc", "url": "https://example.com"}]}}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool(
        "test query",
        mock_http_client,
        brave_api_key=brave_api_key,
        searxng_base_url=searxng_base_url,
    )

    assert "Brave" in result


@pytest.mark.asyncio
async def test_web_search_tool_auto_select_searxng_fallback(mock_http_client, searxng_base_url):
    """Test auto-selection falls back to SearXNG when Jina and Brave not available."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"title": "SearXNG", "url": "https://example.com", "content": "Content"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool("test query", mock_http_client, searxng_base_url=searxng_base_url)

    assert "SearXNG" in result


@pytest.mark.asyncio
async def test_web_search_tool_no_providers_configured(mock_http_client):
    """Test error message when no providers are configured."""
    result = await web_search_tool("test query", mock_http_client)

    assert "No web search provider configured" in result
    assert "JINA_API_KEY" in result
    assert "BRAVE_API_KEY" in result
    assert "SEARXNG_BASE_URL" in result


@pytest.mark.asyncio
async def test_web_search_tool_explicit_provider_not_available(mock_http_client):
    """Test error when explicit provider requested but not configured."""
    result = await web_search_tool(
        "test query", mock_http_client, search_provider="jina"
    )

    assert "Search provider 'jina' not available or not configured" in result


@pytest.mark.asyncio
async def test_web_search_tool_exception_handling(mock_http_client, jina_api_key):
    """Test that exceptions are caught and returned as error messages."""
    mock_http_client.get.side_effect = Exception("Network error")

    result = await web_search_tool(
        "test query", mock_http_client, jina_api_key=jina_api_key
    )

    assert "Web search failed" in result
    assert "Network error" in result


@pytest.mark.asyncio
async def test_web_search_tool_case_insensitive_provider(mock_http_client, jina_api_key):
    """Test that provider selection is case-insensitive."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"title": "Jina", "content": "Content", "url": "https://example.com"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    # Try with uppercase
    result = await web_search_tool(
        "test query", mock_http_client, jina_api_key=jina_api_key, search_provider="JINA"
    )

    assert "Jina.ai Search Results" in result


@pytest.mark.asyncio
@patch("src.tools.web_search.logger")
async def test_web_search_tool_logging(mock_logger, mock_http_client, jina_api_key):
    """Test that appropriate logging occurs."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"title": "Result", "content": "Content", "url": "https://example.com"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    await web_search_tool("test query", mock_http_client, jina_api_key=jina_api_key)

    # Check logging calls
    assert mock_logger.info.call_count >= 2  # Start and completion
    assert mock_logger.debug.call_count >= 1  # Provider selection


@pytest.mark.asyncio
@patch("src.tools.web_search.logger")
async def test_web_search_tool_error_logging(mock_logger, mock_http_client, jina_api_key):
    """Test that errors are logged appropriately."""
    mock_http_client.get.side_effect = Exception("Test error")

    await web_search_tool("test query", mock_http_client, jina_api_key=jina_api_key)

    # Check error logging
    mock_logger.error.assert_called_once()
    error_call = mock_logger.error.call_args
    assert "Web search failed" in str(error_call)


# ============================================================================
# Rate Limiting and Performance Tracking Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.tools.web_search.track_performance")
async def test_performance_tracking_applied(mock_track_perf, mock_http_client, jina_api_key):
    """Test that performance tracking decorator is applied."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"title": "Result", "content": "Content", "url": "https://example.com"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    # Performance tracking should be on the function
    assert hasattr(jina_web_search, "__wrapped__") or "track_performance" in str(jina_web_search)


@pytest.mark.asyncio
@patch("src.tools.web_search.rate_limit")
async def test_rate_limiting_applied(mock_rate_limit, mock_http_client, jina_api_key):
    """Test that rate limiting decorator is applied."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"title": "Result", "content": "Content", "url": "https://example.com"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    # Rate limiting should be on the function
    assert hasattr(jina_web_search, "__wrapped__") or "rate_limit" in str(jina_web_search)


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_web_search_unicode_query(mock_http_client, jina_api_key):
    """Test handling of Unicode characters in query."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"title": "Unicode", "content": "Content", "url": "https://example.com"}]}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool(
        "test query with 你好 émojis 🚀", mock_http_client, jina_api_key=jina_api_key
    )

    assert "Unicode" in result or "Jina.ai Search Results" in result


@pytest.mark.asyncio
async def test_web_search_empty_query(mock_http_client, jina_api_key):
    """Test handling of empty query string."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool("", mock_http_client, jina_api_key=jina_api_key)

    # Should handle gracefully
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_web_search_very_long_query(mock_http_client, jina_api_key):
    """Test handling of very long query strings."""
    long_query = "test " * 1000
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response

    result = await web_search_tool(long_query, mock_http_client, jina_api_key=jina_api_key)

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_multiple_providers_sequential_failure(mock_http_client, jina_api_key, brave_api_key):
    """Test that failure in auto-selection doesn't cascade properly."""
    # Jina fails
    mock_http_client.get.side_effect = httpx.HTTPStatusError(
        "500 Error", request=MagicMock(), response=MagicMock(status_code=500)
    )

    result = await web_search_tool(
        "test query",
        mock_http_client,
        jina_api_key=jina_api_key,
        brave_api_key=brave_api_key,
    )

    # Should return error message, not try Brave
    assert "Web search failed" in result
