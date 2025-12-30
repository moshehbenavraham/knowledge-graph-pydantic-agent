"""
Numeric fact extraction from episode text.

Parses financial numeric values (currency amounts, percentages) from text
and returns structured NumericFact objects with normalized values for
range-based queries in the Neo4j knowledge graph.

This module provides:
- NumericFact Pydantic model for structured numeric data
- parse_numeric_facts function for extracting all numeric facts from text
- Regex patterns for currency, magnitude, and percentage formats

Example:
    >>> from src.agentic_rag.graph.numeric_parser import parse_numeric_facts
    >>> facts = parse_numeric_facts("Revenue was $40,665 million")
    >>> facts[0].value
    40665000000.0
    >>> facts[0].unit
    'USD'
"""

from __future__ import annotations

import re
from typing import Literal

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models (T004)
# =============================================================================


class NumericFact(BaseModel):
    """
    Extracted numeric fact from episode text.

    Represents a parsed numeric value with its normalized form, original text,
    and classification for storage in Neo4j Episode nodes.

    Attributes:
        value: Normalized value after magnitude conversion (e.g., 40665000000)
        raw_value: Value before magnitude normalization (e.g., 40665)
        unit: ISO currency code, "percent", or "number"
        magnitude: Magnitude string if present ("million", "billion", "thousand")
        original_text: Original matched text from source
        fact_type: Classification of the numeric fact

    Example:
        >>> fact = NumericFact(
        ...     value=40665000000.0,
        ...     raw_value=40665.0,
        ...     unit="USD",
        ...     magnitude="million",
        ...     original_text="$40,665 million",
        ...     fact_type="currency"
        ... )
    """

    value: float = Field(description="Normalized value after magnitude conversion")
    raw_value: float = Field(description="Value before magnitude normalization")
    unit: str = Field(description="ISO currency code, 'percent', or 'number'")
    magnitude: str | None = Field(
        default=None, description="Magnitude: million, billion, thousand, or None"
    )
    original_text: str = Field(description="Original matched text from source")
    fact_type: Literal["currency", "percentage", "number"] = Field(
        description="Classification of the numeric fact"
    )

    def to_dict(self) -> dict[str, float | str | None]:
        """
        Convert to dictionary for Neo4j JSON storage.

        Returns:
            Dictionary with all fields for Episode.numeric_facts property
        """
        return {
            "value": self.value,
            "raw_value": self.raw_value,
            "unit": self.unit,
            "magnitude": self.magnitude,
            "original_text": self.original_text,
            "fact_type": self.fact_type,
        }


# =============================================================================
# Constants (T008)
# =============================================================================


# Magnitude multipliers for normalization
MAGNITUDE_MAP: dict[str, float] = {
    "thousand": 1e3,
    "thousands": 1e3,
    "k": 1e3,
    "million": 1e6,
    "millions": 1e6,
    "m": 1e6,
    "billion": 1e9,
    "billions": 1e9,
    "b": 1e9,
    "trillion": 1e12,
    "trillions": 1e12,
    "t": 1e12,
}


# Currency symbol to ISO code mapping
CURRENCY_SYMBOL_MAP: dict[str, str] = {
    "$": "USD",
    "usd": "USD",
    "us$": "USD",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "gbp": "GBP",
    "pound": "GBP",
    "pounds": "GBP",
    "jpy": "JPY",
    "yen": "JPY",
    "cny": "CNY",
    "yuan": "CNY",
    "cad": "CAD",
    "aud": "AUD",
    "chf": "CHF",
}


# =============================================================================
# Regex Patterns (T005, T006, T007)
# =============================================================================


# Pattern 1: Currency with symbol and optional magnitude
# Matches: $40.6B, $40,665 million, USD 35 billion, EUR35B
# Groups: (currency_symbol, number, magnitude_suffix)
CURRENCY_PATTERN = re.compile(
    r"(?P<currency>[\$]|USD|EUR|GBP|JPY|CNY|CAD|AUD|CHF)\s*"
    r"(?P<number>[\d,]+(?:\.\d+)?)\s*"
    r"(?P<magnitude>thousand|thousands|million|millions|billion|billions|trillion|trillions|[KkMmBbTt])?",
    re.IGNORECASE,
)

