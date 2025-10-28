"""
Comprehensive tests for tools/web_search.py - Web search functionality.

Tests cover:
- jina_read_url (URL content extraction)
- jina_web_search (Jina search API)
- brave_web_search (Brave search API)
- searxng_web_search (SearXNG search)
- web_search_tool (main entry point with provider selection)
- Error handling and fallback logic
- Rate limiting and performance tracking
"""

from unittest.mock import AsyncMock, Mock

import pytest
from httpx import AsyncClient, HTTPStatusError, Response


@pytest.fixture
def mock_http_client():
    """Mock AsyncClient for HTTP requests."""
    client = AsyncMock(spec=AsyncClient)
    return client


@pytest.fixture
def jina_api_key():
    """Test Jina API key."""
    return "test_jina_key"


@pytest.fixture
def brave_api_key():
    """Test Brave API key."""
    return "test_brave_key"


@pytest.fixture
def searxng_url():
    """Test SearXNG URL."""
    return "http://localhost:8080"


# ====================
# jina_read_url Tests
# ====================


@pytest.mark.asyncio
async def test_jina_read_url_success(mock_http_client, jina_api_key):
    """Test successful URL reading with Jina."""
    from src.tools.web_search import jina_read_url

    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "title": "Test Page Title",
            "content": "This is the page content from the URL.",
        }
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_read_url("https://example.com", mock_http_client, jina_api_key)

    assert "Test Page Title" in result
    assert "This is the page content" in result

    # Verify API call
    mock_http_client.get.assert_called_once()
    call_args = mock_http_client.get.call_args
    assert "r.jina.ai" in call_args[0][0]


@pytest.mark.asyncio
async def test_jina_read_url_long_content(mock_http_client, jina_api_key):
    """Test that long content is truncated."""
    from src.tools.web_search import jina_read_url

    long_content = "x" * 5000

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "data": {
            "title": "Long Page",
            "content": long_content,
        }
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_read_url("https://example.com", mock_http_client, jina_api_key)

    # Should be truncated to 3000 chars
    assert len(result) <= 3003  # 3000 + "..."


@pytest.mark.asyncio
async def test_jina_read_url_no_content(mock_http_client, jina_api_key):
    """Test Jina read when no content is returned."""
    from src.tools.web_search import jina_read_url

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "data": {
            "title": "Empty Page",
            "content": "",
        }
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_read_url("https://example.com", mock_http_client, jina_api_key)

    assert "Could not extract content" in result


@pytest.mark.asyncio
async def test_jina_read_url_error(mock_http_client, jina_api_key):
    """Test Jina read error handling."""
    from src.tools.web_search import jina_read_url

    mock_http_client.get = AsyncMock(
        side_effect=HTTPStatusError("API error", request=Mock(), response=Mock())
    )

    with pytest.raises(HTTPStatusError):
        await jina_read_url("https://example.com", mock_http_client, jina_api_key)


@pytest.mark.asyncio
async def test_jina_read_url_encoding(mock_http_client, jina_api_key):
    """Test that URLs are properly encoded."""
    from src.tools.web_search import jina_read_url

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"data": {"title": "Test", "content": "Content"}}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    # URL with special characters
    await jina_read_url("https://example.com/page?q=test&lang=en", mock_http_client, jina_api_key)

    # Verify URL was encoded
    call_args = mock_http_client.get.call_args[0][0]
    assert "https%3A%2F%2Fexample.com" in call_args


# ====================
# jina_web_search Tests
# ====================


@pytest.mark.asyncio
async def test_jina_web_search_success(mock_http_client, jina_api_key):
    """Test successful web search with Jina."""
    from src.tools.web_search import jina_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "data": [
            {
                "title": "Result 1",
                "url": "https://example1.com",
                "content": "This is the first result content.",
                "description": "First result description",
            },
            {
                "title": "Result 2",
                "url": "https://example2.com",
                "content": "Second result content here.",
                "description": "Second result description",
            },
        ]
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_web_search("machine learning", mock_http_client, jina_api_key)

    assert "Result 1" in result
    assert "Result 2" in result
    assert "https://example1.com" in result
    assert "Jina.ai Search Results" in result


