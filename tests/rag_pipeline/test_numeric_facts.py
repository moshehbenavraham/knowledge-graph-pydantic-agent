"""
Unit and integration tests for numeric fact extraction.

Tests cover:
- Currency pattern extraction with various formats
- Magnitude pattern extraction (million, billion, etc.)
- Percentage pattern extraction
- Edge cases (empty, malformed, multiple values)
- Backfill script with mock Neo4j connection
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agentic_rag.graph.numeric_parser import (
    CURRENCY_SYMBOL_MAP,
    MAGNITUDE_MAP,
    NumericFact,
    extract_numeric_facts_json,
    map_currency_symbol,
    normalize_magnitude,
    normalize_percentage,
    parse_number_string,
    parse_numeric_facts,
)

# =============================================================================
# T018: Currency Pattern Extraction Tests (8+ test cases)
# =============================================================================


class TestCurrencyPatternExtraction:
    """Test currency pattern extraction with various formats."""

    def test_usd_with_dollar_sign_and_billions(self) -> None:
        """Test $40.6B format."""
        facts = parse_numeric_facts("Revenue was $40.6B in Q3")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(40.6e9)
        assert facts[0].raw_value == pytest.approx(40.6)
        assert facts[0].unit == "USD"
        assert facts[0].magnitude == "billion"
        assert facts[0].fact_type == "currency"

    def test_usd_with_comma_thousands_and_million(self) -> None:
        """Test $40,665 million format."""
        facts = parse_numeric_facts("Net income was $40,665 million")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(40665e6)
        assert facts[0].raw_value == pytest.approx(40665)
        assert facts[0].unit == "USD"
        assert facts[0].magnitude == "million"

    def test_usd_with_decimal_and_million(self) -> None:
        """Test $1.5 million format."""
        facts = parse_numeric_facts("Cost was $1.5 million")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(1.5e6)
        assert facts[0].raw_value == pytest.approx(1.5)

    def test_eur_currency_format(self) -> None:
        """Test EUR currency format."""
        facts = parse_numeric_facts("European sales were EUR 35 billion")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(35e9)
        assert facts[0].unit == "EUR"
        assert facts[0].fact_type == "currency"

    def test_gbp_currency_format(self) -> None:
        """Test GBP currency format."""
        facts = parse_numeric_facts("UK revenue GBP 500 million")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(500e6)
        assert facts[0].unit == "GBP"

    def test_usd_without_magnitude(self) -> None:
        """Test plain USD amount without magnitude."""
        facts = parse_numeric_facts("Price was $50")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(50)
        assert facts[0].raw_value == pytest.approx(50)
        assert facts[0].magnitude is None

    def test_usd_with_thousands_k(self) -> None:
        """Test $100K format."""
        facts = parse_numeric_facts("Bonus was $100K")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(100e3)
        assert facts[0].magnitude == "thousand"

    def test_case_insensitive_magnitude(self) -> None:
        """Test case insensitivity for magnitude words."""
        facts = parse_numeric_facts("Revenue was $5 MILLION")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(5e6)
        assert facts[0].magnitude == "million"

    def test_usd_with_m_suffix(self) -> None:
        """Test $5M format (single letter magnitude)."""
        facts = parse_numeric_facts("Budget is $5M")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(5e6)

    def test_currency_preserves_original_text(self) -> None:
        """Test that original text is preserved in fact."""
        facts = parse_numeric_facts("Total was $40,665 million in revenue")
        assert len(facts) == 1
        assert "$40,665 million" in facts[0].original_text


# =============================================================================
# T019: Magnitude and Percentage Pattern Tests (8+ test cases)
# =============================================================================


class TestMagnitudePatternExtraction:
    """Test magnitude pattern extraction without currency symbols."""

    def test_plain_billion(self) -> None:
        """Test '40 billion' format."""
        facts = parse_numeric_facts("They produced 40 billion units")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(40e9)
        assert facts[0].unit == "number"
        assert facts[0].fact_type == "number"

    def test_plain_million_with_decimal(self) -> None:
        """Test '35.6 million' format."""
        facts = parse_numeric_facts("Population of 35.6 million people")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(35.6e6)

    def test_magnitude_with_trailing_currency(self) -> None:
        """Test '40 billion dollars' format."""
        facts = parse_numeric_facts("Market cap of 40 billion dollars")
        assert len(facts) == 1
        assert facts[0].unit == "USD"
        assert facts[0].fact_type == "currency"

    def test_magnitude_with_euros(self) -> None:
        """Test '50 million euros' format."""
        facts = parse_numeric_facts("Investment of 50 million euros")
        assert len(facts) == 1
        assert facts[0].unit == "EUR"

    def test_thousands_magnitude(self) -> None:
        """Test 'thousand' magnitude."""
        facts = parse_numeric_facts("Sold 500 thousand copies")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(500e3)
        assert facts[0].magnitude == "thousand"


class TestPercentagePatternExtraction:
    """Test percentage pattern extraction."""

    def test_percent_sign(self) -> None:
        """Test '50%' format."""
        facts = parse_numeric_facts("Growth was 50%")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(0.5)
        assert facts[0].raw_value == pytest.approx(50)
        assert facts[0].unit == "percent"
        assert facts[0].fact_type == "percentage"

    def test_decimal_percent(self) -> None:
        """Test '12.5%' format."""
        facts = parse_numeric_facts("Interest rate is 12.5%")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(0.125)
        assert facts[0].raw_value == pytest.approx(12.5)

    def test_percent_word(self) -> None:
        """Test '50 percent' format."""
        facts = parse_numeric_facts("Efficiency of 50 percent")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(0.5)

    def test_small_percentage(self) -> None:
        """Test small percentage like '0.5%'."""
        facts = parse_numeric_facts("Fee is 0.5%")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(0.005)
        assert facts[0].raw_value == pytest.approx(0.5)

    def test_large_percentage(self) -> None:
        """Test percentage over 100%."""
        facts = parse_numeric_facts("Increase of 150%")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(1.5)


# =============================================================================
# T020: Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self) -> None:
        """Test empty string returns empty list."""
        facts = parse_numeric_facts("")
        assert facts == []

    def test_none_input(self) -> None:
        """Test None input returns empty list."""
        # Type ignore because we're testing invalid input
        facts = parse_numeric_facts(None)  # type: ignore[arg-type]
        assert facts == []

    def test_no_numbers_in_text(self) -> None:
        """Test text with no numbers returns empty list."""
        facts = parse_numeric_facts("This is a sentence without any numbers")
        assert facts == []

    def test_multiple_currency_values(self) -> None:
        """Test extraction of multiple currency values."""
        text = "Revenue was $40B and expenses were $35 billion"
        facts = parse_numeric_facts(text)
        assert len(facts) == 2
        values = sorted([f.value for f in facts])
        assert values[0] == pytest.approx(35e9)
        assert values[1] == pytest.approx(40e9)

    def test_mixed_currencies(self) -> None:
        """Test extraction with mixed currencies."""
        text = "US sales $100 million, European sales EUR 80 million"
        facts = parse_numeric_facts(text)
        assert len(facts) == 2
        units = {f.unit for f in facts}
        assert "USD" in units
        assert "EUR" in units

    def test_currency_and_percentage_together(self) -> None:
        """Test extraction of both currency and percentage."""
        text = "Revenue was $50 billion, up 15% from last year"
        facts = parse_numeric_facts(text)
        assert len(facts) == 2
        fact_types = {f.fact_type for f in facts}
        assert "currency" in fact_types
        assert "percentage" in fact_types

    def test_whitespace_handling(self) -> None:
        """Test handling of extra whitespace."""
        facts = parse_numeric_facts("Revenue  was  $40   million")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(40e6)

    def test_comma_in_large_number(self) -> None:
        """Test handling of comma-separated thousands."""
        facts = parse_numeric_facts("Total was $1,234,567")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(1234567)

    def test_trillion_magnitude(self) -> None:
        """Test trillion magnitude."""
        facts = parse_numeric_facts("National debt of $30 trillion")
        assert len(facts) == 1
        assert facts[0].value == pytest.approx(30e12)
        assert facts[0].magnitude == "trillion"


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Test helper functions for normalization and mapping."""

    def test_normalize_magnitude_million(self) -> None:
        """Test million normalization."""
        assert normalize_magnitude(40.0, "million") == pytest.approx(40e6)

    def test_normalize_magnitude_billion(self) -> None:
        """Test billion normalization."""
        assert normalize_magnitude(5.5, "billion") == pytest.approx(5.5e9)

    def test_normalize_magnitude_none(self) -> None:
        """Test no magnitude returns original value."""
        assert normalize_magnitude(100.0, None) == pytest.approx(100.0)

    def test_normalize_magnitude_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert normalize_magnitude(1.0, "MILLION") == pytest.approx(1e6)
        assert normalize_magnitude(1.0, "Billion") == pytest.approx(1e9)

    def test_map_currency_symbol_dollar(self) -> None:
        """Test dollar sign mapping."""
        assert map_currency_symbol("$") == "USD"

    def test_map_currency_symbol_eur(self) -> None:
        """Test EUR mapping."""
        assert map_currency_symbol("EUR") == "EUR"
        assert map_currency_symbol("eur") == "EUR"

    def test_map_currency_symbol_gbp(self) -> None:
        """Test GBP mapping."""
        assert map_currency_symbol("GBP") == "GBP"
        assert map_currency_symbol("pounds") == "GBP"

    def test_parse_number_string_with_commas(self) -> None:
        """Test parsing numbers with commas."""
        assert parse_number_string("40,665") == pytest.approx(40665)
        assert parse_number_string("1,234,567") == pytest.approx(1234567)

    def test_parse_number_string_with_decimal(self) -> None:
        """Test parsing decimal numbers."""
        assert parse_number_string("40.665") == pytest.approx(40.665)

    def test_normalize_percentage(self) -> None:
        """Test percentage normalization."""
        normalized, raw = normalize_percentage(50.0)
        assert normalized == pytest.approx(0.5)
        assert raw == pytest.approx(50.0)


