"""
Unit tests for document reference functionality.

Tests cover:
- DocumentReference Pydantic model validation
- extract_document_metadata function
- add_entities() with document metadata
- Backfill script components
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agentic_rag.models.document_reference import (
    DocumentReference,
    extract_document_metadata,
)


class TestDocumentReference:
    """Test suite for DocumentReference Pydantic model."""

    def test_valid_document_reference(self):
        """Test creation with valid data."""
        doc_ref = DocumentReference(
            filename="INTC_Q4_2024.pdf",
            company="INTC",
            quarter="Q4",
            year=2024,
            mention_count=1,
        )
        assert doc_ref.filename == "INTC_Q4_2024.pdf"
        assert doc_ref.company == "INTC"
        assert doc_ref.quarter == "Q4"
        assert doc_ref.year == 2024
        assert doc_ref.mention_count == 1

    def test_minimal_document_reference(self):
        """Test creation with only required fields."""
        doc_ref = DocumentReference(filename="test.pdf")
        assert doc_ref.filename == "test.pdf"
        assert doc_ref.company is None
        assert doc_ref.quarter is None
        assert doc_ref.year is None
        assert doc_ref.mention_count == 1

    def test_filename_sanitization_unicode(self):
        """Test that Unicode characters are removed from filename."""
        doc_ref = DocumentReference(filename="test_file.pdf")
        assert doc_ref.filename == "test_file.pdf"
        # Emoji would be stripped
        doc_ref2 = DocumentReference(filename="test.pdf")
        assert doc_ref2.filename == "test.pdf"

    def test_filename_sanitization_special_chars(self):
        """Test that special characters are replaced in filename."""
        doc_ref = DocumentReference(filename='test<>:"/\\|?*.pdf')
        assert "<" not in doc_ref.filename
        assert ">" not in doc_ref.filename
        assert ":" not in doc_ref.filename

    def test_quarter_validation_valid(self):
        """Test valid quarter values."""
        for q in ["Q1", "Q2", "Q3", "Q4", "q1", "q2", "q3", "q4"]:
            doc_ref = DocumentReference(filename="test.pdf", quarter=q)
            assert doc_ref.quarter in ["Q1", "Q2", "Q3", "Q4"]

    def test_quarter_validation_invalid(self):
        """Test invalid quarter values are set to None."""
        doc_ref = DocumentReference(filename="test.pdf", quarter="Q5")
        assert doc_ref.quarter is None

        doc_ref2 = DocumentReference(filename="test.pdf", quarter="invalid")
        assert doc_ref2.quarter is None

    def test_year_validation_valid(self):
        """Test valid year values."""
        doc_ref = DocumentReference(filename="test.pdf", year=2024)
        assert doc_ref.year == 2024

        doc_ref2 = DocumentReference(filename="test.pdf", year=1999)
        assert doc_ref2.year == 1999

    def test_year_validation_invalid(self):
        """Test invalid year values are set to None."""
        doc_ref = DocumentReference(filename="test.pdf", year=1800)
        assert doc_ref.year is None

        doc_ref2 = DocumentReference(filename="test.pdf", year=2200)
        assert doc_ref2.year is None

    def test_mention_count_minimum(self):
        """Test that mention_count must be at least 1."""
        with pytest.raises(ValueError):
            DocumentReference(filename="test.pdf", mention_count=0)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        doc_ref = DocumentReference(
            filename="INTC_Q4_2024.pdf",
            company="INTC",
            quarter="Q4",
            year=2024,
            mention_count=5,
        )
        result = doc_ref.to_dict()
        assert result == {
            "filename": "INTC_Q4_2024.pdf",
            "company": "INTC",
            "quarter": "Q4",
            "year": 2024,
            "mention_count": 5,
        }

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "filename": "test.pdf",
            "company": "AMD",
            "quarter": "Q1",
            "year": 2023,
            "mention_count": 3,
        }
        doc_ref = DocumentReference.from_dict(data)
        assert doc_ref.filename == "test.pdf"
        assert doc_ref.company == "AMD"
        assert doc_ref.quarter == "Q1"
        assert doc_ref.year == 2023
        assert doc_ref.mention_count == 3

    def test_from_dict_missing_fields(self):
        """Test creation from dict with missing optional fields."""
        data = {"filename": "minimal.pdf"}
        doc_ref = DocumentReference.from_dict(data)
        assert doc_ref.filename == "minimal.pdf"
        assert doc_ref.company is None
        assert doc_ref.mention_count == 1

    def test_equality_based_on_filename(self):
        """Test that equality is based on filename."""
        ref1 = DocumentReference(filename="test.pdf", company="A")
        ref2 = DocumentReference(filename="test.pdf", company="B")
        ref3 = DocumentReference(filename="other.pdf", company="A")

        assert ref1 == ref2
        assert ref1 != ref3

    def test_hash_based_on_filename(self):
        """Test that hash is based on filename for set operations."""
        ref1 = DocumentReference(filename="test.pdf", company="A")
        ref2 = DocumentReference(filename="test.pdf", company="B")

        # Should be in same bucket
        assert hash(ref1) == hash(ref2)

        # Set should deduplicate
        ref_set = {ref1, ref2}
        assert len(ref_set) == 1


class TestExtractDocumentMetadata:
    """Test suite for extract_document_metadata function."""

    def test_extract_from_standard_filename(self):
        """Test extraction from COMPANY_QUARTER_YEAR.pdf pattern."""
        result = extract_document_metadata("INTC_Q4_2024.pdf")
        assert result.filename == "INTC_Q4_2024.pdf"
        assert result.company == "INTC"
        assert result.quarter == "Q4"
        assert result.year == 2024

    def test_extract_from_path(self):
        """Test extraction from full path."""
        result = extract_document_metadata("/path/to/docs/AMD_Q2_2023.pdf")
        assert result.filename == "AMD_Q2_2023.pdf"
        assert result.company == "AMD"
        assert result.quarter == "Q2"
        assert result.year == 2023

    def test_extract_from_windows_path(self):
        """Test extraction from Windows-style path."""
        result = extract_document_metadata("C:\\Documents\\NVDA_Q1_2024.pdf")
        assert result.filename == "NVDA_Q1_2024.pdf"
        assert result.company == "NVDA"

    def test_extract_with_metadata_override(self):
        """Test that metadata dict values override filename extraction."""
        metadata = {"company": "OVERRIDE", "quarter": "Q3", "year": 2025}
        result = extract_document_metadata("INTC_Q4_2024.pdf", metadata=metadata)
        assert result.company == "OVERRIDE"
        assert result.quarter == "Q3"
        assert result.year == 2025

    def test_extract_without_quarter(self):
        """Test extraction when quarter is not in filename."""
        result = extract_document_metadata("INTC_annual_2024.pdf")
        assert result.filename == "INTC_annual_2024.pdf"
        assert result.company == "INTC"
        assert result.quarter is None
        assert result.year == 2024

    def test_extract_without_company(self):
        """Test extraction when company is not recognizable."""
        result = extract_document_metadata("quarterly_report_Q4_2024.pdf")
        assert result.filename == "quarterly_report_Q4_2024.pdf"
        assert result.company is None
        assert result.quarter == "Q4"
        assert result.year == 2024

    def test_extract_minimal_filename(self):
        """Test extraction from filename with minimal info."""
        result = extract_document_metadata("document.pdf")
        assert result.filename == "document.pdf"
        assert result.company is None
        assert result.quarter is None
        assert result.year is None

    def test_extract_year_string_in_metadata(self):
        """Test that year string in metadata is converted to int."""
        metadata = {"year": "2024"}
        result = extract_document_metadata("test.pdf", metadata=metadata)
        assert result.year == 2024

    def test_mention_count_default(self):
        """Test that mention_count defaults to 1."""
        result = extract_document_metadata("test.pdf")
        assert result.mention_count == 1


class TestAddEntitiesWithDocumentMetadata:
    """Test suite for add_entities() with document metadata."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock connection manager."""
        manager = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"entity_id": "entity_123"})
        mock_session.run = AsyncMock(return_value=mock_result)

        # Make get_neo4j_session an async context manager
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        manager.get_neo4j_session = MagicMock(return_value=mock_session)

        return manager

    @pytest.mark.asyncio
    async def test_add_entities_with_document_metadata(self, mock_connection_manager):
        """Test that document metadata is passed to Cypher query."""
        from src.agentic_rag.storage.neo4j_store import Neo4jStore

        store = Neo4jStore(mock_connection_manager)
        doc_ref = DocumentReference(
            filename="INTC_Q4_2024.pdf",
            company="INTC",
            quarter="Q4",
            year=2024,
        )

        entities = [{"name": "Intel", "type": "COMPANY"}]
        result = await store.add_entities(
            entities=entities,
            source_chunk_id="chunk_123",
            document_metadata=doc_ref,
        )

        assert len(result) == 1
        # Verify the session.run was called with doc_ref parameter
        mock_session = mock_connection_manager.get_neo4j_session().__aenter__.return_value
        call_kwargs = mock_session.run.call_args[1]
        assert call_kwargs["doc_ref"] is not None
        assert call_kwargs["doc_ref"]["filename"] == "INTC_Q4_2024.pdf"

    @pytest.mark.asyncio
    async def test_add_entities_without_document_metadata(self, mock_connection_manager):
        """Test backward compatibility without document metadata."""
        from src.agentic_rag.storage.neo4j_store import Neo4jStore

        store = Neo4jStore(mock_connection_manager)

        entities = [{"name": "Intel", "type": "COMPANY"}]
        result = await store.add_entities(
            entities=entities,
            source_chunk_id="chunk_123",
        )

        assert len(result) == 1
        # Verify doc_ref is None
        mock_session = mock_connection_manager.get_neo4j_session().__aenter__.return_value
        call_kwargs = mock_session.run.call_args[1]
        assert call_kwargs["doc_ref"] is None

    @pytest.mark.asyncio
    async def test_add_entities_handles_malformed_metadata(self, mock_connection_manager):
        """Test graceful handling of malformed document metadata."""
        from src.agentic_rag.storage.neo4j_store import Neo4jStore

        store = Neo4jStore(mock_connection_manager)

        # Create a mock DocumentReference that raises on to_dict
        bad_ref = MagicMock()
        bad_ref.to_dict = MagicMock(side_effect=Exception("Conversion failed"))

        entities = [{"name": "Test", "type": "TEST"}]
        # Should not raise, should gracefully degrade
        result = await store.add_entities(
            entities=entities,
            source_chunk_id="chunk_123",
            document_metadata=bad_ref,
        )

        assert len(result) == 1