# Pattern 2: Number with magnitude (no currency symbol)
# Matches: 40 billion, 35.6 million, 100K
# Groups: (number, magnitude)
MAGNITUDE_PATTERN = re.compile(
    r"(?<![.\d$])"  # Negative lookbehind to avoid matching currency amounts again
    r"(?P<number>[\d,]+(?:\.\d+)?)\s*"
    r"(?P<magnitude>thousand|thousands|million|millions|billion|billions|trillion|trillions)"
    r"(?:\s+(?P<currency>dollars|USD|EUR|GBP|euros|pounds))?",
    re.IGNORECASE,
)

# Pattern 3: Percentages
# Matches: 50%, 12.5%, 50 percent, 12.5 percent
# Groups: (number, percent_indicator)
PERCENTAGE_PATTERN = re.compile(
    r"(?P<number>[\d,]+(?:\.\d+)?)\s*" r"(?P<indicator>%|percent|percentage|pct)",
    re.IGNORECASE,
)


# =============================================================================
# Normalization Functions (T009, T010, T011)
# =============================================================================


def normalize_magnitude(value: float, magnitude: str | None) -> float:
    """
    Apply magnitude multiplier to a value.

    Args:
        value: The raw numeric value
        magnitude: Magnitude string (million, billion, etc.) or None

    Returns:
        Value multiplied by magnitude factor, or original value if no magnitude

    Example:
        >>> normalize_magnitude(40.665, "million")
        40665000.0
        >>> normalize_magnitude(35, "billion")
        35000000000.0
        >>> normalize_magnitude(100, None)
        100.0
    """
    if magnitude is None:
        return value

    magnitude_lower = magnitude.lower().strip()
    multiplier = MAGNITUDE_MAP.get(magnitude_lower, 1.0)

    return value * multiplier


def map_currency_symbol(symbol: str) -> str:
    """
    Map currency symbol or name to ISO code.

    Args:
        symbol: Currency symbol ($) or name (USD, dollar, euro)

    Returns:
        ISO 4217 currency code (USD, EUR, GBP, etc.)

    Example:
        >>> map_currency_symbol("$")
        'USD'
        >>> map_currency_symbol("EUR")
        'EUR'
        >>> map_currency_symbol("pounds")
        'GBP'
    """
    symbol_lower = symbol.lower().strip()

    # Check direct mapping
    if symbol_lower in CURRENCY_SYMBOL_MAP:
        return CURRENCY_SYMBOL_MAP[symbol_lower]

    # Handle special case for dollar sign
    if "$" in symbol:
        return "USD"

    # Check if already an ISO code (uppercase 3-letter)
    if len(symbol) == 3 and symbol.upper() in [
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CNY",
        "CAD",
        "AUD",
        "CHF",
    ]:
        return symbol.upper()

    # Default to USD for unrecognized (most common in financial docs)
    logger.debug("Unrecognized currency symbol, defaulting to USD", symbol=symbol)
    return "USD"


def parse_number_string(number_str: str) -> float:
    """
    Parse a number string with commas and decimals.

    Args:
        number_str: Number string like "40,665" or "40.665"

    Returns:
        Parsed float value

    Raises:
        ValueError: If string cannot be parsed as a number

    Example:
        >>> parse_number_string("40,665")
        40665.0
        >>> parse_number_string("40.665")
        40.665
    """
    # Remove commas (thousand separators)
    cleaned = number_str.replace(",", "")
    return float(cleaned)


def normalize_percentage(value: float) -> tuple[float, float]:
    """
    Normalize percentage to decimal form.

    Args:
        value: Raw percentage value (e.g., 50 for 50%)

    Returns:
        Tuple of (normalized_value, raw_value) where normalized is decimal

    Example:
        >>> normalize_percentage(50.0)
        (0.5, 50.0)
        >>> normalize_percentage(12.5)
        (0.125, 12.5)
    """
    return (value / 100.0, value)