class TestNumericFactModel:
    """Test NumericFact Pydantic model."""

    def test_model_creation(self) -> None:
        """Test creating a NumericFact instance."""
        fact = NumericFact(
            value=40665000000.0,
            raw_value=40665.0,
            unit="USD",
            magnitude="million",
            original_text="$40,665 million",
            fact_type="currency",
        )
        assert fact.value == 40665000000.0
        assert fact.unit == "USD"
        assert fact.fact_type == "currency"

    def test_model_to_dict(self) -> None:
        """Test converting model to dictionary."""
        fact = NumericFact(
            value=1000000.0,
            raw_value=1.0,
            unit="USD",
            magnitude="million",
            original_text="$1 million",
            fact_type="currency",
        )
        d = fact.to_dict()
        assert d["value"] == 1000000.0
        assert d["unit"] == "USD"
        assert d["fact_type"] == "currency"
        assert d["magnitude"] == "million"

    def test_model_with_none_magnitude(self) -> None:
        """Test model with None magnitude."""
        fact = NumericFact(
            value=50.0,
            raw_value=50.0,
            unit="USD",
            magnitude=None,
            original_text="$50",
            fact_type="currency",
        )
        assert fact.magnitude is None
        assert fact.to_dict()["magnitude"] is None


class TestExtractNumericFactsJson:
    """Test the JSON extraction convenience function."""

    def test_returns_list_of_dicts(self) -> None:
        """Test that function returns list of dictionaries."""
        result = extract_numeric_facts_json("Revenue was $40B")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["value"] == pytest.approx(40e9)

    def test_empty_text_returns_empty_list(self) -> None:
        """Test empty text returns empty list."""
        result = extract_numeric_facts_json("")
        assert result == []


