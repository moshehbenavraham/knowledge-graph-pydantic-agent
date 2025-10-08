import os
import sys
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

# Mock environment variables before importing modules that use them
with patch.dict(
    os.environ,
    {
        "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
    },
):
    # Add src directory to path to import the tools module
    sys.path.append(str(Path(__file__).parent.parent.resolve() / "src"))
    from tools.rag import (
        get_document_content_tool,
        get_embedding,
        list_documents_tool,
        retrieve_relevant_documents_tool,
    )


# Global reference to the mocked OpenAI client
openai_client_mock = MagicMock()


class TestEmbeddingTools:
    @pytest.mark.asyncio
    async def test_get_embedding_success(self):
        # Mock embedding client and response
        mock_client = AsyncMock()
        mock_embeddings = AsyncMock()
        mock_client.embeddings = mock_embeddings

        # Setup mock response
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = [0.1, 0.2, 0.3]
        mock_response = MagicMock()
        mock_response.data = [mock_embedding_data]
        mock_embeddings.create.return_value = mock_response

        # Test the function
        with patch("tools.rag.embedding_model", "text-embedding-3-small"):
            result = await get_embedding("test text", mock_client)

        # Verify the embedding request was made correctly
        mock_embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input="test text"
        )

        # Verify the result
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_get_embedding_exception(self):
        # Mock embedding client that raises an exception
        mock_client = AsyncMock()
        mock_embeddings = AsyncMock()
        mock_client.embeddings = mock_embeddings
        mock_embeddings.create.side_effect = Exception("Test exception")

        # Test the function
        with (
            patch("tools.rag.embedding_model", "text-embedding-3-small"),
            patch("builtins.print") as mock_print,
        ):
            result = await get_embedding("test text", mock_client)

        # Verify the exception was handled
        mock_print.assert_called_once_with("Error getting embedding: Test exception")

        # Verify a zero vector was returned
        assert len(result) == 1536
        assert all(x == 0 for x in result)