# =============================================================================
# Pattern Extraction Functions (T012, T013)
# =============================================================================


def _extract_currency_facts(text: str) -> list[NumericFact]:
    """
    Extract currency-based numeric facts from text.

    Args:
        text: Input text to parse

    Returns:
        List of NumericFact objects for currency matches
    """
    facts: list[NumericFact] = []

    for match in CURRENCY_PATTERN.finditer(text):
        try:
            currency = match.group("currency")
            number_str = match.group("number")
            magnitude = match.group("magnitude")

            raw_value = parse_number_string(number_str)
            normalized_value = normalize_magnitude(raw_value, magnitude)
            unit = map_currency_symbol(currency)

            # Normalize magnitude string
            magnitude_normalized = None
            if magnitude:
                mag_lower = magnitude.lower()
                if mag_lower in ["k"]:
                    magnitude_normalized = "thousand"
                elif mag_lower in ["m"]:
                    magnitude_normalized = "million"
                elif mag_lower in ["b"]:
                    magnitude_normalized = "billion"
                elif mag_lower in ["t"]:
                    magnitude_normalized = "trillion"
                else:
                    # Remove trailing 's' for consistency
                    magnitude_normalized = mag_lower.rstrip("s")

            fact = NumericFact(
                value=normalized_value,
                raw_value=raw_value,
                unit=unit,
                magnitude=magnitude_normalized,
                original_text=match.group(0).strip(),
                fact_type="currency",
            )
            facts.append(fact)

            logger.debug(
                "Currency fact extracted",
                original=match.group(0).strip(),
                value=normalized_value,
                unit=unit,
            )

        except (ValueError, AttributeError) as e:
            logger.debug(
                "Failed to parse currency match",
                match=match.group(0),
                error=str(e),
            )
            continue

    return facts


def _extract_magnitude_facts(text: str, existing_spans: list[tuple[int, int]]) -> list[NumericFact]:
    """
    Extract magnitude-based numeric facts (without currency symbol).

    Args:
        text: Input text to parse
        existing_spans: List of (start, end) spans already matched by currency pattern

    Returns:
        List of NumericFact objects for magnitude matches
    """
    facts: list[NumericFact] = []

    for match in MAGNITUDE_PATTERN.finditer(text):
        # Skip if this span overlaps with an existing currency match
        span = (match.start(), match.end())
        if any(
            not (span[1] <= existing[0] or span[0] >= existing[1]) for existing in existing_spans
        ):
            continue

        try:
            number_str = match.group("number")
            magnitude = match.group("magnitude")
            currency = match.group("currency")

            raw_value = parse_number_string(number_str)
            normalized_value = normalize_magnitude(raw_value, magnitude)

            # Determine unit
            if currency:
                unit = map_currency_symbol(currency)
                fact_type: Literal["currency", "percentage", "number"] = "currency"
            else:
                unit = "number"
                fact_type = "number"

            # Normalize magnitude string
            magnitude_normalized = magnitude.lower().rstrip("s") if magnitude else None

            fact = NumericFact(
                value=normalized_value,
                raw_value=raw_value,
                unit=unit,
                magnitude=magnitude_normalized,
                original_text=match.group(0).strip(),
                fact_type=fact_type,
            )
            facts.append(fact)

            logger.debug(
                "Magnitude fact extracted",
                original=match.group(0).strip(),
                value=normalized_value,
            )

        except (ValueError, AttributeError) as e:
            logger.debug(
                "Failed to parse magnitude match",
                match=match.group(0),
                error=str(e),
            )
            continue

    return facts