class TestBackfillScriptComponents:
    """Test suite for backfill script components."""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_first_try(self):
        """Test retry succeeds on first attempt."""
        import sys
        from pathlib import Path

        # Import from scripts
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_document_refs import retry_with_backoff

        async def successful_func():
            return "success"

        result = await retry_with_backoff(successful_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_after_retry(self):
        """Test retry succeeds after initial failure."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_document_refs import retry_with_backoff

        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await retry_with_backoff(
            fail_then_succeed,
            max_retries=3,
            initial_backoff=0.01,  # Fast for tests
        )
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_backoff_exhausted(self):
        """Test retry raises after all attempts exhausted."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_document_refs import retry_with_backoff

        async def always_fail():
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError, match="Persistent failure"):
            await retry_with_backoff(
                always_fail,
                max_retries=2,
                initial_backoff=0.01,
            )

    def test_document_ref_backfill_initialization(self):
        """Test DocumentRefBackfill class initialization."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_document_refs import DocumentRefBackfill

        mock_manager = MagicMock()
        backfill = DocumentRefBackfill(
            connection_manager=mock_manager,
            batch_size=50,
            dry_run=True,
        )

        assert backfill.batch_size == 50
        assert backfill.dry_run is True
        assert backfill.stats["total_entities"] == 0

    def test_document_ref_backfill_stats_tracking(self):
        """Test that backfill stats are properly initialized."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_document_refs import DocumentRefBackfill

        mock_manager = MagicMock()
        backfill = DocumentRefBackfill(connection_manager=mock_manager)

        expected_keys = [
            "total_entities",
            "entities_processed",
            "entities_updated",
            "entities_skipped",
            "errors",
        ]
        for key in expected_keys:
            assert key in backfill.stats
            assert backfill.stats[key] == 0


class TestDocumentReferenceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_filename_becomes_unknown(self):
        """Test that empty filename after sanitization becomes 'unknown'."""
        # Non-ASCII only filename would be stripped to empty
        doc_ref = DocumentReference(filename="   ")
        assert doc_ref.filename == "unknown"

    def test_very_long_filename(self):
        """Test handling of very long filenames."""
        long_name = "a" * 500 + ".pdf"
        doc_ref = DocumentReference(filename=long_name)
        assert len(doc_ref.filename) > 0

    def test_mention_count_large_value(self):
        """Test handling of large mention counts."""
        doc_ref = DocumentReference(filename="test.pdf", mention_count=999999)
        assert doc_ref.mention_count == 999999

    def test_extract_year_from_various_formats(self):
        """Test year extraction from different filename formats."""
        test_cases = [
            ("report_2024.pdf", 2024),
            ("2023_annual.pdf", 2023),
            ("Q4-2022-report.pdf", 2022),
            ("document_19990101.pdf", 1999),
        ]
        for filename, expected_year in test_cases:
            result = extract_document_metadata(filename)
            assert result.year == expected_year, f"Failed for {filename}"

    def test_extract_quarter_case_insensitive(self):
        """Test that quarter extraction is case insensitive."""
        test_cases = [
            ("report_q1.pdf", "Q1"),
            ("report_Q2.pdf", "Q2"),
            ("REPORT_Q3.PDF", "Q3"),
            ("Report_q4.Pdf", "Q4"),
        ]
        for filename, expected_quarter in test_cases:
            result = extract_document_metadata(filename)
            assert result.quarter == expected_quarter, f"Failed for {filename}"
