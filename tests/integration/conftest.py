"""
Integration test fixtures and configuration.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.agentic_rag.storage.graphiti_client import GraphitiClient
from src.agentic_rag.storage.neo4j_store import Neo4jStore
from src.agentic_rag.storage.postgres_store import PostgresStore
from src.config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Get test settings from environment."""
    import os

    settings = get_settings()

    # Check if integration tests are explicitly enabled
    enable_integration = os.getenv("ENABLE_INTEGRATION_TESTS", "false").lower() == "true"

    # Verify test database is configured OR integration tests are explicitly enabled
    if not enable_integration and "test" not in settings.supabase_url.lower():
        pytest.skip(
            "Integration tests disabled. Set ENABLE_INTEGRATION_TESTS=true to run "
            "integration tests (WARNING: will use configured database)"
        )

    return settings


@pytest_asyncio.fixture(scope="session")
async def connection_manager(
    test_settings,
) -> AsyncGenerator[ConnectionManager, None]:
    """Create connection manager for tests."""
    manager = ConnectionManager()

    # Initialize connections
    await manager.initialize()

    yield manager

    # Cleanup
    await manager.close_all()


@pytest_asyncio.fixture
async def postgres_store(
    connection_manager,
) -> AsyncGenerator[PostgresStore, None]:
    """Create PostgreSQL store for tests with cleanup."""
    store = PostgresStore(connection_manager)

    # Track created document IDs for cleanup
    created_docs = []

    # Monkey patch store_document to track IDs
    original_store_document = store.store_document

    async def tracking_store_document(*args, **kwargs):
        doc_id = await original_store_document(*args, **kwargs)
        created_docs.append(doc_id)
        return doc_id

    store.store_document = tracking_store_document

    yield store

    # Cleanup test data
    try:
        for doc_id in created_docs:
            await store.delete_document(doc_id, hard_delete=True)
    except Exception as e:
        print(f"Cleanup error: {e}")


@pytest_asyncio.fixture
async def neo4j_store(
    connection_manager,
) -> AsyncGenerator[Neo4jStore, None]:
    """Create Neo4j store for tests with cleanup."""
    store = Neo4jStore(connection_manager)

    # Track test data for cleanup
    test_marker = f"test_{uuid.uuid4().hex[:8]}"

    yield store

    # Cleanup test nodes (nodes with test marker in metadata)
    try:
        async with connection_manager.get_neo4j_session() as session:
            await session.run(
                """
                MATCH (n)
                WHERE n.test_marker = $marker
                DETACH DELETE n
                """,
                marker=test_marker,
            )
    except Exception as e:
        print(f"Neo4j cleanup error: {e}")


@pytest_asyncio.fixture
async def graphiti_client(
    connection_manager,
) -> AsyncGenerator[GraphitiClient, None]:
    """Create Graphiti client for tests."""
    settings = get_settings()

    if not all([settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password]):
        pytest.skip("Neo4j credentials not configured")

    client = GraphitiClient(connection_manager)

    # Initialize if needed
    try:
        await client.initialize()
    except Exception:
        pytest.skip("Could not initialize Graphiti client")

    yield client

    # Cleanup handled by neo4j_store fixture


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "title": "Test Document",
        "content": (
            "This is test content for integration testing. "
            "It contains information about machine learning and AI. "
            "Machine learning is a subset of artificial intelligence. "
            "Deep learning uses neural networks with multiple layers."
        ),
        "source": "test.txt",
        "metadata": {"category": "test", "language": "en"},
    }


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        {
            "content": "This is test content for integration testing.",
            "embedding_1536": [0.1] * 1536,
            "embedding_768": [0.1] * 768,
            "metadata": {"chunk_type": "text"},
            "token_count": 10,
        },
        {
            "content": "It contains information about machine learning and AI.",
            "embedding_1536": [0.2] * 1536,
            "embedding_768": [0.2] * 768,
            "metadata": {"chunk_type": "text"},
            "token_count": 12,
        },
        {
            "content": "Machine learning is a subset of artificial intelligence.",
            "embedding_1536": [0.3] * 1536,
            "embedding_768": [0.3] * 768,
            "metadata": {"chunk_type": "text"},
            "token_count": 11,
        },
    ]


@pytest_asyncio.fixture
async def sample_document_with_chunks(postgres_store, sample_document, sample_chunks):
    """Create a sample document with chunks in the database."""
    # Store document
    doc_id = await postgres_store.store_document(
        title=sample_document["title"],
        source=sample_document["source"],
        content=sample_document["content"],
        metadata=sample_document["metadata"],
    )

    # Store chunks
    chunk_ids = await postgres_store.store_chunks(doc_id, sample_chunks)

    return {
        "document_id": doc_id,
        "chunk_ids": chunk_ids,
        "document": sample_document,
        "chunks": sample_chunks,
    }