class TestDocumentTools:
    @pytest.mark.asyncio
    @patch("tools.rag.get_embedding")
    async def test_retrieve_relevant_documents_tool_success(self, mock_get_embedding):
        # Mock embedding function
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]

        # Mock Supabase client and response
        mock_supabase = MagicMock()
        mock_rpc = MagicMock()
        mock_supabase.rpc.return_value = mock_rpc
        mock_execute = MagicMock()
        mock_rpc.execute.return_value = mock_execute

        # Setup mock data
        mock_execute.data = [
            {
                "content": "Document content 1",
                "metadata": {"file_id": "doc1", "file_title": "Document 1"},
            },
            {
                "content": "Document content 2",
                "metadata": {"file_id": "doc2", "file_title": "Document 2"},
            },
        ]

        # Create a specific mock client to pass to the function
        mock_embedding_client = AsyncMock()

        # Test the function
        result = await retrieve_relevant_documents_tool(
            mock_supabase, mock_embedding_client, "test query"
        )

        # Verify embedding was requested with the right parameters
        # Use ANY for the client parameter since we can't directly compare AsyncMock instances
        mock_get_embedding.assert_called_once_with("test query", ANY)

        # Verify Supabase RPC was called correctly
        mock_supabase.rpc.assert_called_once_with(
            "match_documents", {"query_embedding": [0.1, 0.2, 0.3], "match_count": 4}
        )

        # Verify the result contains document information
        assert "Document ID: doc1" in result
        assert "Document Tilte: Document 1" in result
        assert "Document content 1" in result
        assert "Document ID: doc2" in result
        assert "Document Tilte: Document 2" in result
        assert "Document content 2" in result

    @pytest.mark.asyncio
    @patch("tools.rag.get_embedding")
    async def test_retrieve_relevant_documents_tool_no_results(self, mock_get_embedding):
        # Mock embedding function
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]

        # Mock Supabase client with no results
        mock_supabase = MagicMock()
        mock_rpc = MagicMock()
        mock_supabase.rpc.return_value = mock_rpc
        mock_execute = MagicMock()
        mock_rpc.execute.return_value = mock_execute
        mock_execute.data = []

        # Test the function
        result = await retrieve_relevant_documents_tool(mock_supabase, AsyncMock(), "test query")

        # Verify the result for no documents
        assert result == "No relevant documents found."

    @pytest.mark.asyncio
    @patch("tools.rag.get_embedding")
    async def test_retrieve_relevant_documents_tool_exception(self, mock_get_embedding):
        # Mock embedding function that raises an exception
        mock_get_embedding.side_effect = Exception("Test exception")

        # Test the function
        with patch("builtins.print") as mock_print:
            result = await retrieve_relevant_documents_tool(MagicMock(), AsyncMock(), "test query")

        # Verify the exception was handled
        mock_print.assert_called_once_with("Error retrieving documents: Test exception")
        assert "Error retrieving documents: Test exception" in result

    @pytest.mark.asyncio
    async def test_list_documents_tool_success(self):
        # Mock Supabase client and response
        mock_supabase = MagicMock()
        mock_from = MagicMock()
        mock_supabase.from_.return_value = mock_from
        mock_select = MagicMock()
        mock_from.select.return_value = mock_select
        mock_execute = MagicMock()
        mock_select.execute.return_value = mock_execute

        # Setup mock data
        mock_execute.data = [
            {
                "id": "doc1",
                "title": "Document 1",
                "schema": "schema1",
                "url": "https://example.com/doc1",
            },
            {
                "id": "doc2",
                "title": "Document 2",
                "schema": "schema2",
                "url": "https://example.com/doc2",
            },
        ]

        # Test the function
        result = await list_documents_tool(mock_supabase)

        # Verify Supabase query was called correctly
        mock_supabase.from_.assert_called_once_with("document_metadata")
        mock_from.select.assert_called_once_with("id, title, schema, url")

        # Verify the result contains document information
        assert str(mock_execute.data) == result

    @pytest.mark.asyncio
    async def test_list_documents_tool_exception(self):
        # Mock Supabase client that raises an exception
        mock_supabase = MagicMock()
        mock_supabase.from_.side_effect = Exception("Test exception")

        # Test the function
        with patch("builtins.print") as mock_print:
            result = await list_documents_tool(mock_supabase)

        # Verify the exception was handled
        mock_print.assert_called_once_with("Error retrieving documents: Test exception")
        assert result == str([])

    @pytest.mark.asyncio
    async def test_get_document_content_tool_success(self):
        # Mock Supabase client and response
        mock_supabase = MagicMock()
        mock_from = MagicMock()
        mock_supabase.from_.return_value = mock_from
        mock_select = MagicMock()
        mock_from.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_order = MagicMock()
        mock_eq.order.return_value = mock_order
        mock_execute = MagicMock()
        mock_order.execute.return_value = mock_execute

        # Setup mock data
        mock_execute.data = [
            {
                "id": "chunk1",
                "content": "Document content part 1",
                "metadata": {"file_id": "doc1", "file_title": "Document 1 - Part 1"},
            },
            {
                "id": "chunk2",
                "content": "Document content part 2",
                "metadata": {"file_id": "doc1", "file_title": "Document 1 - Part 2"},
            },
        ]

        # Test the function
        result = await get_document_content_tool(mock_supabase, "doc1")

        # Verify Supabase query was called correctly
        mock_supabase.from_.assert_called_once_with("documents")
        mock_from.select.assert_called_once_with("id, content, metadata")
        mock_select.eq.assert_called_once_with("metadata->>file_id", "doc1")
        mock_eq.order.assert_called_once_with("id")

        # Verify the result contains document content
        assert "# Document 1" in result
        assert "Document content part 1" in result
        assert "Document content part 2" in result

    @pytest.mark.asyncio
    async def test_get_document_content_tool_no_content(self):
        # Mock Supabase client with no results
        mock_supabase = MagicMock()
        mock_from = MagicMock()
        mock_supabase.from_.return_value = mock_from
        mock_select = MagicMock()
        mock_from.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_order = MagicMock()
        mock_eq.order.return_value = mock_order
        mock_execute = MagicMock()
        mock_order.execute.return_value = mock_execute
        mock_execute.data = []

        # Test the function
        result = await get_document_content_tool(mock_supabase, "doc1")

        # Verify the result for no content
        assert result == "No content found for document: doc1"

    @pytest.mark.asyncio
    async def test_get_document_content_tool_exception(self):
        # Mock Supabase client that raises an exception
        mock_supabase = MagicMock()
        mock_supabase.from_.side_effect = Exception("Test exception")

        # Test the function
        with patch("builtins.print") as mock_print:
            result = await get_document_content_tool(mock_supabase, "doc1")

        # Verify the exception was handled
        mock_print.assert_called_once_with("Error retrieving document content: Test exception")
        assert "Error retrieving document content: Test exception" in result