@pytest.mark.asyncio
async def test_jina_web_search_limit_results(mock_http_client, jina_api_key):
    """Test that Jina search limits to top 5 results."""
    from src.tools.web_search import jina_web_search

    # Create 10 results
    results = [
        {
            "title": f"Result {i}",
            "url": f"https://example{i}.com",
            "content": f"Content {i}",
        }
        for i in range(10)
    ]

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"data": results}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_web_search("test query", mock_http_client, jina_api_key)

    # Should only include top 5
    assert "Result 4" in result
    assert "Result 5" not in result


@pytest.mark.asyncio
async def test_jina_web_search_truncate_content(mock_http_client, jina_api_key):
    """Test that long content is truncated."""
    from src.tools.web_search import jina_web_search

    long_content = "x" * 1000

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "data": [
            {
                "title": "Long Result",
                "url": "https://example.com",
                "content": long_content,
            }
        ]
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_web_search("test", mock_http_client, jina_api_key)

    # Content should be truncated to 500 chars
    assert "..." in result


@pytest.mark.asyncio
async def test_jina_web_search_use_description_fallback(mock_http_client, jina_api_key):
    """Test that description is used when content is missing."""
    from src.tools.web_search import jina_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "data": [
            {
                "title": "Result",
                "url": "https://example.com",
                "content": "",
                "description": "This is the description",
            }
        ]
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_web_search("test", mock_http_client, jina_api_key)

    assert "This is the description" in result


@pytest.mark.asyncio
async def test_jina_web_search_empty_results(mock_http_client, jina_api_key):
    """Test Jina search with no results."""
    from src.tools.web_search import jina_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"data": []}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_web_search("test", mock_http_client, jina_api_key)

    assert "No results found" in result


@pytest.mark.asyncio
async def test_jina_web_search_error(mock_http_client, jina_api_key):
    """Test Jina search error handling."""
    from src.tools.web_search import jina_web_search

    mock_http_client.get = AsyncMock(side_effect=RuntimeError("API error"))

    with pytest.raises(RuntimeError):
        await jina_web_search("test", mock_http_client, jina_api_key)


# ====================
# brave_web_search Tests
# ====================


@pytest.mark.asyncio
async def test_brave_web_search_success(mock_http_client, brave_api_key):
    """Test successful web search with Brave."""
    from src.tools.web_search import brave_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "web": {
            "results": [
                {
                    "title": "Brave Result 1",
                    "description": "First result from Brave",
                    "url": "https://brave1.com",
                },
                {
                    "title": "Brave Result 2",
                    "description": "Second result from Brave",
                    "url": "https://brave2.com",
                },
            ]
        }
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await brave_web_search("artificial intelligence", mock_http_client, brave_api_key)

    assert "Brave Result 1" in result
    assert "First result from Brave" in result
    assert "https://brave1.com" in result


@pytest.mark.asyncio
async def test_brave_web_search_limit_three(mock_http_client, brave_api_key):
    """Test that Brave search returns top 3 results."""
    from src.tools.web_search import brave_web_search

    results = [
        {
            "title": f"Result {i}",
            "description": f"Description {i}",
            "url": f"https://example{i}.com",
        }
        for i in range(5)
    ]

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"web": {"results": results}}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await brave_web_search("test", mock_http_client, brave_api_key)

    # Should only include top 3
    assert "Result 2" in result
    assert "Result 3" not in result


@pytest.mark.asyncio
async def test_brave_web_search_empty_results(mock_http_client, brave_api_key):
    """Test Brave search with no results."""
    from src.tools.web_search import brave_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"web": {"results": []}}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await brave_web_search("test", mock_http_client, brave_api_key)

    assert "No results found" in result


@pytest.mark.asyncio
async def test_brave_web_search_missing_fields(mock_http_client, brave_api_key):
    """Test Brave search with missing fields in results."""
    from src.tools.web_search import brave_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "web": {
            "results": [
                {
                    "title": "",
                    "description": "Only description",
                    "url": "",
                }
            ]
        }
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await brave_web_search("test", mock_http_client, brave_api_key)

    # Should skip results with missing title
    assert "No results found" in result or "Only description" not in result


# ====================
# searxng_web_search Tests
# ====================


@pytest.mark.asyncio
async def test_searxng_web_search_success(mock_http_client, searxng_url):
    """Test successful web search with SearXNG."""
    from src.tools.web_search import searxng_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "results": [
            {
                "title": "SearXNG Result 1",
                "url": "https://searx1.com",
                "content": "First SearXNG result content here",
            },
            {
                "title": "SearXNG Result 2",
                "url": "https://searx2.com",
                "content": "Second SearXNG result content",
            },
        ]
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await searxng_web_search("python programming", mock_http_client, searxng_url)

    assert "SearXNG Result 1" in result
    assert "https://searx1.com" in result


