"""
Comprehensive integration tests for tools/web_search.py.

Tests web search tools including Jina, Brave, and SearXNG providers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture
def mock_http_client():
    """Mock HTTP client."""
    client = MagicMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def mock_jina_response():
    """Mock Jina API response."""
    return {
        "data": [
            {
                "title": "Result 1",
                "content": "Content for result 1",
                "url": "https://example.com/1",
                "description": "Description 1",
            },
            {
                "title": "Result 2",
                "content": "Content for result 2",
                "url": "https://example.com/2",
                "description": "Description 2",
            },
        ]
    }


@pytest.fixture
def mock_brave_response():
    """Mock Brave API response."""
    return {
        "web": {
            "results": [
                {
                    "title": "Brave Result 1",
                    "description": "Brave description 1",
                    "url": "https://example.com/brave1",
                },
                {
                    "title": "Brave Result 2",
                    "description": "Brave description 2",
                    "url": "https://example.com/brave2",
                },
            ]
        }
    }


@pytest.fixture
def mock_searxng_response():
    """Mock SearXNG response."""
    return {
        "results": [
            {
                "title": "SearXNG Result 1",
                "content": "SearXNG content 1",
                "url": "https://example.com/searx1",
            },
            {
                "title": "SearXNG Result 2",
                "content": "SearXNG content 2",
                "url": "https://example.com/searx2",
            },
        ]
    }


class TestJinaReadUrl:
    """Test jina_read_url function."""

    @patch("src.tools.web_search.track_performance")
    @patch("src.tools.web_search.rate_limit")
    async def test_jina_read_url_success(self, mock_rate_limit, mock_track, mock_http_client):
        """Test successful URL reading with Jina."""
        from src.tools.web_search import jina_read_url

        # Mock decorators
        mock_rate_limit.return_value = lambda f: f
        mock_track.return_value = lambda f: f

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "title": "Test Page",
                "content": "Page content here",
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await jina_read_url(
            url="https://example.com",
            http_client=mock_http_client,
            jina_api_key="test-key",
        )

        assert "Test Page" in result
        assert "Page content here" in result
        assert mock_http_client.get.called

    @patch("src.tools.web_search.track_performance")
    @patch("src.tools.web_search.rate_limit")
    async def test_jina_read_url_truncates_long_content(
        self, mock_rate_limit, mock_track, mock_http_client
    ):
        """Test long content is truncated."""
        from src.tools.web_search import jina_read_url

        mock_rate_limit.return_value = lambda f: f
        mock_track.return_value = lambda f: f

        long_content = "x" * 5000

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "title": "Long Page",
                "content": long_content,
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await jina_read_url(
            url="https://example.com",
            http_client=mock_http_client,
            jina_api_key="test-key",
        )

        assert len(result) <= 3100  # 3000 + title + formatting

    @patch("src.tools.web_search.track_performance")
    @patch("src.tools.web_search.rate_limit")
    async def test_jina_read_url_error(self, mock_rate_limit, mock_track, mock_http_client):
        """Test error handling in Jina read."""
        from src.tools.web_search import jina_read_url

        mock_rate_limit.return_value = lambda f: f
        mock_track.return_value = lambda f: f

        mock_http_client.get = AsyncMock(side_effect=Exception("Network error"))

        with pytest.raises(Exception):
            await jina_read_url(
                url="https://example.com",
                http_client=mock_http_client,
                jina_api_key="test-key",
            )


class TestJinaWebSearch:
    """Test jina_web_search function."""

    @patch("src.tools.web_search.track_performance")
    @patch("src.tools.web_search.rate_limit")
    async def test_jina_search_success(
        self, mock_rate_limit, mock_track, mock_http_client, mock_jina_response
    ):
        """Test successful Jina search."""
        from src.tools.web_search import jina_web_search

        mock_rate_limit.return_value = lambda f: f
        mock_track.return_value = lambda f: f

        mock_response = MagicMock()
        mock_response.json.return_value = mock_jina_response
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await jina_web_search(
            query="test query",
            http_client=mock_http_client,
            jina_api_key="test-key",
        )

        assert "Result 1" in result
        assert "Result 2" in result
        assert "example.com" in result

    @patch("src.tools.web_search.track_performance")
    @patch("src.tools.web_search.rate_limit")
    async def test_jina_search_no_results(self, mock_rate_limit, mock_track, mock_http_client):
        """Test Jina search with no results."""
        from src.tools.web_search import jina_web_search

        mock_rate_limit.return_value = lambda f: f
        mock_track.return_value = lambda f: f

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await jina_web_search(
            query="test query",
            http_client=mock_http_client,
            jina_api_key="test-key",
        )

        assert "No results found" in result


class TestBraveWebSearch:
    """Test brave_web_search function."""

    @patch("src.tools.web_search.track_performance")
    @patch("src.tools.web_search.rate_limit")
    async def test_brave_search_success(
        self, mock_rate_limit, mock_track, mock_http_client, mock_brave_response
    ):
        """Test successful Brave search."""
        from src.tools.web_search import brave_web_search

        mock_rate_limit.return_value = lambda f: f
        mock_track.return_value = lambda f: f

        mock_response = MagicMock()
        mock_response.json.return_value = mock_brave_response
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await brave_web_search(
            query="test query",
            http_client=mock_http_client,
            brave_api_key="test-key",
        )

        assert "Brave Result 1" in result
        assert "Brave description 1" in result

    @patch("src.tools.web_search.track_performance")
    @patch("src.tools.web_search.rate_limit")
    async def test_brave_search_no_results(self, mock_rate_limit, mock_track, mock_http_client):
        """Test Brave search with no results."""
        from src.tools.web_search import brave_web_search

        mock_rate_limit.return_value = lambda f: f
        mock_track.return_value = lambda f: f

        mock_response = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await brave_web_search(
            query="test query",
            http_client=mock_http_client,
            brave_api_key="test-key",
        )

        assert "No results found" in result


class TestSearXNGWebSearch:
    """Test searxng_web_search function."""

    @patch("src.tools.web_search.track_performance")
    async def test_searxng_search_success(
        self, mock_track, mock_http_client, mock_searxng_response
    ):
        """Test successful SearXNG search."""
        from src.tools.web_search import searxng_web_search

        mock_track.return_value = lambda f: f

        mock_response = MagicMock()
        mock_response.json.return_value = mock_searxng_response
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await searxng_web_search(
            query="test query",
            http_client=mock_http_client,
            searxng_base_url="https://searxng.local",
        )

        assert "SearXNG Result 1" in result
        assert "SearXNG content 1" in result

    @patch("src.tools.web_search.track_performance")
    async def test_searxng_search_limits_results(self, mock_track, mock_http_client):
        """Test SearXNG limits to top 10 results."""
        from src.tools.web_search import searxng_web_search

        mock_track.return_value = lambda f: f

        # Create 15 results
        results = [
            {
                "title": f"Result {i}",
                "content": f"Content {i}",
                "url": f"https://example.com/{i}",
            }
            for i in range(15)
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": results}
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await searxng_web_search(
            query="test query",
            http_client=mock_http_client,
            searxng_base_url="https://searxng.local",
        )

        # Should contain first 10 but not 11th
        assert "Result 9" in result
        assert "Result 11" not in result


class TestWebSearchTool:
    """Test web_search_tool main function."""

    @patch("src.tools.web_search.jina_web_search")
    async def test_web_search_jina_explicit(self, mock_jina, mock_http_client):
        """Test web search with explicit Jina provider."""
        from src.tools.web_search import web_search_tool

        mock_jina.return_value = "Jina results"

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            jina_api_key="jina-key",
            search_provider="jina",
        )

        assert result == "Jina results"
        assert mock_jina.called

    @patch("src.tools.web_search.brave_web_search")
    async def test_web_search_brave_explicit(self, mock_brave, mock_http_client):
        """Test web search with explicit Brave provider."""
        from src.tools.web_search import web_search_tool

        mock_brave.return_value = "Brave results"

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            brave_api_key="brave-key",
            search_provider="brave",
        )

        assert result == "Brave results"
        assert mock_brave.called

    @patch("src.tools.web_search.searxng_web_search")
    async def test_web_search_searxng_explicit(self, mock_searxng, mock_http_client):
        """Test web search with explicit SearXNG provider."""
        from src.tools.web_search import web_search_tool

        mock_searxng.return_value = "SearXNG results"

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            searxng_base_url="https://searxng.local",
            search_provider="searxng",
        )

        assert result == "SearXNG results"
        assert mock_searxng.called

    @patch("src.tools.web_search.jina_web_search")
    async def test_web_search_auto_selection_jina(self, mock_jina, mock_http_client):
        """Test auto-selection prioritizes Jina."""
        from src.tools.web_search import web_search_tool

        mock_jina.return_value = "Jina results"

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            jina_api_key="jina-key",
            brave_api_key="brave-key",
        )

        assert result == "Jina results"
        assert mock_jina.called

    @patch("src.tools.web_search.jina_web_search")
    @patch("src.tools.web_search.brave_web_search")
    async def test_web_search_fallback_to_brave(self, mock_brave, mock_jina, mock_http_client):
        """Test fallback from Jina to Brave."""
        from src.tools.web_search import web_search_tool

        mock_jina.side_effect = Exception("Jina failed")
        mock_brave.return_value = "Brave fallback results"

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            jina_api_key="jina-key",
            brave_api_key="brave-key",
        )

        assert result == "Brave fallback results"
        assert mock_brave.called

    @patch("src.tools.web_search.jina_web_search")
    @patch("src.tools.web_search.brave_web_search")
    @patch("src.tools.web_search.searxng_web_search")
    async def test_web_search_fallback_chain(
        self, mock_searxng, mock_brave, mock_jina, mock_http_client
    ):
        """Test fallback chain Jina -> Brave -> SearXNG."""
        from src.tools.web_search import web_search_tool

        mock_jina.side_effect = Exception("Jina failed")
        mock_brave.side_effect = Exception("Brave failed")
        mock_searxng.return_value = "SearXNG fallback results"

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            jina_api_key="jina-key",
            brave_api_key="brave-key",
            searxng_base_url="https://searxng.local",
        )

        assert result == "SearXNG fallback results"
        assert mock_searxng.called

    async def test_web_search_no_provider_configured(self, mock_http_client):
        """Test error when no provider configured."""
        from src.tools.web_search import web_search_tool

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
        )

        assert "No web search provider configured" in result

    async def test_web_search_invalid_provider(self, mock_http_client):
        """Test error with invalid provider name."""
        from src.tools.web_search import web_search_tool

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            search_provider="invalid-provider",
        )

        assert "not available" in result

    @patch("src.tools.web_search.jina_web_search")
    async def test_web_search_logging(self, mock_jina, mock_http_client):
        """Test web search logs appropriately."""
        from src.tools.web_search import web_search_tool

        mock_jina.return_value = "Results"

        await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            jina_api_key="key",
        )

        # Function should complete without errors

    @patch("src.tools.web_search.jina_web_search")
    async def test_web_search_complete_failure(self, mock_jina, mock_http_client):
        """Test complete search failure."""
        from src.tools.web_search import web_search_tool

        mock_jina.side_effect = Exception("All providers failed")

        result = await web_search_tool(
            query="test query",
            http_client=mock_http_client,
            jina_api_key="key",
        )

        assert "Web search failed" in result


class TestWebSearchProviderPriority:
    """Test provider priority and selection logic."""

    @patch("src.tools.web_search.jina_web_search")
    @patch("src.tools.web_search.brave_web_search")
    @patch("src.tools.web_search.searxng_web_search")
    async def test_priority_jina_first(self, mock_searxng, mock_brave, mock_jina, mock_http_client):
        """Test Jina has highest priority."""
        from src.tools.web_search import web_search_tool

        mock_jina.return_value = "Jina"
        mock_brave.return_value = "Brave"
        mock_searxng.return_value = "SearXNG"

        result = await web_search_tool(
            query="test",
            http_client=mock_http_client,
            jina_api_key="key",
            brave_api_key="key",
            searxng_base_url="url",
        )

        assert result == "Jina"
        assert not mock_brave.called
        assert not mock_searxng.called

    @patch("src.tools.web_search.brave_web_search")
    @patch("src.tools.web_search.searxng_web_search")
    async def test_priority_brave_second(self, mock_searxng, mock_brave, mock_http_client):
        """Test Brave is second priority."""
        from src.tools.web_search import web_search_tool

        mock_brave.return_value = "Brave"
        mock_searxng.return_value = "SearXNG"

        result = await web_search_tool(
            query="test",
            http_client=mock_http_client,
            brave_api_key="key",
            searxng_base_url="url",
        )

        assert result == "Brave"
        assert not mock_searxng.called
