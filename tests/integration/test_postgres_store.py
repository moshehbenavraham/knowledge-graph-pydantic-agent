"""
Integration tests for PostgresStore with live database.
"""

import pytest


class TestPostgresStoreIntegration:
    """Integration tests for PostgresStore with live database."""

    @pytest.mark.asyncio
    async def test_document_lifecycle(self, postgres_store, sample_document):
        """Test complete document lifecycle: create, read, update, delete."""
        # Create
        doc_id = await postgres_store.store_document(
            title=sample_document["title"],
            content=sample_document["content"],
            source=sample_document["source"],
            metadata=sample_document["metadata"],
        )
        assert doc_id is not None

        # Read
        doc = await postgres_store.get_document(doc_id)
        assert doc is not None
        assert doc["title"] == sample_document["title"]
        assert doc["source"] == sample_document["source"]

        # Update
        updated = await postgres_store.update_document(doc_id, {"title": "Updated Title"})
        assert updated is True

        doc = await postgres_store.get_document(doc_id)
        assert doc["title"] == "Updated Title"

        # Delete (soft)
        await postgres_store.delete_document(doc_id, hard_delete=False)
        doc = await postgres_store.get_document(doc_id)
        assert doc is None  # Soft deleted, should not be returned

    @pytest.mark.asyncio
    async def test_list_documents_pagination(self, postgres_store, sample_document):
        """Test document listing with pagination."""
        # Create 25 test documents
        doc_ids = []
        for i in range(25):
            doc_id = await postgres_store.store_document(
                title=f"Test Doc {i}",
                content=f"Content {i}",
                source=f"test_{i}.txt",
            )
            doc_ids.append(doc_id)

        # Test pagination
        page1 = await postgres_store.list_documents(limit=10, offset=0)
        assert len(page1) == 10

        page2 = await postgres_store.list_documents(limit=10, offset=10)
        assert len(page2) == 10

        page3 = await postgres_store.list_documents(limit=10, offset=20)
        assert len(page3) >= 5  # At least 5 from our test data

        # Test count
        total = await postgres_store.count_documents()
        assert total >= 25

    @pytest.mark.asyncio
    async def test_list_documents_filtering(self, postgres_store):
        """Test document listing with source filtering."""
        # Create documents with different sources
        await postgres_store.store_document(title="PDF Doc 1", content="Content", source="doc1.pdf")
        await postgres_store.store_document(title="PDF Doc 2", content="Content", source="doc2.pdf")
        await postgres_store.store_document(title="Text Doc", content="Content", source="doc.txt")

        # Filter by PDF
        pdf_docs = await postgres_store.list_documents(source_filter="%.pdf")
        assert len(pdf_docs) >= 2
        assert all(".pdf" in doc["source"] for doc in pdf_docs)

        # Count filtered
        pdf_count = await postgres_store.count_documents(source_filter="%.pdf")
        assert pdf_count >= 2

    @pytest.mark.asyncio
    async def test_list_documents_sorting(self, postgres_store):
        """Test document listing with different sort options."""
        # Create documents
        await postgres_store.store_document(title="Alpha", content="Content", source="a.txt")
        await postgres_store.store_document(title="Zeta", content="Content", source="z.txt")

        # Sort by title ascending
        docs_asc = await postgres_store.list_documents(sort_by="title", sort_order="asc", limit=100)
        titles_asc = [doc["title"] for doc in docs_asc]
        assert titles_asc == sorted(titles_asc)

        # Sort by title descending
        docs_desc = await postgres_store.list_documents(
            sort_by="title", sort_order="desc", limit=100
        )
        titles_desc = [doc["title"] for doc in docs_desc]
        assert titles_desc == sorted(titles_desc, reverse=True)

    @pytest.mark.asyncio
    async def test_get_document_chunks(self, postgres_store, sample_document, sample_chunks):
        """Test retrieving chunks for document."""
        # Create document with chunks
        doc_id = await postgres_store.store_document(
            title="Chunked Doc", content="Test content", source="test.txt"
        )

        # Store chunks
        chunk_ids = await postgres_store.store_chunks(doc_id, sample_chunks)
        assert len(chunk_ids) == len(sample_chunks)

        # Get chunks without embeddings
        chunks = await postgres_store.get_document_chunks(doc_id, include_embeddings=False)
        assert len(chunks) == len(sample_chunks)
        assert all("embedding_1536" not in chunk for chunk in chunks)
        assert all("embedding_768" not in chunk for chunk in chunks)
        assert chunks[0]["content"] == sample_chunks[0]["content"]

        # Get chunks with embeddings
        chunks_with_emb = await postgres_store.get_document_chunks(doc_id, include_embeddings=True)
        assert len(chunks_with_emb) == len(sample_chunks)
        assert all("embedding_1536" in chunk for chunk in chunks_with_emb)

        # Count chunks
        count = await postgres_store.count_chunks(doc_id)
        assert count == len(sample_chunks)

    @pytest.mark.asyncio
    async def test_update_document_metadata(self, postgres_store, sample_document):
        """Test updating document metadata and title."""
        # Create document
        doc_id = await postgres_store.store_document(
            title=sample_document["title"],
            content=sample_document["content"],
            source=sample_document["source"],
            metadata={"key1": "value1"},
        )

        # Update title
        success = await postgres_store.update_document(doc_id, {"title": "New Title"})
        assert success is True

        doc = await postgres_store.get_document(doc_id)
        assert doc["title"] == "New Title"

        # Update metadata
        new_metadata = {"key1": "updated", "key2": "value2"}
        success = await postgres_store.update_document(doc_id, {"metadata": new_metadata})
        assert success is True

        doc = await postgres_store.get_document(doc_id)
        # Note: metadata comparison might need json parsing
        assert "key2" in str(doc["metadata"])

        # Update both
        success = await postgres_store.update_document(
            doc_id, {"title": "Final Title", "metadata": {"final": "metadata"}}
        )
        assert success is True

        doc = await postgres_store.get_document(doc_id)
        assert doc["title"] == "Final Title"

    @pytest.mark.asyncio
    async def test_update_nonexistent_document(self, postgres_store):
        """Test updating a document that doesn't exist."""
        from uuid import uuid4

        fake_id = uuid4()
        success = await postgres_store.update_document(fake_id, {"title": "Should Fail"})
        assert success is False

    @pytest.mark.asyncio
    async def test_count_chunks_empty_document(self, postgres_store):
        """Test counting chunks for document with no chunks."""
        # Create document without chunks
        doc_id = await postgres_store.store_document(
            title="Empty Doc", content="Content", source="empty.txt"
        )

        count = await postgres_store.count_chunks(doc_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_chunk_ordering(self, postgres_store, sample_chunks):
        """Test that chunks are returned in correct order."""
        # Create document
        doc_id = await postgres_store.store_document(
            title="Ordered Doc", content="Content", source="test.txt"
        )

        # Store chunks (should be indexed 0, 1, 2...)
        await postgres_store.store_chunks(doc_id, sample_chunks)

        # Get chunks
        chunks = await postgres_store.get_document_chunks(doc_id)

        # Verify ordering
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    @pytest.mark.asyncio
    async def test_search_similar(self, postgres_store, sample_document_with_chunks):
        """Test vector similarity search."""
        # Search with similar embedding
        query_embedding = [0.15] * 1536  # Between chunk 0 and 1
        results = await postgres_store.search_similar(
            query_embedding, limit=5, similarity_threshold=0.0
        )

        assert len(results) > 0
        assert "similarity" in results[0]
        assert "content" in results[0]

        # Results should be ordered by similarity
        similarities = [r["similarity"] for r in results]
        assert similarities == sorted(similarities, reverse=True)

    @pytest.mark.asyncio
    async def test_hybrid_search(self, postgres_store, sample_document_with_chunks):
        """Test hybrid search with vector and entity boosting."""
        # Search with embedding and text
        query_embedding = [0.2] * 1536
        results = await postgres_store.hybrid_search(
            query_embedding=query_embedding,
            query_text="machine learning",
            limit=5,
        )

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_get_statistics(self, postgres_store, sample_document_with_chunks):
        """Test getting database statistics."""
        stats = await postgres_store.get_statistics()

        # Verify expected keys
        assert "total_documents" in stats
        assert "total_chunks" in stats
        assert stats["total_documents"] >= 1
        assert stats["total_chunks"] >= 1

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, postgres_store, sample_document):
        """Test concurrent document operations."""
        import asyncio

        # Create multiple documents concurrently
        tasks = [
            postgres_store.store_document(
                title=f"Concurrent Doc {i}",
                content=f"Content {i}",
                source=f"test_{i}.txt",
            )
            for i in range(10)
        ]

        doc_ids = await asyncio.gather(*tasks)
        assert len(doc_ids) == 10
        assert all(doc_id is not None for doc_id in doc_ids)

        # Read them back concurrently
        read_tasks = [postgres_store.get_document(doc_id) for doc_id in doc_ids]
        docs = await asyncio.gather(*read_tasks)
        assert len(docs) == 10
        assert all(doc is not None for doc in docs)