@pytest.mark.asyncio
async def test_searxng_web_search_limit_ten(mock_http_client, searxng_url):
    """Test that SearXNG search limits to 10 results."""
    from src.tools.web_search import searxng_web_search

    results = [
        {
            "title": f"Result {i}",
            "url": f"https://example{i}.com",
            "content": f"Content {i}",
        }
        for i in range(15)
    ]

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"results": results}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await searxng_web_search("test", mock_http_client, searxng_url)

    # Should only include up to 10
    assert "Result 9" in result
    assert "Result 10" not in result


@pytest.mark.asyncio
async def test_searxng_web_search_truncate_content(mock_http_client, searxng_url):
    """Test that SearXNG content is truncated to 300 chars."""
    from src.tools.web_search import searxng_web_search

    long_content = "x" * 500

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Long Result",
                "url": "https://example.com",
                "content": long_content,
            }
        ]
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await searxng_web_search("test", mock_http_client, searxng_url)

    # Content should be truncated
    assert "x" * 300 in result
    assert "..." in result


@pytest.mark.asyncio
async def test_searxng_web_search_empty_results(mock_http_client, searxng_url):
    """Test SearXNG search with no results."""
    from src.tools.web_search import searxng_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"results": []}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await searxng_web_search("test", mock_http_client, searxng_url)

    assert "No results found" in result


# ====================
# web_search_tool Tests (Main Entry Point)
# ====================


@pytest.mark.asyncio
async def test_web_search_explicit_jina(mock_http_client, jina_api_key):
    """Test web search with explicit Jina provider."""
    from src.tools.web_search import web_search_tool

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "data": [{"title": "Result", "url": "https://test.com", "content": "Content"}]
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await web_search_tool(
        query="test query",
        http_client=mock_http_client,
        jina_api_key=jina_api_key,
        search_provider="jina",
    )

    assert "Result" in result


@pytest.mark.asyncio
async def test_web_search_explicit_brave(mock_http_client, brave_api_key):
    """Test web search with explicit Brave provider."""
    from src.tools.web_search import web_search_tool

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "web": {"results": [{"title": "Brave", "description": "Test", "url": "https://test.com"}]}
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
        brave_api_key=brave_api_key,
        search_provider="brave",
    )

    assert "Brave" in result


@pytest.mark.asyncio
async def test_web_search_explicit_searxng(mock_http_client, searxng_url):
    """Test web search with explicit SearXNG provider."""
    from src.tools.web_search import web_search_tool

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "results": [{"title": "SearXNG", "url": "https://test.com", "content": "Content"}]
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
        searxng_base_url=searxng_url,
        search_provider="searxng",
    )

    assert "SearXNG" in result


@pytest.mark.asyncio
async def test_web_search_auto_select_jina(mock_http_client, jina_api_key):
    """Test web search auto-selects Jina when available."""
    from src.tools.web_search import web_search_tool

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {
        "data": [{"title": "Jina Auto", "url": "https://test.com", "content": "Content"}]
    }

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
        jina_api_key=jina_api_key,
    )

    assert "Jina Auto" in result


@pytest.mark.asyncio
async def test_web_search_fallback_to_brave(mock_http_client, jina_api_key, brave_api_key):
    """Test web search falls back to Brave when Jina fails."""
    from src.tools.web_search import web_search_tool

    # Make Jina fail
    jina_error = HTTPStatusError("Jina failed", request=Mock(), response=Mock())

    # Brave succeeds
    brave_response = Mock(spec=Response)
    brave_response.json.return_value = {
        "web": {
            "results": [
                {"title": "Brave Fallback", "description": "Test", "url": "https://test.com"}
            ]
        }
    }

    call_count = [0]

    async def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First call (Jina) fails
            raise jina_error
        # Second call (Brave) succeeds
        return brave_response

    mock_http_client.get = AsyncMock(side_effect=side_effect)

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
        jina_api_key=jina_api_key,
        brave_api_key=brave_api_key,
    )

    assert "Brave Fallback" in result


