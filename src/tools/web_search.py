from httpx import AsyncClient

from src.utils.monitoring import logger, track_performance
from src.utils.rate_limiting import rate_limit


@track_performance(tool_name="jina_reader")
@rate_limit(service="jina")
async def jina_read_url(url: str, http_client: AsyncClient, jina_api_key: str) -> str:
    """
    Helper function to read and extract content from a specific URL using Jina Reader API.
    
    Args:
        url: The URL to read and parse
        http_client: HTTP client for making requests
        jina_api_key: Jina.ai API key
    
    Returns:
        Clean, formatted content from the URL
    """
    from urllib.parse import quote
    
    headers = {
        "Authorization": f"Bearer {jina_api_key}",
        "Accept": "application/json",
    }
    
    # Jina.ai Reader API - for specific URL reading
    encoded_url = quote(url, safe='')
    reader_url = f"https://r.jina.ai/{encoded_url}"
    
    try:
        response = await http_client.get(
            reader_url,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Extract content from the response structure
        if isinstance(data, dict) and "data" in data:
            content = data["data"].get("content", "")
            title = data["data"].get("title", "")
            
            if content:
                result = f"**{title}**\n\n{content}"
                # Truncate if too long
                if len(result) > 3000:
                    result = result[:3000] + "..."
                return result
        
        return "Could not extract content from the URL."
            
    except Exception as e:
        logger.error(f"Jina Reader failed for URL {url}: {e}")
        raise


@track_performance(tool_name="jina_web_search")
@rate_limit(service="jina")
async def jina_web_search(query: str, http_client: AsyncClient, jina_api_key: str) -> str:
    """
    Helper function for web_search_tool - searches the web with the Jina.ai Search API
    and returns clean, formatted content from top search results.
    
    Args:
        query: The search query
        http_client: HTTP client for making requests
        jina_api_key: Jina.ai API key
    
    Returns:
        Formatted search results from Jina.ai
    """
    from urllib.parse import quote
    
    headers = {
        "Authorization": f"Bearer {jina_api_key}",
        "Accept": "application/json",
    }
    
    # Jina.ai Search API - properly encode the query
    encoded_query = quote(query)
    search_url = f"https://s.jina.ai/{encoded_query}"
    
    try:
        response = await http_client.get(
            search_url,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        
        # Parse JSON response - search mode returns a list of results
        data = response.json()
        
        # Format the search results
        if isinstance(data, list) and len(data) > 0:
            results = []
            for i, item in enumerate(data[:5], 1):  # Top 5 results
                title = item.get("title", "No title")
                content = item.get("content", "No content")
                url = item.get("url", "")
                
                # Truncate content if too long
                if len(content) > 500:
                    content = content[:500] + "..."
                
                results.append(f"{i}. **{title}**\n   URL: {url}\n   {content}\n")
            
            return "Jina.ai Search Results:\n\n" + "\n".join(results)
        else:
            return "No results found for the query."
            
    except Exception as e:
        logger.error(f"Jina.ai search failed: {e}")
        raise


@track_performance(tool_name="brave_web_search")
@rate_limit(service="brave")
async def brave_web_search(query: str, http_client: AsyncClient, brave_api_key: str) -> str:
    """
    Helper function for web_search_tool - searches the web with the Brave API
    and returns a summary of all the top search results.

    Args are the same as the parent function except without the SearXNG base url.
    """
    headers = {
        "X-Subscription-Token": brave_api_key,
        "Accept": "application/json",
    }

    response = await http_client.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": 5, "text_decorations": True, "search_lang": "en"},
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    results = []

    # Add web results in a nice formatted way
    web_results = data.get("web", {}).get("results", [])
    for item in web_results[:3]:
        title = item.get("title", "")
        description = item.get("description", "")
        url = item.get("url", "")
        if title and description:
            results.append(f"Title: {title}\nSummary: {description}\nSource: {url}\n")

    return "\n".join(results) if results else "No results found for the query."


@track_performance(tool_name="searxng_web_search")
async def searxng_web_search(query: str, http_client: AsyncClient, searxng_base_url: str) -> str:
    """
    Helper function for web_search_tool - searches the web with SearXNG
    and returns a list of the top search results with the most relevant snippet from each page.

    Args are the same as the parent function except without the Brave API key.
    """
    # Prepare the parameters for the request
    params = {"q": query, "format": "json"}

    # Make the request to SearXNG
    response = await http_client.get(f"{searxng_base_url}/search", params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors

    # Parse the results
    data = response.json()

    results = ""
    for i, page in enumerate(data.get("results", []), 1):
        if (
            i > 10
        ):  # Limiting to the top 10 results, could make this a parameter for the function too
            break

        results += f"{i}. {page.get('title', 'No title')}"
        results += f"   URL: {page.get('url', 'No URL')}"
        results += f"   Content: {page.get('content', 'No content')[:300]}...\n\n"

    return results if results else "No results found for the query."


@track_performance(tool_name="web_search_tool")
async def web_search_tool(
    query: str, 
    http_client: AsyncClient, 
    brave_api_key: str = None,
    searxng_base_url: str = None,
    jina_api_key: str = None,
    search_provider: str = None
) -> str:
    """
    Search the web with a specific query and get a summary of the top search results.

    Args:
        query: The query for the web search
        http_client: The client for making HTTP requests
        brave_api_key: Optional API key for Brave search
        searxng_base_url: Optional base URL for SearXNG
        jina_api_key: Optional API key for Jina.ai
        search_provider: Optional explicit provider choice ('jina', 'brave', 'searxng')

    Returns:
        A summary of the web search.
        - Jina.ai: Clean, formatted markdown content
        - Brave: Formatted search results with titles and descriptions
        - SearXNG: List of top search results with snippets
    """
    logger.info("Starting web search", query=query, provider=search_provider)

    try:
        # Explicit provider selection
        if search_provider:
            if search_provider.lower() == "jina" and jina_api_key:
                logger.debug("Using Jina.ai search (explicit)", query=query)
                result = await jina_web_search(query, http_client, jina_api_key)
            elif search_provider.lower() == "brave" and brave_api_key:
                logger.debug("Using Brave search (explicit)", query=query)
                result = await brave_web_search(query, http_client, brave_api_key)
            elif search_provider.lower() == "searxng" and searxng_base_url:
                logger.debug("Using SearXNG search (explicit)", query=query)
                result = await searxng_web_search(query, http_client, searxng_base_url)
            else:
                return f"Search provider '{search_provider}' not available or not configured"
        # Auto-selection based on available credentials (priority: Jina > Brave > SearXNG)
        elif jina_api_key:
            logger.debug("Using Jina.ai search (auto)", query=query)
            result = await jina_web_search(query, http_client, jina_api_key)
        elif brave_api_key:
            logger.debug("Using Brave search (auto)", query=query)
            result = await brave_web_search(query, http_client, brave_api_key)
        elif searxng_base_url:
            logger.debug("Using SearXNG search (auto)", query=query, searxng_url=searxng_base_url)
            result = await searxng_web_search(query, http_client, searxng_base_url)
        else:
            return "No web search provider configured. Please set JINA_API_KEY, BRAVE_API_KEY, or SEARXNG_BASE_URL"

        logger.info("Web search completed successfully", query=query, result_length=len(result))
        return result

    except Exception as e:
        logger.error("Web search failed", query=query, error=str(e), error_type=type(e).__name__)
        return f"Web search failed: {e!s}"
