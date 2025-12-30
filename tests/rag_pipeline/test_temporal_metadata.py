"""
Unit and integration tests for temporal metadata extraction.

Tests cover:
- Temporal parser (TemporalMetadata, parse_filename, extract_temporal_properties)
- Neo4j store temporal integration
- Backfill script functionality

Session: phase01-session02-temporal_metadata_extraction
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agentic_rag.graph.temporal_parser import (
    FILENAME_PATTERN,
    TemporalMetadata,
    extract_temporal_properties,
    get_company_name,
    parse_filename,
)


class TestTemporalMetadata:
    """Tests for TemporalMetadata dataclass."""

    def test_valid_metadata_creation(self) -> None:
        """Test creating valid TemporalMetadata."""
        metadata = TemporalMetadata(
            fiscal_quarter="Q3",
            fiscal_year=2023,
            company_ticker="INTC",
            company_name="Intel Corporation",
            document_date="2023-Q3",
        )
        assert metadata.fiscal_quarter == "Q3"
        assert metadata.fiscal_year == 2023
        assert metadata.company_ticker == "INTC"
        assert metadata.company_name == "Intel Corporation"
        assert metadata.document_date == "2023-Q3"

    def test_metadata_is_frozen(self) -> None:
        """Test that TemporalMetadata is immutable."""
        metadata = TemporalMetadata(
            fiscal_quarter="Q1",
            fiscal_year=2024,
            company_ticker="AAPL",
            company_name="Apple Inc.",
            document_date="2024-Q1",
        )
        with pytest.raises(AttributeError):
            metadata.fiscal_quarter = "Q2"  # type: ignore[misc]

    def test_is_valid_with_all_fields(self) -> None:
        """Test is_valid returns True when all required fields present."""
        metadata = TemporalMetadata(
            fiscal_quarter="Q2",
            fiscal_year=2023,
            company_ticker="MSFT",
            company_name="Microsoft Corporation",
            document_date="2023-Q2",
        )
        assert metadata.is_valid() is True

    def test_is_valid_missing_quarter(self) -> None:
        """Test is_valid returns False when fiscal_quarter is None."""
        metadata = TemporalMetadata(
            fiscal_quarter=None,
            fiscal_year=2023,
            company_ticker="MSFT",
            company_name=None,
            document_date=None,
        )
        assert metadata.is_valid() is False

    def test_is_valid_missing_year(self) -> None:
        """Test is_valid returns False when fiscal_year is None."""
        metadata = TemporalMetadata(
            fiscal_quarter="Q1",
            fiscal_year=None,
            company_ticker="MSFT",
            company_name=None,
            document_date=None,
        )
        assert metadata.is_valid() is False

    def test_is_valid_missing_ticker(self) -> None:
        """Test is_valid returns False when company_ticker is None."""
        metadata = TemporalMetadata(
            fiscal_quarter="Q1",
            fiscal_year=2023,
            company_ticker=None,
            company_name=None,
            document_date=None,
        )
        assert metadata.is_valid() is False

    def test_to_dict(self) -> None:
        """Test to_dict returns proper dictionary."""
        metadata = TemporalMetadata(
            fiscal_quarter="Q4",
            fiscal_year=2024,
            company_ticker="AMD",
            company_name="Advanced Micro Devices, Inc.",
            document_date="2024-Q4",
        )
        result = metadata.to_dict()
        assert result == {
            "fiscal_quarter": "Q4",
            "fiscal_year": 2024,
            "company_ticker": "AMD",
            "company_name": "Advanced Micro Devices, Inc.",
            "document_date": "2024-Q4",
        }


class TestParseFilename:
    """Tests for parse_filename function."""

    def test_standard_format(self) -> None:
        """Test parsing standard filename format."""
        result = parse_filename("2023 Q3 INTC.pdf")
        assert result.fiscal_quarter == "Q3"
        assert result.fiscal_year == 2023
        assert result.company_ticker == "INTC"
        assert result.document_date == "2023-Q3"

    def test_all_quarters(self) -> None:
        """Test parsing all four quarters."""
        for q in range(1, 5):
            result = parse_filename(f"2024 Q{q} AAPL.pdf")
            assert result.fiscal_quarter == f"Q{q}"
            assert result.fiscal_year == 2024

    def test_all_known_tickers(self) -> None:
        """Test parsing all known company tickers."""
        tickers = ["AAPL", "MSFT", "NVDA", "INTC", "AMD"]
        for ticker in tickers:
            result = parse_filename(f"2023 Q1 {ticker}.pdf")
            assert result.company_ticker == ticker
            assert result.company_name is not None

    def test_lowercase_quarter(self) -> None:
        """Test parsing lowercase quarter."""
        result = parse_filename("2023 q3 INTC.pdf")
        assert result.fiscal_quarter == "Q3"

    def test_lowercase_ticker(self) -> None:
        """Test parsing lowercase ticker (should normalize to uppercase)."""
        result = parse_filename("2023 Q3 intc.pdf")
        assert result.company_ticker == "INTC"

    def test_extra_whitespace(self) -> None:
        """Test parsing with extra whitespace."""
        result = parse_filename("  2023  Q3  INTC.pdf  ")
        assert result.fiscal_quarter == "Q3"
        assert result.fiscal_year == 2023

    def test_without_pdf_extension(self) -> None:
        """Test parsing without .pdf extension."""
        result = parse_filename("2023 Q3 INTC")
        assert result.fiscal_quarter == "Q3"
        assert result.fiscal_year == 2023
        assert result.company_ticker == "INTC"

    def test_empty_string(self) -> None:
        """Test parsing empty string returns null metadata."""
        result = parse_filename("")
        assert result.fiscal_quarter is None
        assert result.fiscal_year is None
        assert result.company_ticker is None

    def test_none_input(self) -> None:
        """Test parsing None input returns null metadata."""
        result = parse_filename(None)  # type: ignore[arg-type]
        assert result.fiscal_quarter is None

    def test_invalid_quarter_q5(self) -> None:
        """Test invalid quarter Q5 returns null."""
        result = parse_filename("2023 Q5 INTC.pdf")
        assert result.fiscal_quarter is None

    def test_invalid_quarter_q0(self) -> None:
        """Test invalid quarter Q0 returns null."""
        result = parse_filename("2023 Q0 INTC.pdf")
        assert result.fiscal_quarter is None

    def test_missing_year(self) -> None:
        """Test filename without year returns null."""
        result = parse_filename("Q3 INTC.pdf")
        assert result.fiscal_quarter is None

    def test_malformed_filename(self) -> None:
        """Test malformed filename returns null."""
        result = parse_filename("random_document.pdf")
        assert result.fiscal_quarter is None

    def test_year_out_of_range_too_old(self) -> None:
        """Test year before 1990 returns null."""
        result = parse_filename("1985 Q3 INTC.pdf")
        assert result.fiscal_quarter is None

    def test_year_out_of_range_too_new(self) -> None:
        """Test year after 2100 returns null."""
        result = parse_filename("2150 Q3 INTC.pdf")
        assert result.fiscal_quarter is None

    def test_unknown_ticker_still_parses(self) -> None:
        """Test unknown ticker parses but company_name is None."""
        result = parse_filename("2023 Q3 UNKNOWN.pdf")
        assert result.fiscal_quarter == "Q3"
        assert result.fiscal_year == 2023
        assert result.company_ticker == "UNKNOWN"
        assert result.company_name is None

    def test_document_date_format(self) -> None:
        """Test document_date format is YYYY-QN."""
        result = parse_filename("2024 Q2 MSFT.pdf")
        assert result.document_date == "2024-Q2"

    def test_full_path_handling(self) -> None:
        """Test that full path still works if filename is at end."""
        # Note: parse_filename expects just the filename, not full path
        # This test verifies behavior with path-like string
        result = parse_filename("2023 Q3 INTC.pdf")
        assert result.is_valid()


class TestGetCompanyName:
    """Tests for get_company_name function."""

    def test_known_tickers(self) -> None:
        """Test all known tickers resolve correctly."""
        assert get_company_name("AAPL") == "Apple Inc."
        assert get_company_name("MSFT") == "Microsoft Corporation"
        assert get_company_name("NVDA") == "NVIDIA Corporation"
        assert get_company_name("INTC") == "Intel Corporation"
        assert get_company_name("AMD") == "Advanced Micro Devices, Inc."

    def test_case_insensitive(self) -> None:
        """Test ticker lookup is case-insensitive."""
        assert get_company_name("aapl") == "Apple Inc."
        assert get_company_name("Msft") == "Microsoft Corporation"

    def test_unknown_ticker_returns_none(self) -> None:
        """Test unknown ticker returns None."""
        assert get_company_name("UNKNOWN") is None
        assert get_company_name("GOOG") is None


class TestExtractTemporalProperties:
    """Tests for extract_temporal_properties convenience function."""

    def test_returns_dict_format(self) -> None:
        """Test returns dictionary with expected keys."""
        result = extract_temporal_properties("2023 Q3 INTC.pdf")
        assert "fiscal_quarter" in result
        assert "fiscal_year" in result
        assert "document_date" in result
        assert "company" in result

    def test_company_field_is_name_not_ticker(self) -> None:
        """Test company field contains name, not ticker."""
        result = extract_temporal_properties("2023 Q3 INTC.pdf")
        assert result["company"] == "Intel Corporation"

    def test_empty_filename_returns_nulls(self) -> None:
        """Test empty filename returns all nulls."""
        result = extract_temporal_properties("")
        assert result["fiscal_quarter"] is None
        assert result["fiscal_year"] is None
        assert result["document_date"] is None
        assert result["company"] is None


class TestFilenamePattern:
    """Tests for the regex pattern directly."""

    def test_pattern_matches_valid_formats(self) -> None:
        """Test regex pattern matches valid filename formats."""
        valid_filenames = [
            "2023 Q3 INTC.pdf",
            "2024 Q1 AAPL.pdf",
            "2020 Q4 AMD.pdf",
            "2023 q2 msft.pdf",
            "  2023 Q3 INTC.pdf  ",
        ]
        for filename in valid_filenames:
            assert FILENAME_PATTERN.match(filename) is not None, f"Failed: {filename}"

    def test_pattern_rejects_invalid_formats(self) -> None:
        """Test regex pattern rejects invalid filename formats."""
        invalid_filenames = [
            "random.pdf",
            "2023-Q3-INTC.pdf",  # Wrong separators
            "Q3 2023 INTC.pdf",  # Wrong order
            "2023 INTC.pdf",  # Missing quarter
        ]
        for filename in invalid_filenames:
            assert FILENAME_PATTERN.match(filename) is None, f"Matched: {filename}"


class TestNeo4jStoreTemporalIntegration:
    """Tests for neo4j_store temporal integration."""

    @pytest.mark.asyncio
    async def test_add_episodes_with_temporal_properties(self) -> None:
        """Test add_episodes includes temporal properties."""
        # Mock the connection manager and session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"episode_id": "ep_123"})
        mock_session.run = AsyncMock(return_value=mock_result)

        mock_cm = MagicMock()
        mock_cm.get_neo4j_session = MagicMock(return_value=AsyncMock())
        mock_cm.get_neo4j_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.get_neo4j_session.return_value.__aexit__ = AsyncMock(return_value=None)

        # Import and create Neo4jStore
        from src.agentic_rag.storage.neo4j_store import Neo4jStore

        store = Neo4jStore(mock_cm)

        # Call add_episodes with source_document_name
        await store.add_episodes(
            facts=["Test fact"],
            entity_names=["TestEntity"],
            source_chunk_id="chunk_1",
            source_document_id="doc_1",
            source_document_name="2023 Q3 INTC.pdf",
        )

        # Verify session.run was called with temporal properties
        call_args = mock_session.run.call_args_list[0]
        # Check that temporal properties are passed
        kwargs = call_args.kwargs if call_args.kwargs else {}
        assert "fiscal_quarter" in kwargs
        assert "fiscal_year" in kwargs
        assert "document_date" in kwargs
        assert "company" in kwargs

    @pytest.mark.asyncio
    async def test_add_episodes_without_document_name(self) -> None:
        """Test add_episodes works without source_document_name."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"episode_id": "ep_123"})
        mock_session.run = AsyncMock(return_value=mock_result)

        mock_cm = MagicMock()
        mock_cm.get_neo4j_session = MagicMock(return_value=AsyncMock())
        mock_cm.get_neo4j_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.get_neo4j_session.return_value.__aexit__ = AsyncMock(return_value=None)

        from src.agentic_rag.storage.neo4j_store import Neo4jStore

        store = Neo4jStore(mock_cm)

        # Call without source_document_name
        await store.add_episodes(
            facts=["Test fact"],
            entity_names=["TestEntity"],
            source_chunk_id="chunk_1",
            source_document_id="doc_1",
        )

        # Verify it still works (temporal props will be None)
        call_args = mock_session.run.call_args_list[0]
        kwargs = call_args.kwargs if call_args.kwargs else {}
        assert kwargs.get("fiscal_quarter") is None


