from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from httpx import AsyncClient
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext

from src.clients.llm import get_model
from src.tools import (
    execute_safe_code_tool,
    execute_sql_query_tool,
    get_document_content_tool,
    image_analysis_tool,
    list_documents_tool,
    retrieve_relevant_documents_tool,
    web_search_tool,
)
from supabase.client import Client

from .prompt import AGENT_SYSTEM_PROMPT

# Load environment variables from what we have set for our agent
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path, override=True)


# ========== Pydantic AI Agent ==========
@dataclass
class AgentDeps:
    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient
    brave_api_key: str | None
    searxng_base_url: str | None
    memories: str


agent = Agent(
    get_model(),
    system_prompt=AGENT_SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2,
)


@agent.system_prompt
def add_memories(ctx: RunContext[str]) -> str:
    return f"\nUser Memories:\n{ctx.deps.memories}"


@agent.tool
async def web_search(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    Search the web with a specific query and get a summary of the top search results.

    Args:
        ctx: The context for the agent including the HTTP client and optional Brave API key/SearXNG base url
        query: The query for the web search

    Returns:
        A summary of the web search.
        For Brave, this is a single paragraph.
        For SearXNG, this is a list of the top search results including the most relevant snippet from the page.
    """
    print("Calling web_search tool")
    return await web_search_tool(
        query, ctx.deps.http_client, ctx.deps.brave_api_key, ctx.deps.searxng_base_url
    )


@agent.tool
async def retrieve_relevant_documents(ctx: RunContext[AgentDeps], user_query: str) -> str:
    """
    Retrieve relevant document chunks based on the query with RAG.

    Args:
        ctx: The context including the Supabase client and OpenAI client
        user_query: The user's question or query

    Returns:
        A formatted string containing the top 4 most relevant documents chunks
    """
    print("Calling retrieve_relevant_documents tool")
    return await retrieve_relevant_documents_tool(
        ctx.deps.supabase, ctx.deps.embedding_client, user_query
    )


@agent.tool
async def list_documents(ctx: RunContext[AgentDeps]) -> list[str]:
    """
    Retrieve a list of all available documents.

    Returns:
        List[str]: List of documents including their metadata (URL/path, schema if applicable, etc.)
    """
    print("Calling list_documents tool")
    return await list_documents_tool(ctx.deps.supabase)


@agent.tool
async def get_document_content(ctx: RunContext[AgentDeps], document_id: str) -> str:
    """
    Retrieve the full content of a specific document by combining all its chunks.

    Args:
        ctx: The context including the Supabase client
        document_id: The ID (or file path) of the document to retrieve

    Returns:
        str: The full content of the document with all chunks combined in order
    """
    print("Calling get_document_content tool")
    return await get_document_content_tool(ctx.deps.supabase, document_id)


@agent.tool
async def execute_sql_query(ctx: RunContext[AgentDeps], sql_query: str) -> str:
    """
    Run a SQL query - use this to query from the document_rows table once you know the file ID you are querying.
    dataset_id is the file_id and you are always using the row_data for filtering, which is a jsonb field that has
    all the keys from the file schema given in the document_metadata table.

    Never use a placeholder file ID. Always use the list_documents tool first to get the file ID.

    Example query:

    SELECT AVG((row_data->>'revenue')::numeric)
    FROM document_rows
    WHERE dataset_id = '123';

    Example query 2:

    SELECT
        row_data->>'category' as category,
        SUM((row_data->>'sales')::numeric) as total_sales
    FROM document_rows
    WHERE dataset_id = '123'
    GROUP BY row_data->>'category';

    Args:
        ctx: The context including the Supabase client
        sql_query: The SQL query to execute (must be read-only)

    Returns:
        str: The results of the SQL query in JSON format
    """
    print(f"Calling execute_sql_query tool with SQL: {sql_query }")
    return await execute_sql_query_tool(ctx.deps.supabase, sql_query)


@agent.tool
async def image_analysis(ctx: RunContext[AgentDeps], document_id: str, query: str) -> str:
    """
    Analyzes an image based on the document ID of the image provided.
    This function pulls the binary of the image from the knowledge base
    and passes that into a subagent with a vision LLM
    Before calling this tool, call list_documents to see the images available
    and to get the exact document ID for the image.

    Args:
        ctx: The context including the Supabase client
        document_id: The ID (or file path) of the image to analyze
        query: What to extract from the image analysis

    Returns:
        str: An analysis of the image based on the query
    """
    print("Calling image_analysis tool")
    return await image_analysis_tool(ctx.deps.supabase, document_id, query)


# Using the MCP server instead for code execution, but you can use this simple version
# if you don't want to use MCP for whatever reason! Just uncomment the line below:
@agent.tool
async def execute_code(ctx: RunContext[AgentDeps], code: str) -> str:
    """
    Executes a given Python code string in a protected environment.
    Use print to output anything that you need as a result of executing the code.

    Args:
        code: Python code to execute

    Returns:
        str: Anything printed out to standard output with the print command
    """
    print(f"executing code: {code}")
    print(f"Result is: {execute_safe_code_tool(code)}")
    return execute_safe_code_tool(code)
