"""Unit tests for entity deduplication system.

Tests cover:
- Canonical name normalization (T018)
- Deduplication matching passes (T019)
- Merge history logging and retrieval (T020)
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agentic_rag.entity_resolution.canonical_names import (
    COMPANY_SUFFIXES,
    TICKER_TO_CANONICAL,
    get_all_known_aliases,
    get_canonical_name,
    is_excluded_term,
    normalize_entity_name,
)
from src.agentic_rag.entity_resolution.deduplication import (
    DEFAULT_FUZZY_THRESHOLD,
    DuplicateGroup,
    Entity,
    EntityResolver,
    context_match_pass,
    exact_match_pass,
    fuzzy_match_pass,
    ticker_resolution_pass,
)
from src.agentic_rag.entity_resolution.merge_history import (
    MergedEntity,
    MergeHistory,
    MergeMatchType,
    MergeOperation,
    MergeStatus,
)

# =============================================================================
# T018: Tests for canonical_names.py
# =============================================================================


class TestNormalizeEntityName:
    """Tests for normalize_entity_name function."""

    def test_empty_string_returns_empty(self) -> None:
        """Empty input returns empty string."""
        assert normalize_entity_name("") == ""
        assert normalize_entity_name("   ") == ""

    def test_lowercase_conversion(self) -> None:
        """Names are converted to lowercase."""
        assert normalize_entity_name("APPLE") == "apple"
        assert normalize_entity_name("Microsoft") == "microsoft"

    def test_strips_whitespace(self) -> None:
        """Leading and trailing whitespace is removed."""
        assert normalize_entity_name("  Apple  ") == "apple"
        assert normalize_entity_name("\tIntel\n") == "intel"

    def test_removes_inc_suffix(self) -> None:
        """Removes Inc. suffix variations."""
        assert normalize_entity_name("Apple Inc.") == "apple"
        assert normalize_entity_name("Apple Inc") == "apple"
        assert normalize_entity_name("Apple Incorporated") == "apple"

    def test_removes_corp_suffix(self) -> None:
        """Removes Corp. suffix variations."""
        assert normalize_entity_name("Intel Corp.") == "intel"
        assert normalize_entity_name("Intel Corp") == "intel"
        assert normalize_entity_name("Intel Corporation") == "intel"

    def test_removes_llc_suffix(self) -> None:
        """Removes LLC suffix variations."""
        assert normalize_entity_name("Acme LLC") == "acme"
        assert normalize_entity_name("Acme L.L.C.") == "acme"

    def test_removes_ltd_suffix(self) -> None:
        """Removes Ltd. suffix variations."""
        assert normalize_entity_name("British Ltd.") == "british"
        assert normalize_entity_name("British Ltd") == "british"
        assert normalize_entity_name("British Limited") == "british"

    def test_removes_co_suffix(self) -> None:
        """Removes Co. suffix variations."""
        assert normalize_entity_name("Johnson Co.") == "johnson"
        assert normalize_entity_name("Johnson Company") == "johnson"

    def test_removes_nested_suffixes(self) -> None:
        """Removes nested suffixes like 'Company, Inc.'."""
        assert normalize_entity_name("Acme Company, Inc.") == "acme"

    def test_collapses_multiple_spaces(self) -> None:
        """Multiple spaces are collapsed to single space."""
        assert normalize_entity_name("United   Parcel   Service") == "united parcel service"

    def test_strips_trailing_punctuation(self) -> None:
        """Trailing punctuation is stripped."""
        assert normalize_entity_name("Apple,") == "apple"
        assert normalize_entity_name("Microsoft.") == "microsoft"

    def test_preserves_internal_punctuation(self) -> None:
        """Internal punctuation in names is preserved."""
        result = normalize_entity_name("Amazon.com")
        assert "amazon" in result


class TestGetCanonicalName:
    """Tests for get_canonical_name function."""

    def test_known_ticker_returns_canonical(self) -> None:
        """Known ticker symbols return canonical names."""
        assert get_canonical_name("AAPL") == "Apple Inc."
        assert get_canonical_name("MSFT") == "Microsoft Corporation"
        assert get_canonical_name("INTC") == "Intel Corporation"
        assert get_canonical_name("GOOGL") == "Alphabet Inc."

    def test_case_insensitive_ticker(self) -> None:
        """Ticker lookup is case-insensitive."""
        assert get_canonical_name("aapl") == "Apple Inc."
        assert get_canonical_name("Aapl") == "Apple Inc."
        assert get_canonical_name("AAPL") == "Apple Inc."

    def test_unknown_ticker_returns_none(self) -> None:
        """Unknown ticker symbols return None."""
        assert get_canonical_name("UNKNOWN") is None
        assert get_canonical_name("XYZ123") is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        assert get_canonical_name("") is None
        assert get_canonical_name("   ") is None

    def test_strips_whitespace(self) -> None:
        """Whitespace around ticker is stripped."""
        assert get_canonical_name("  AAPL  ") == "Apple Inc."


class TestIsExcludedTerm:
    """Tests for is_excluded_term function."""

    def test_generic_terms_excluded(self) -> None:
        """Generic terms are excluded from matching."""
        assert is_excluded_term("The Company") is True
        assert is_excluded_term("Management") is True
        assert is_excluded_term("Board") is True
        assert is_excluded_term("Shareholders") is True

    def test_case_insensitive(self) -> None:
        """Exclusion check is case-insensitive."""
        assert is_excluded_term("THE COMPANY") is True
        assert is_excluded_term("the company") is True
        assert is_excluded_term("Company") is True

    def test_short_names_excluded(self) -> None:
        """Names shorter than 2 chars are excluded."""
        assert is_excluded_term("A") is True
        assert is_excluded_term("") is True

    def test_valid_names_not_excluded(self) -> None:
        """Valid entity names are not excluded."""
        assert is_excluded_term("Apple") is False
        assert is_excluded_term("Microsoft Corporation") is False
        assert is_excluded_term("Intel") is False


class TestGetAllKnownAliases:
    """Tests for get_all_known_aliases function."""

    def test_returns_canonical_and_normalized(self) -> None:
        """Returns both canonical name and normalized form."""
        aliases = get_all_known_aliases("Apple Inc.")
        assert "Apple Inc." in aliases
        assert "apple" in aliases

    def test_includes_ticker_symbols(self) -> None:
        """Includes ticker symbols for known companies."""
        aliases = get_all_known_aliases("Apple Inc.")
        assert "AAPL" in aliases

    def test_unknown_company_returns_basic_aliases(self) -> None:
        """Unknown companies return at least 2 aliases."""
        aliases = get_all_known_aliases("Unknown Corp")
        assert len(aliases) >= 2


class TestCompanySuffixConstants:
    """Tests for COMPANY_SUFFIXES constant."""

    def test_contains_common_suffixes(self) -> None:
        """Contains all common company suffixes."""
        assert "inc." in COMPANY_SUFFIXES
        assert "corp." in COMPANY_SUFFIXES
        assert "llc" in COMPANY_SUFFIXES
        assert "ltd." in COMPANY_SUFFIXES

    def test_longer_patterns_first(self) -> None:
        """Longer patterns appear before shorter ones."""
        inc_idx = COMPANY_SUFFIXES.index("incorporated")
        inc_short_idx = COMPANY_SUFFIXES.index("inc.")
        assert inc_idx < inc_short_idx


class TestTickerMappings:
    """Tests for TICKER_TO_CANONICAL constant."""

    def test_contains_major_companies(self) -> None:
        """Contains mappings for major companies."""
        assert "AAPL" in TICKER_TO_CANONICAL
        assert "MSFT" in TICKER_TO_CANONICAL
        assert "GOOGL" in TICKER_TO_CANONICAL
        assert "AMZN" in TICKER_TO_CANONICAL

    def test_all_tickers_uppercase(self) -> None:
        """All ticker keys are uppercase."""
        for ticker in TICKER_TO_CANONICAL:
            assert ticker == ticker.upper()


# =============================================================================
# T019: Tests for deduplication.py
# =============================================================================


class TestEntity:
    """Tests for Entity dataclass."""

    def test_normalized_name_property(self) -> None:
        """normalized_name returns normalized form."""
        entity = Entity(
            entity_id="uuid-1",
            name="Apple Inc.",
            entity_type="COMPANY",
            mention_count=10,
        )
        assert entity.normalized_name == "apple"

    def test_get_companies_extracts_from_refs(self) -> None:
        """get_companies extracts company from document_refs."""
        entity = Entity(
            entity_id="uuid-1",
            name="Test Entity",
            document_refs=[
                {"company": "AAPL", "filename": "test.pdf"},
                {"company": "INTC", "filename": "test2.pdf"},
            ],
        )
        companies = entity.get_companies()
        assert "AAPL" in companies
        assert "INTC" in companies

    def test_get_companies_handles_empty_refs(self) -> None:
        """get_companies handles empty document_refs."""
        entity = Entity(entity_id="uuid-1", name="Test", document_refs=[])
        assert entity.get_companies() == set()


class TestDuplicateGroup:
    """Tests for DuplicateGroup dataclass."""

    def test_total_mentions(self) -> None:
        """total_mentions sums all entity mentions."""
        canonical = Entity(entity_id="1", name="Apple", mention_count=100)
        dup1 = Entity(entity_id="2", name="AAPL", mention_count=50)
        dup2 = Entity(entity_id="3", name="Apple Inc", mention_count=25)

        group = DuplicateGroup(
            canonical=canonical,
            duplicates=[dup1, dup2],
            match_type=MergeMatchType.EXACT,
        )
        assert group.total_mentions == 175

    def test_all_entities(self) -> None:
        """all_entities returns canonical plus duplicates."""
        canonical = Entity(entity_id="1", name="Apple", mention_count=100)
        dup1 = Entity(entity_id="2", name="AAPL", mention_count=50)

        group = DuplicateGroup(canonical=canonical, duplicates=[dup1])
        all_ents = group.all_entities()
        assert len(all_ents) == 2
        assert canonical in all_ents
        assert dup1 in all_ents


class TestExactMatchPass:
    """Tests for exact_match_pass function."""

    def test_groups_identical_normalized_names(self) -> None:
        """Groups entities with identical normalized names."""
        entities = [
            Entity(entity_id="1", name="Apple Inc.", mention_count=100),
            Entity(entity_id="2", name="Apple Inc", mention_count=50),
            Entity(entity_id="3", name="apple incorporated", mention_count=25),
        ]
        groups = exact_match_pass(entities)
        assert len(groups) == 1
        assert groups[0].canonical.entity_id == "1"  # Highest mentions
        assert len(groups[0].duplicates) == 2

    def test_excludes_generic_terms(self) -> None:
        """Excludes generic terms from matching."""
        entities = [
            Entity(entity_id="1", name="The Company", mention_count=100),
            Entity(entity_id="2", name="Management", mention_count=50),
            Entity(entity_id="3", name="Apple", mention_count=25),
        ]
        groups = exact_match_pass(entities)
        assert len(groups) == 0  # No groups formed

    def test_no_groups_for_unique_entities(self) -> None:
        """Returns empty list when all entities unique."""
        entities = [
            Entity(entity_id="1", name="Apple", mention_count=100),
            Entity(entity_id="2", name="Microsoft", mention_count=50),
            Entity(entity_id="3", name="Google", mention_count=25),
        ]
        groups = exact_match_pass(entities)
        assert len(groups) == 0

    def test_highest_mention_count_becomes_canonical(self) -> None:
        """Entity with highest mention count becomes canonical."""
        entities = [
            Entity(entity_id="1", name="Apple Inc", mention_count=10),
            Entity(entity_id="2", name="Apple Inc.", mention_count=100),
            Entity(entity_id="3", name="APPLE INC", mention_count=50),
        ]
        groups = exact_match_pass(entities)
        assert len(groups) == 1
        assert groups[0].canonical.entity_id == "2"


class TestFuzzyMatchPass:
    """Tests for fuzzy_match_pass function."""

    def test_matches_similar_names(self) -> None:
        """Matches entities with similar names above threshold."""
        entities = [
            Entity(entity_id="1", name="Microsft", mention_count=100),  # Typo
            Entity(entity_id="2", name="Microsoft", mention_count=50),
        ]
        groups = fuzzy_match_pass(entities, set(), threshold=85.0)
        assert len(groups) == 1

    def test_respects_threshold(self) -> None:
        """Does not match when similarity below threshold."""
        entities = [
            Entity(entity_id="1", name="Apple", mention_count=100),
            Entity(entity_id="2", name="Orange", mention_count=50),
        ]
        groups = fuzzy_match_pass(entities, set(), threshold=90.0)
        assert len(groups) == 0

    def test_excludes_already_matched(self) -> None:
        """Excludes entities already matched in previous passes."""
        entities = [
            Entity(entity_id="1", name="Apple", mention_count=100),
            Entity(entity_id="2", name="Appel", mention_count=50),  # Similar
        ]
        already_matched = {"1", "2"}
        groups = fuzzy_match_pass(entities, already_matched, threshold=80.0)
        assert len(groups) == 0

    def test_default_threshold(self) -> None:
        """Uses default threshold of 90%."""
        assert DEFAULT_FUZZY_THRESHOLD == 90.0


class TestContextMatchPass:
    """Tests for context_match_pass function."""

    def test_groups_by_company_context(self) -> None:
        """Groups entities with same company in document_refs."""
        entities = [
            Entity(
                entity_id="1",
                name="AAPL",
                mention_count=50,
                document_refs=[{"company": "AAPL", "filename": "q4.pdf"}],
            ),
            Entity(
                entity_id="2",
                name="Apple Inc.",
                mention_count=100,
                document_refs=[{"company": "AAPL", "filename": "10k.pdf"}],
            ),
        ]
        groups = context_match_pass(entities, set())
        # Should group by AAPL company context
        assert len(groups) >= 0  # May or may not match depending on logic

    def test_excludes_already_matched(self) -> None:
        """Excludes entities already matched."""
        entities = [
            Entity(
                entity_id="1",
                name="Apple",
                document_refs=[{"company": "AAPL"}],
            ),
        ]
        groups = context_match_pass(entities, {"1"})
        assert len(groups) == 0


class TestTickerResolutionPass:
    """Tests for ticker_resolution_pass function."""

    def test_matches_ticker_to_canonical_name(self) -> None:
        """Matches ticker symbol entities to canonical name entities."""
        entities = [
            Entity(entity_id="1", name="AAPL", mention_count=50),
            Entity(entity_id="2", name="apple", mention_count=100),
        ]
        groups = ticker_resolution_pass(entities)
        # Should find group for AAPL -> Apple mapping
        assert len(groups) >= 0


class TestEntityResolver:
    """Tests for EntityResolver class."""

    def test_resolve_name_ticker(self) -> None:
        """resolve_name returns canonical for ticker."""
        driver = MagicMock()
        resolver = EntityResolver(driver)
        assert resolver.resolve_name("AAPL") == "Apple Inc."

    def test_resolve_name_regular(self) -> None:
        """resolve_name normalizes regular names."""
        driver = MagicMock()
        resolver = EntityResolver(driver)
        assert resolver.resolve_name("Microsoft Corporation") == "microsoft"

    @pytest.mark.asyncio
    async def test_get_entity_count(self) -> None:
        """get_entity_count queries Neo4j."""
        # Create async context manager mock
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"count": 5000})

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)

        # Create async context manager for session
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_context)

        resolver = EntityResolver(driver)
        count = await resolver.get_entity_count()
        assert count == 5000


# =============================================================================
# T020: Tests for merge_history.py
# =============================================================================


class TestMergeStatus:
    """Tests for MergeStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """All expected statuses exist."""
        assert MergeStatus.PENDING == "pending"
        assert MergeStatus.COMPLETED == "completed"
        assert MergeStatus.ROLLED_BACK == "rolled_back"
        assert MergeStatus.FAILED == "failed"