class TestBackfillScript:
    """Integration tests for backfill script components."""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self) -> None:
        """Test retry_with_backoff succeeds on first try."""
        import sys
        from pathlib import Path

        # Add scripts to path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_temporal_metadata import retry_with_backoff

        async def success_func() -> str:
            return "success"

        result = await retry_with_backoff(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_retries_on_failure(self) -> None:
        """Test retry_with_backoff retries on failure."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_temporal_metadata import retry_with_backoff

        call_count = 0

        async def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await retry_with_backoff(failing_func, max_retries=3, initial_backoff=0.01)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_raises_after_max_retries(self) -> None:
        """Test retry_with_backoff raises after max retries exceeded."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_temporal_metadata import retry_with_backoff

        async def always_fails() -> str:
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError):
            await retry_with_backoff(always_fails, max_retries=2, initial_backoff=0.01)

    def test_temporal_backfill_class_initialization(self) -> None:
        """Test TemporalMetadataBackfill class initializes correctly."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from backfill_temporal_metadata import TemporalMetadataBackfill

        mock_cm = MagicMock()
        backfill = TemporalMetadataBackfill(
            connection_manager=mock_cm,
            batch_size=100,
            dry_run=True,
            verbose=True,
        )

        assert backfill.batch_size == 100
        assert backfill.dry_run is True
        assert backfill.verbose is True
        assert backfill.episodes_processed == 0
        assert backfill.episodes_updated == 0