# =============================================================================
# T021: Integration Tests for Backfill Script with Mock Neo4j
# =============================================================================


class TestBackfillScriptIntegration:
    """Integration tests for the backfill script with mock Neo4j."""

    @pytest.fixture
    def mock_connection_manager(self) -> MagicMock:
        """Create a mock connection manager."""
        manager = MagicMock()

        # Mock the context manager for Neo4j session
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        manager.get_neo4j_session.return_value = mock_context

        return manager

    @pytest.mark.asyncio
    async def test_backfill_class_initialization(self, mock_connection_manager: MagicMock) -> None:
        """Test NumericFactsBackfill class initialization."""
        from scripts.backfill_numeric_facts import NumericFactsBackfill

        backfill = NumericFactsBackfill(
            connection_manager=mock_connection_manager,
            batch_size=100,
            dry_run=True,
            verbose=True,
        )

        assert backfill.batch_size == 100
        assert backfill.dry_run is True
        assert backfill.verbose is True
        assert backfill.episodes_processed == 0

    @pytest.mark.asyncio
    async def test_get_total_episode_count(self, mock_connection_manager: MagicMock) -> None:
        """Test getting total episode count."""
        from scripts.backfill_numeric_facts import NumericFactsBackfill

        # Setup mock response
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"count": 1000})
        mock_session.run = AsyncMock(return_value=mock_result)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_connection_manager.get_neo4j_session.return_value = mock_context

        backfill = NumericFactsBackfill(
            connection_manager=mock_connection_manager,
            dry_run=True,
        )

        count = await backfill.get_total_episode_count()
        assert count == 1000

    @pytest.mark.asyncio
    async def test_update_episode_dry_run(self, mock_connection_manager: MagicMock) -> None:
        """Test that dry run does not update episodes."""
        from scripts.backfill_numeric_facts import NumericFactsBackfill

        backfill = NumericFactsBackfill(
            connection_manager=mock_connection_manager,
            dry_run=True,
        )

        numeric_facts = [
            {
                "value": 40e9,
                "raw_value": 40,
                "unit": "USD",
                "magnitude": "billion",
                "original_text": "$40B",
                "fact_type": "currency",
            }
        ]

        result = await backfill.update_episode_numeric_facts("ep_123", numeric_facts)
        assert result is True
        # Session should not be accessed in dry run
        mock_connection_manager.get_neo4j_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_episode_live(self, mock_connection_manager: MagicMock) -> None:
        """Test live update of episode."""
        from scripts.backfill_numeric_facts import NumericFactsBackfill

        # Setup mock session
        mock_session = AsyncMock()
        mock_session.run = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_connection_manager.get_neo4j_session.return_value = mock_context

        backfill = NumericFactsBackfill(
            connection_manager=mock_connection_manager,
            dry_run=False,
        )

        numeric_facts = [
            {
                "value": 40e9,
                "raw_value": 40,
                "unit": "USD",
                "magnitude": "billion",
                "original_text": "$40B",
                "fact_type": "currency",
            }
        ]

        result = await backfill.update_episode_numeric_facts("ep_123", numeric_facts)
        assert result is True
        mock_session.run.assert_called_once()

    def test_print_summary(self, mock_connection_manager: MagicMock) -> None:
        """Test summary printing."""
        from scripts.backfill_numeric_facts import NumericFactsBackfill

        backfill = NumericFactsBackfill(
            connection_manager=mock_connection_manager,
        )
        backfill.episodes_processed = 100
        backfill.episodes_updated = 50
        backfill.episodes_skipped = 50
        backfill.total_facts_extracted = 150
        backfill.errors = 0

        # Should not raise
        backfill.print_summary()


