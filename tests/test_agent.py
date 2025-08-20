import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock, call
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerHTTP
from dataclasses import dataclass

# Mock environment variables before importing modules that use them
with patch.dict(os.environ, {
    'LLM_PROVIDER': 'openai',
    'LLM_BASE_URL': 'https://api.openai.com/v1',
    'LLM_API_KEY': 'test-api-key',
    'LLM_CHOICE': 'gpt-4o-mini',
    'VISION_LLM_CHOICE': 'gpt-4o-mini',
    'EMBEDDING_PROVIDER': 'openai',
    'EMBEDDING_BASE_URL': 'https://api.openai.com/v1',
    'EMBEDDING_API_KEY': 'test-api-key',
    'EMBEDDING_MODEL_CHOICE': 'text-embedding-3-small',
    'SUPABASE_URL': 'https://test-supabase-url.com',
    'SUPABASE_SERVICE_KEY': 'test-supabase-key',
    'BRAVE_API_KEY': 'test-brave-key',
    'SEARXNG_BASE_URL': 'http://test-searxng-url.com'
}):
    # Add src directory to path to import the agent module
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
    from agent.agent import agent, AgentDeps, get_model, add_memories, web_search, retrieve_relevant_documents, list_documents, get_document_content, execute_sql_query, image_analysis, execute_code
    from agent.prompt import AGENT_SYSTEM_PROMPT
    import tools.web_search
    import tools.rag
    import tools.sql_query
    import tools.image_analysis
    import tools.code_execution


class TestAgentInitialization:
    def test_get_model(self):
        model = get_model()
        assert model.model_name == 'gpt-4o-mini'
        assert model.provider.base_url == 'https://api.openai.com/v1'
        assert model.provider.api_key == 'test-api-key'

    def test_agent_creation(self):
        assert isinstance(agent, Agent)
        assert agent.system_prompt == AGENT_SYSTEM_PROMPT
        assert agent.deps_type == AgentDeps
        assert agent.retries == 2

class TestAgentSystemPrompts:
    def test_add_memories_system_prompt(self):
        mock_deps = MagicMock(spec=AgentDeps)
        mock_deps.memories = "Memory 1\nMemory 2"
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = mock_deps
        
        prompt = add_memories(mock_ctx)
        assert prompt == "User Memories:\nMemory 1\nMemory 2"

class TestAgentTools:
    @pytest.mark.asyncio
    @patch('tools.web_search.web_search_tool')
    async def test_web_search_tool_call(self, mock_web_search_tool):
        mock_deps = MagicMock(spec=AgentDeps)
        mock_deps.http_client = AsyncMock()
        mock_deps.brave_api_key = "test-brave-key"
        mock_deps.searxng_base_url = "test-searxng-url"
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = mock_deps
        
        mock_web_search_tool.return_value = "Web search result"
        
        result = await web_search(mock_ctx, "test query")
        
        mock_web_search_tool.assert_called_once_with(
            "test query", 
            mock_deps.http_client, 
            "test-brave-key", 
            "test-searxng-url"
        )
        assert result == "Web search result"

    @pytest.mark.asyncio
    @patch('tools.rag.retrieve_relevant_documents_tool')
    async def test_retrieve_relevant_documents_tool_call(self, mock_retrieve_relevant_documents_tool):
        mock_deps = MagicMock(spec=AgentDeps)
        mock_deps.supabase = MagicMock()
        mock_deps.embedding_client = AsyncMock()
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = mock_deps
        
        mock_retrieve_relevant_documents_tool.return_value = "Relevant documents"
        
        result = await retrieve_relevant_documents(mock_ctx, "user query")
        
        mock_retrieve_relevant_documents_tool.assert_called_once_with(
            mock_deps.supabase, 
            mock_deps.embedding_client, 
            "user query"
        )
        assert result == "Relevant documents"

    @pytest.mark.asyncio
    @patch('tools.rag.list_documents_tool')
    async def test_list_documents_tool_call(self, mock_list_documents_tool):
        mock_deps = MagicMock(spec=AgentDeps)
        mock_deps.supabase = MagicMock()
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = mock_deps
        
        mock_list_documents_tool.return_value = ["doc1", "doc2"]
        
        result = await list_documents(mock_ctx)
        
        mock_list_documents_tool.assert_called_once_with(mock_deps.supabase)
        assert result == ["doc1", "doc2"]

    @pytest.mark.asyncio
    @patch('tools.rag.get_document_content_tool')
    async def test_get_document_content_tool_call(self, mock_get_document_content_tool):
        mock_deps = MagicMock(spec=AgentDeps)
        mock_deps.supabase = MagicMock()
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = mock_deps
        
        mock_get_document_content_tool.return_value = "Document content"
        
        result = await get_document_content(mock_ctx, "doc_id")
        
        mock_get_document_content_tool.assert_called_once_with(mock_deps.supabase, "doc_id")
        assert result == "Document content"

    @pytest.mark.asyncio
    @patch('tools.sql_query.execute_sql_query_tool')
    async def test_execute_sql_query_tool_call(self, mock_execute_sql_query_tool):
        mock_deps = MagicMock(spec=AgentDeps)
        mock_deps.supabase = MagicMock()
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = mock_deps
        
        mock_execute_sql_query_tool.return_value = "SQL query result"
        
        result = await execute_sql_query(mock_ctx, "SELECT * FROM users;")
        
        mock_execute_sql_query_tool.assert_called_once_with(mock_deps.supabase, "SELECT * FROM users;")
        assert result == "SQL query result"

    @pytest.mark.asyncio
    @patch('tools.image_analysis.image_analysis_tool')
    async def test_image_analysis_tool_call(self, mock_image_analysis_tool):
        mock_deps = MagicMock(spec=AgentDeps)
        mock_deps.supabase = MagicMock()
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = mock_deps
        
        mock_image_analysis_tool.return_value = "Image analysis result"
        
        result = await image_analysis(mock_ctx, "image_id", "describe image")
        
        mock_image_analysis_tool.assert_called_once_with(mock_deps.supabase, "image_id", "describe image")
        assert result == "Image analysis result"

    @pytest.mark.asyncio
    @patch('tools.code_execution.execute_safe_code_tool')
    async def test_execute_code_tool_call(self, mock_execute_safe_code_tool):
        mock_deps = MagicMock(spec=AgentDeps)
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = mock_deps
        
        mock_execute_safe_code_tool.return_value = "Code execution result"
        
        result = await execute_code(mock_ctx, "print('hello')")
        
        mock_execute_safe_code_tool.assert_called_once_with("print('hello')")
        assert result == "Code execution result"