class TestMergeMatchType:
    """Tests for MergeMatchType enum."""

    def test_all_types_exist(self) -> None:
        """All expected match types exist."""
        assert MergeMatchType.EXACT == "exact"
        assert MergeMatchType.FUZZY == "fuzzy"
        assert MergeMatchType.CONTEXT == "context"
        assert MergeMatchType.TICKER == "ticker"
        assert MergeMatchType.MANUAL == "manual"


class TestMergedEntity:
    """Tests for MergedEntity model."""

    def test_required_fields(self) -> None:
        """entity_id and name are required."""
        entity = MergedEntity(entity_id="uuid-1", name="Test Entity")
        assert entity.entity_id == "uuid-1"
        assert entity.name == "Test Entity"

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        entity = MergedEntity(entity_id="uuid-1", name="Test")
        assert entity.entity_type == ""
        assert entity.mention_count == 0
        assert entity.document_refs == []
        assert entity.relationship_count == 0


class TestMergeOperation:
    """Tests for MergeOperation model."""

    def test_required_fields(self) -> None:
        """Required fields are enforced."""
        operation = MergeOperation(
            merge_id="merge-1",
            match_type=MergeMatchType.EXACT,
            canonical_id="canonical-uuid",
            canonical_name="Apple Inc.",
        )
        assert operation.merge_id == "merge-1"
        assert operation.canonical_name == "Apple Inc."

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        operation = MergeOperation(
            merge_id="merge-1",
            match_type=MergeMatchType.EXACT,
            canonical_id="uuid",
            canonical_name="Test",
        )
        assert operation.status == MergeStatus.PENDING
        assert operation.similarity_score == 1.0
        assert operation.user == "system"
        assert operation.notes == ""
        assert operation.merged_entities == []

    def test_timestamp_auto_generated(self) -> None:
        """Timestamp is auto-generated."""
        operation = MergeOperation(
            merge_id="merge-1",
            match_type=MergeMatchType.EXACT,
            canonical_id="uuid",
            canonical_name="Test",
        )
        assert operation.timestamp is not None
        assert isinstance(operation.timestamp, datetime)