class TestConstantMaps:
    """Test constant map values."""

    def test_magnitude_map_values(self) -> None:
        """Test MAGNITUDE_MAP has correct values."""
        assert MAGNITUDE_MAP["million"] == 1e6
        assert MAGNITUDE_MAP["billion"] == 1e9
        assert MAGNITUDE_MAP["thousand"] == 1e3
        assert MAGNITUDE_MAP["trillion"] == 1e12

    def test_currency_symbol_map_values(self) -> None:
        """Test CURRENCY_SYMBOL_MAP has correct values."""
        assert CURRENCY_SYMBOL_MAP["$"] == "USD"
        assert CURRENCY_SYMBOL_MAP["eur"] == "EUR"
        assert CURRENCY_SYMBOL_MAP["gbp"] == "GBP"


# =============================================================================
# Real-world Financial Text Examples
# =============================================================================


class TestRealWorldExamples:
    """Test with real-world financial text examples."""

    def test_earnings_report_style(self) -> None:
        """Test text similar to earnings reports."""
        text = (
            "Intel reported revenue of $15.4 billion for Q3 2023, "
            "up 12% from the prior quarter. Operating margin was 25%."
        )
        facts = parse_numeric_facts(text)
        assert len(facts) >= 3

        # Should find currency, and percentages
        fact_types = [f.fact_type for f in facts]
        assert "currency" in fact_types
        assert "percentage" in fact_types

    def test_sec_filing_style(self) -> None:
        """Test text similar to SEC filings."""
        text = (
            "Total assets were $234,567 million as of December 31, 2023. "
            "Long-term debt increased to $45 billion."
        )
        facts = parse_numeric_facts(text)
        assert len(facts) >= 2

        # Find the billion dollar amount
        billion_facts = [f for f in facts if f.value >= 1e9]
        assert len(billion_facts) >= 1

    def test_multiple_currencies_in_report(self) -> None:
        """Test extraction from multi-currency report."""
        text = (
            "US operations generated $500 million in revenue. "
            "European operations contributed EUR 350 million. "
            "Combined operating margin of 18%."
        )
        facts = parse_numeric_facts(text)
        assert len(facts) >= 3

        currencies = {f.unit for f in facts if f.fact_type == "currency"}
        assert "USD" in currencies
        assert "EUR" in currencies