def _extract_percentage_facts(
    text: str, existing_spans: list[tuple[int, int]]
) -> list[NumericFact]:
    """
    Extract percentage facts from text.

    Args:
        text: Input text to parse
        existing_spans: List of (start, end) spans already matched

    Returns:
        List of NumericFact objects for percentage matches
    """
    facts: list[NumericFact] = []

    for match in PERCENTAGE_PATTERN.finditer(text):
        # Skip if this span overlaps with an existing match
        span = (match.start(), match.end())
        if any(
            not (span[1] <= existing[0] or span[0] >= existing[1]) for existing in existing_spans
        ):
            continue

        try:
            number_str = match.group("number")
            raw_value = parse_number_string(number_str)
            normalized_value, _ = normalize_percentage(raw_value)

            fact = NumericFact(
                value=normalized_value,
                raw_value=raw_value,
                unit="percent",
                magnitude=None,
                original_text=match.group(0).strip(),
                fact_type="percentage",
            )
            facts.append(fact)

            logger.debug(
                "Percentage fact extracted",
                original=match.group(0).strip(),
                value=normalized_value,
                raw_value=raw_value,
            )

        except (ValueError, AttributeError) as e:
            logger.debug(
                "Failed to parse percentage match",
                match=match.group(0),
                error=str(e),
            )
            continue

    return facts


def parse_numeric_facts(text: str) -> list[NumericFact]:
    """
    Parse all numeric facts from episode text.

    Extracts currency amounts, magnitudes, and percentages from text
    using a priority-ordered pattern pipeline. Returns structured
    NumericFact objects suitable for Neo4j storage.

    Pattern priority (most specific first):
    1. Currency with magnitude: $40.6B, $40,665 million, EUR 35 billion
    2. Plain magnitude: 40 billion, 35.6 million (with optional trailing currency)
    3. Percentages: 50%, 12.5 percent

    Args:
        text: Episode text to parse for numeric facts

    Returns:
        List of NumericFact objects, empty list if no facts found

    Example:
        >>> facts = parse_numeric_facts("Revenue was $40,665 million, up 15%")
        >>> len(facts)
        2
        >>> facts[0].value
        40665000000.0
        >>> facts[0].fact_type
        'currency'
        >>> facts[1].value
        0.15
        >>> facts[1].fact_type
        'percentage'
    """
    if not text or not isinstance(text, str):
        logger.debug("parse_numeric_facts called with empty or invalid text")
        return []

    logger.debug("parse_numeric_facts called", text_length=len(text))

    all_facts: list[NumericFact] = []
    matched_spans: list[tuple[int, int]] = []

    # Step 1: Extract currency facts (highest priority)
    currency_facts = _extract_currency_facts(text)
    for fact in currency_facts:
        # Track the span (approximate - find the match in text)
        start = text.find(fact.original_text)
        if start >= 0:
            matched_spans.append((start, start + len(fact.original_text)))
    all_facts.extend(currency_facts)

    # Step 2: Extract magnitude facts (avoiding currency overlaps)
    magnitude_facts = _extract_magnitude_facts(text, matched_spans)
    for fact in magnitude_facts:
        start = text.find(fact.original_text)
        if start >= 0:
            matched_spans.append((start, start + len(fact.original_text)))
    all_facts.extend(magnitude_facts)

    # Step 3: Extract percentage facts (avoiding previous overlaps)
    percentage_facts = _extract_percentage_facts(text, matched_spans)
    all_facts.extend(percentage_facts)

    logger.info(
        "parse_numeric_facts completed",
        text_length=len(text),
        facts_found=len(all_facts),
        currency_count=len(currency_facts),
        magnitude_count=len(magnitude_facts),
        percentage_count=len(percentage_facts),
    )

    return all_facts


def extract_numeric_facts_json(text: str) -> list[dict[str, float | str | None]]:
    """
    Extract numeric facts and return as JSON-serializable dictionaries.

    Convenience function for direct Neo4j property storage.

    Args:
        text: Episode text to parse

    Returns:
        List of dictionaries ready for Neo4j Episode.numeric_facts property

    Example:
        >>> facts = extract_numeric_facts_json("Revenue was $40B")
        >>> facts[0]["value"]
        40000000000.0
        >>> facts[0]["unit"]
        'USD'
    """
    facts = parse_numeric_facts(text)
    return [fact.to_dict() for fact in facts]
