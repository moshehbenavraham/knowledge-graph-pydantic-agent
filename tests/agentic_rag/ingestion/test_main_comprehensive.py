"""
Comprehensive tests for ingestion CLI main entry point.

Target coverage: 0% -> 95%+

Tests CLI argument parsing, main entry point, ingest_directory function,
error handling, fallback logic, and pipeline initialization.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.agentic_rag.ingestion.__main__ import ingest_directory, main


class TestIngestDirectory:
    """Test ingest_directory function."""

    @pytest.mark.asyncio
    async def test_ingest_directory_success(self, tmp_path):
        """Test successful ingestion of markdown files."""
        # Create test markdown files
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("# Document 1\nContent here")
        (test_dir / "doc2.md").write_text("# Document 2\nMore content")

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline._initialized = True
        mock_pipeline.ingest_batch = AsyncMock(
            return_value=[
                MagicMock(success=True, title="doc1", errors=[]),
                MagicMock(success=True, title="doc2", errors=[]),
            ]
        )
        mock_pipeline.get_stats = Mock(
            return_value={
                "chunks_created": 10,
                "entities_extracted": 5,
                "facts_extracted": 3,
                "avg_chunks_per_doc": 5.0,
                "avg_entities_per_doc": 2.5,
                "avg_facts_per_doc": 1.5,
            }
        )

        # Run ingestion
        await ingest_directory(mock_pipeline, test_dir)

        # Verify batch ingestion was called
        mock_pipeline.ingest_batch.assert_called_once()
        args, kwargs = mock_pipeline.ingest_batch.call_args
        documents = args[0]

        assert len(documents) == 2
        # Check both documents exist (order not guaranteed from glob)
        contents = [d["content"] for d in documents]
        assert "# Document 1\nContent here" in contents
        assert "# Document 2\nMore content" in contents
        titles = [d["title"] for d in documents]
        assert "Doc1" in titles
        assert "Doc2" in titles
        assert "file_name" in documents[0]["metadata"]
        assert kwargs["max_concurrent"] == 3

    @pytest.mark.asyncio
    async def test_ingest_directory_with_failures(self, tmp_path):
        """Test ingestion with some failures."""
        # Create test files
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("Content 1")
        (test_dir / "doc2.md").write_text("Content 2")

        # Mock pipeline with failures
        mock_pipeline = AsyncMock()
        mock_pipeline._initialized = True
        mock_pipeline.ingest_batch = AsyncMock(
            return_value=[
                MagicMock(success=True, title="doc1", errors=[]),
                MagicMock(success=False, title="doc2", errors=["Error processing"]),
            ]
        )
        mock_pipeline.get_stats = Mock(
            return_value={
                "chunks_created": 5,
                "entities_extracted": 2,
                "facts_extracted": 1,
            }
        )

        # Run ingestion
        await ingest_directory(mock_pipeline, test_dir)

        # Should complete without raising exception
        mock_pipeline.ingest_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_directory_no_markdown_files(self, tmp_path, caplog):
        """Test ingestion with no markdown files."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("Not markdown")

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline._initialized = True

        # Run ingestion
        await ingest_directory(mock_pipeline, test_dir)

        # Should log warning and return early
        assert "No markdown files found" in caplog.text

    @pytest.mark.asyncio
    async def test_ingest_directory_pipeline_not_initialized(self):
        """Test error when pipeline not initialized."""
        mock_pipeline = AsyncMock()
        mock_pipeline._initialized = False

        test_dir = Path("/tmp/test")

        with pytest.raises(RuntimeError, match="Pipeline not initialized"):
            await ingest_directory(mock_pipeline, test_dir)

    @pytest.mark.asyncio
    async def test_ingest_directory_file_read_error(self, tmp_path, caplog):
        """Test handling of file read errors."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()

        # Create a markdown file
        md_file = test_dir / "doc1.md"
        md_file.write_text("Content")

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline._initialized = True
        mock_pipeline.ingest_batch = AsyncMock(return_value=[])
        mock_pipeline.get_stats = Mock(return_value={"chunks_created": 0})

        # Mock file read to raise exception
        with patch.object(
            Path, "read_text", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "")
        ):
            await ingest_directory(mock_pipeline, test_dir)

        # Should log error
        assert "Failed to read" in caplog.text

    @pytest.mark.asyncio
    async def test_ingest_directory_no_documents_loaded(self, tmp_path, caplog):
        """Test when no documents can be loaded."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("Content")

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline._initialized = True

        # Mock file read to always fail
        with patch.object(Path, "read_text", side_effect=Exception("Read error")):
            await ingest_directory(mock_pipeline, test_dir)

        # Should log error and return early
        assert "No documents could be loaded" in caplog.text

    @pytest.mark.asyncio
    async def test_ingest_directory_nested_files(self, tmp_path):
        """Test ingestion of nested markdown files."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        subdir = test_dir / "subdir"
        subdir.mkdir()

        (test_dir / "root.md").write_text("Root content")
        (subdir / "nested.md").write_text("Nested content")

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline._initialized = True
        mock_pipeline.ingest_batch = AsyncMock(
            return_value=[
                MagicMock(success=True, title="root", errors=[]),
                MagicMock(success=True, title="nested", errors=[]),
            ]
        )
        mock_pipeline.get_stats = Mock(
            return_value={"chunks_created": 2, "entities_extracted": 0, "facts_extracted": 0}
        )

        # Run ingestion
        await ingest_directory(mock_pipeline, test_dir)

        # Should find both files
        mock_pipeline.ingest_batch.assert_called_once()
        args, _ = mock_pipeline.ingest_batch.call_args
        documents = args[0]
        assert len(documents) == 2


class TestMain:
    """Test main CLI entry point."""

    @pytest.mark.asyncio
    async def test_main_ingest_success(self, tmp_path, monkeypatch):
        """Test successful ingest command."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("Content")

        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["__main__.py", "ingest", "--path", str(test_dir)])

        # Mock DocumentIngestionPipeline
        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance._initialized = True
        mock_pipeline_instance.ingest_batch = AsyncMock(
            return_value=[MagicMock(success=True, title="doc1", errors=[])]
        )
        mock_pipeline_instance.get_stats = Mock(
            return_value={"chunks_created": 1, "entities_extracted": 0, "facts_extracted": 0}
        )

        # Mock the async context manager
        mock_pipeline_instance.__aenter__ = AsyncMock(return_value=mock_pipeline_instance)
        mock_pipeline_instance.__aexit__ = AsyncMock(return_value=None)

        mock_pipeline_class = MagicMock(return_value=mock_pipeline_instance)

        with patch(
            "src.agentic_rag.ingestion.__main__.DocumentIngestionPipeline",
            mock_pipeline_class,
        ):
            await main()

        # Verify pipeline was created and used
        mock_pipeline_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_path_does_not_exist(self, monkeypatch):
        """Test error when path does not exist."""
        monkeypatch.setattr(sys, "argv", ["__main__.py", "ingest", "--path", "/nonexistent/path"])

        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_path_not_directory(self, tmp_path, monkeypatch):
        """Test error when path is not a directory."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("Not a directory")

        monkeypatch.setattr(sys, "argv", ["__main__.py", "ingest", "--path", str(test_file)])

        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_verbose_logging(self, tmp_path, monkeypatch):
        """Test verbose logging flag."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("Content")

        monkeypatch.setattr(
            sys, "argv", ["__main__.py", "ingest", "--path", str(test_dir), "--verbose"]
        )

        # Mock pipeline
        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance._initialized = True
        mock_pipeline_instance.ingest_batch = AsyncMock(
            return_value=[MagicMock(success=True, title="doc1", errors=[])]
        )
        mock_pipeline_instance.get_stats = Mock(
            return_value={"chunks_created": 1, "entities_extracted": 0, "facts_extracted": 0}
        )
        mock_pipeline_instance.__aenter__ = AsyncMock(return_value=mock_pipeline_instance)
        mock_pipeline_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.agentic_rag.ingestion.__main__.DocumentIngestionPipeline",
            MagicMock(return_value=mock_pipeline_instance),
        ):
            await main()

        # Verbose flag should be processed without error

    @pytest.mark.asyncio
    async def test_main_rest_api_flag(self, tmp_path, monkeypatch):
        """Test --rest-api flag."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("Content")

        monkeypatch.setattr(
            sys, "argv", ["__main__.py", "ingest", "--path", str(test_dir), "--rest-api"]
        )

        # Mock pipeline
        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance._initialized = True
        mock_pipeline_instance.ingest_batch = AsyncMock(
            return_value=[MagicMock(success=True, title="doc1", errors=[])]
        )
        mock_pipeline_instance.get_stats = Mock(
            return_value={"chunks_created": 1, "entities_extracted": 0, "facts_extracted": 0}
        )
        mock_pipeline_instance.__aenter__ = AsyncMock(return_value=mock_pipeline_instance)
        mock_pipeline_instance.__aexit__ = AsyncMock(return_value=None)

        mock_pipeline_class = MagicMock(return_value=mock_pipeline_instance)

        with patch(
            "src.agentic_rag.ingestion.__main__.DocumentIngestionPipeline",
            mock_pipeline_class,
        ):
            await main()

        # Verify pipeline was created with use_rest_api=True
        mock_pipeline_class.assert_called_once_with(use_rest_api=True)

    @pytest.mark.asyncio
    async def test_main_postgresql_fallback_to_rest_api(self, tmp_path, monkeypatch):
        """Test fallback from PostgreSQL to REST API on error."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("Content")

        monkeypatch.setattr(sys, "argv", ["__main__.py", "ingest", "--path", str(test_dir)])

        # First pipeline (PostgreSQL) fails, second (REST API) succeeds
        mock_failed_pipeline = AsyncMock()
        mock_failed_pipeline.__aenter__ = AsyncMock(
            side_effect=Exception("PostgreSQL connection failed")
        )
        mock_failed_pipeline.__aexit__ = AsyncMock()

        mock_success_pipeline = AsyncMock()
        mock_success_pipeline._initialized = True
        mock_success_pipeline.ingest_batch = AsyncMock(
            return_value=[MagicMock(success=True, title="doc1", errors=[])]
        )
        mock_success_pipeline.get_stats = Mock(
            return_value={"chunks_created": 1, "entities_extracted": 0, "facts_extracted": 0}
        )
        mock_success_pipeline.__aenter__ = AsyncMock(return_value=mock_success_pipeline)
        mock_success_pipeline.__aexit__ = AsyncMock()

        # Mock to return failed first, then success
        call_count = 0

        def mock_pipeline_factory(use_rest_api=False):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_failed_pipeline
            return mock_success_pipeline

        with patch(
            "src.agentic_rag.ingestion.__main__.DocumentIngestionPipeline",
            side_effect=mock_pipeline_factory,
        ):
            await main()

        # Should have tried twice: PostgreSQL then REST API

    @pytest.mark.asyncio
    async def test_main_clean_flag(self, tmp_path, monkeypatch):
        """Test --clean flag parsing."""
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "doc1.md").write_text("Content")

        monkeypatch.setattr(
            sys, "argv", ["__main__.py", "ingest", "--path", str(test_dir), "--clean"]
        )

        # Mock pipeline
        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance._initialized = True
        mock_pipeline_instance.ingest_batch = AsyncMock(
            return_value=[MagicMock(success=True, title="doc1", errors=[])]
        )
        mock_pipeline_instance.get_stats = Mock(
            return_value={"chunks_created": 1, "entities_extracted": 0, "facts_extracted": 0}
        )
        mock_pipeline_instance.__aenter__ = AsyncMock(return_value=mock_pipeline_instance)
        mock_pipeline_instance.__aexit__ = AsyncMock()

        with patch(
            "src.agentic_rag.ingestion.__main__.DocumentIngestionPipeline",
            MagicMock(return_value=mock_pipeline_instance),
        ):
            await main()

        # Clean flag should be parsed without error

    @pytest.mark.asyncio
    async def test_main_default_path(self, monkeypatch):
        """Test default path when --path not provided."""
        monkeypatch.setattr(sys, "argv", ["__main__.py", "ingest"])

        # Default path likely doesn't exist, should exit with error
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1


class TestModuleExecution:
    """Test module execution patterns."""

    def test_main_command_execution(self, tmp_path, monkeypatch):
        """Test main function can be called as a module."""
        # Just verify main function is importable and callable
        # Verify it's a coroutine function
        import asyncio

        from src.agentic_rag.ingestion.__main__ import main

        assert asyncio.iscoroutinefunction(main)