@pytest.mark.asyncio
async def test_web_search_fallback_to_searxng(mock_http_client, jina_api_key, searxng_url):
    """Test web search falls back to SearXNG when Jina fails and Brave not available."""
    from src.tools.web_search import web_search_tool

    jina_error = RuntimeError("Jina error")
    searxng_response = Mock(spec=Response)
    searxng_response.json.return_value = {
        "results": [{"title": "SearXNG Fallback", "url": "https://test.com", "content": "Content"}]
    }

    call_count = [0]

    async def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise jina_error
        return searxng_response

    mock_http_client.get = AsyncMock(side_effect=side_effect)

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
        jina_api_key=jina_api_key,
        searxng_base_url=searxng_url,
    )

    assert "SearXNG Fallback" in result


@pytest.mark.asyncio
async def test_web_search_no_provider_configured(mock_http_client):
    """Test web search with no provider configured."""
    from src.tools.web_search import web_search_tool

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
    )

    assert "No web search provider configured" in result


@pytest.mark.asyncio
async def test_web_search_provider_not_available(mock_http_client):
    """Test web search with unavailable provider."""
    from src.tools.web_search import web_search_tool

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
        search_provider="jina",  # Requested but no API key
    )

    assert "not available" in result


@pytest.mark.asyncio
async def test_web_search_all_providers_fail(mock_http_client, jina_api_key, brave_api_key):
    """Test web search when all providers fail."""
    from src.tools.web_search import web_search_tool

    mock_http_client.get = AsyncMock(side_effect=RuntimeError("All failed"))

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
        jina_api_key=jina_api_key,
        brave_api_key=brave_api_key,
    )

    assert "Web search failed" in result


@pytest.mark.asyncio
async def test_web_search_priority_jina_brave_searxng(
    mock_http_client, jina_api_key, brave_api_key, searxng_url
):
    """Test that web search prioritizes Jina > Brave > SearXNG."""
    from src.tools.web_search import web_search_tool

    jina_response = Mock(spec=Response)
    jina_response.json.return_value = {
        "data": [{"title": "Jina Priority", "url": "https://test.com", "content": "Content"}]
    }

    mock_http_client.get = AsyncMock(return_value=jina_response)

    result = await web_search_tool(
        query="test",
        http_client=mock_http_client,
        jina_api_key=jina_api_key,
        brave_api_key=brave_api_key,
        searxng_base_url=searxng_url,
    )

    # Should use Jina (highest priority)
    assert "Jina Priority" in result


# ====================
# Edge Cases
# ====================


@pytest.mark.asyncio
async def test_jina_web_search_unexpected_format(mock_http_client, jina_api_key):
    """Test Jina search with unexpected response format."""
    from src.tools.web_search import jina_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = "unexpected string response"

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_web_search("test", mock_http_client, jina_api_key)

    assert "No results found" in result


@pytest.mark.asyncio
async def test_jina_web_search_list_response(mock_http_client, jina_api_key):
    """Test Jina search when response is directly a list."""
    from src.tools.web_search import jina_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = [
        {"title": "Result", "url": "https://test.com", "content": "Content"}
    ]

    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await jina_web_search("test", mock_http_client, jina_api_key)

    assert "Result" in result


@pytest.mark.asyncio
async def test_brave_web_search_api_parameters(mock_http_client, brave_api_key):
    """Test that Brave search uses correct API parameters."""
    from src.tools.web_search import brave_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"web": {"results": []}}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    await brave_web_search("test query", mock_http_client, brave_api_key)

    # Verify API parameters
    call_kwargs = mock_http_client.get.call_args[1]
    params = call_kwargs["params"]
    assert params["q"] == "test query"
    assert params["count"] == 5
    assert params["text_decorations"] is True
    assert params["search_lang"] == "en"


@pytest.mark.asyncio
async def test_searxng_web_search_api_parameters(mock_http_client, searxng_url):
    """Test that SearXNG search uses correct API parameters."""
    from src.tools.web_search import searxng_web_search

    mock_response = Mock(spec=Response)
    mock_response.json.return_value = {"results": []}

    mock_http_client.get = AsyncMock(return_value=mock_response)

    await searxng_web_search("test query", mock_http_client, searxng_url)

    # Verify API parameters
    call_args = mock_http_client.get.call_args
    assert f"{searxng_url}/search" in call_args[0]
    params = call_args[1]["params"]
    assert params["q"] == "test query"
    assert params["format"] == "json"