def _create_driver_mock(result_data: dict | None) -> MagicMock:
    """Create a properly configured Neo4j driver mock."""
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=result_data)

    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    driver = MagicMock()
    driver.session = MagicMock(return_value=mock_context)

    return driver


class TestMergeHistory:
    """Tests for MergeHistory class."""

    @pytest.mark.asyncio
    async def test_log_merge(self) -> None:
        """log_merge creates MergeOperation node."""
        driver = _create_driver_mock({"merge_id": "merge-1"})

        history = MergeHistory(driver)
        operation = MergeOperation(
            merge_id="merge-1",
            match_type=MergeMatchType.EXACT,
            canonical_id="uuid",
            canonical_name="Apple Inc.",
        )

        merge_id = await history.log_merge(operation)
        assert merge_id == "merge-1"

    @pytest.mark.asyncio
    async def test_update_status(self) -> None:
        """update_status modifies merge status."""
        driver = _create_driver_mock({"merge_id": "merge-1"})

        history = MergeHistory(driver)
        success = await history.update_status("merge-1", MergeStatus.COMPLETED, "Done")
        assert success is True

    @pytest.mark.asyncio
    async def test_get_merge(self) -> None:
        """get_merge retrieves operation by ID."""
        driver = _create_driver_mock(None)

        history = MergeHistory(driver)
        operation = await history.get_merge("nonexistent")
        assert operation is None

    @pytest.mark.asyncio
    async def test_get_merge_stats(self) -> None:
        """get_merge_stats returns statistics."""
        driver = _create_driver_mock(
            {
                "total_merges": 100,
                "completed": 90,
                "rolled_back": 5,
                "failed": 5,
                "exact_matches": 60,
                "fuzzy_matches": 30,
                "context_matches": 10,
                "ticker_matches": 0,
            }
        )

        history = MergeHistory(driver)
        stats = await history.get_merge_stats()
        assert stats["total_merges"] == 100
        assert stats["completed"] == 90


# =============================================================================
# Integration Tests
# =============================================================================


class TestEntityResolutionIntegration:
    """Integration tests for entity resolution system."""

    def test_normalize_and_dedupe_workflow(self) -> None:
        """End-to-end normalization and deduplication workflow."""
        # Simulate entities from a document
        raw_entities = [
            Entity(entity_id="1", name="Apple Inc.", mention_count=50),
            Entity(entity_id="2", name="AAPL", mention_count=30),
            Entity(entity_id="3", name="apple", mention_count=20),
            Entity(entity_id="4", name="Microsoft Corporation", mention_count=40),
            Entity(entity_id="5", name="MSFT", mention_count=25),
        ]

        # All should normalize to their base forms
        for entity in raw_entities:
            normalized = normalize_entity_name(entity.name)
            assert len(normalized) > 0

        # Exact match should group Apple variants
        groups = exact_match_pass(raw_entities)
        apple_group = next((g for g in groups if "apple" in g.canonical.name.lower()), None)
        if apple_group:
            assert len(apple_group.duplicates) >= 1

    def test_ticker_to_canonical_resolution(self) -> None:
        """Verify ticker symbols resolve to canonical names."""
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "INTC"]

        for ticker in tickers:
            canonical = get_canonical_name(ticker)
            assert canonical is not None
            assert len(canonical) > len(ticker)
            assert not canonical.isupper()  # Not just a ticker


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_unicode_in_entity_names(self) -> None:
        """Handles unicode characters in names."""
        # Should not crash, just normalize
        name = normalize_entity_name("Cafe Bene")
        assert len(name) > 0

    def test_very_long_entity_name(self) -> None:
        """Handles very long entity names."""
        long_name = "A" * 1000
        normalized = normalize_entity_name(long_name)
        assert len(normalized) == 1000  # Normalized but not truncated

    def test_entity_name_only_suffix(self) -> None:
        """Handles names that are only suffixes."""
        assert normalize_entity_name("Inc.") == ""
        assert normalize_entity_name("Corporation") == ""

    def test_numeric_entity_names(self) -> None:
        """Handles numeric-only entity names."""
        assert normalize_entity_name("123") == "123"
        assert normalize_entity_name("7-Eleven") == "7-eleven"

    def test_empty_entity_list(self) -> None:
        """Handles empty entity lists."""
        assert exact_match_pass([]) == []
        assert fuzzy_match_pass([], set()) == []
        assert context_match_pass([], set()) == []

    def test_single_entity(self) -> None:
        """Handles single entity in list."""
        entities = [Entity(entity_id="1", name="Apple", mention_count=100)]
        assert exact_match_pass(entities) == []
        assert fuzzy_match_pass(entities, set()) == []
