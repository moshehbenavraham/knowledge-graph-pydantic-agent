"""Canonical name mappings and normalization for entity resolution.

This module provides:
- Company suffix normalization patterns (Inc., Corp., LLC, etc.)
- Ticker symbol to canonical name mappings
- Entity name normalization functions

The patterns handle common variations in company names to enable
accurate entity deduplication.
"""

import re
from typing import Final

import structlog

logger = structlog.get_logger(__name__)

# Company suffix patterns for normalization (T005)
# Order matters: longer patterns first to avoid partial matches
COMPANY_SUFFIXES: Final[tuple[str, ...]] = (
    # Full forms
    "incorporated",
    "corporation",
    "limited",
    "company",
    # Abbreviated forms with periods
    "inc.",
    "corp.",
    "ltd.",
    "llc.",
    "l.l.c.",
    "co.",
    "plc.",
    "p.l.c.",
    "n.v.",
    "s.a.",
    "a.g.",
    "gmbh",
    # Abbreviated forms without periods
    "inc",
    "corp",
    "ltd",
    "llc",
    "co",
    "plc",
    "nv",
    "sa",
    "ag",
)

# Build regex pattern for suffix removal
_SUFFIX_PATTERN = re.compile(
    r"\s*,?\s*(" + "|".join(re.escape(s) for s in COMPANY_SUFFIXES) + r")\s*$",
    re.IGNORECASE,
)

# Generic terms to exclude from fuzzy matching (T005)
# These are too common and would create false positive matches
EXCLUDED_TERMS: Final[frozenset[str]] = frozenset(
    {
        "the company",
        "company",
        "the board",
        "board",
        "management",
        "the management",
        "shareholders",
        "stockholders",
        "directors",
        "officers",
        "employees",
        "n/a",
        "na",
        "none",
        "other",
        "various",
        "unknown",
    }
)

# Ticker symbol to canonical company name mappings (T006)
# Based on common SEC filings and financial documents
TICKER_TO_CANONICAL: Final[dict[str, str]] = {
    # Technology
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "GOOG": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms Inc.",
    "NVDA": "NVIDIA Corporation",
    "INTC": "Intel Corporation",
    "AMD": "Advanced Micro Devices Inc.",
    "CRM": "Salesforce Inc.",
    "ORCL": "Oracle Corporation",
    "IBM": "International Business Machines Corporation",
    "CSCO": "Cisco Systems Inc.",
    "ADBE": "Adobe Inc.",
    "AVGO": "Broadcom Inc.",
    "QCOM": "Qualcomm Inc.",
    "TXN": "Texas Instruments Inc.",
    "AMAT": "Applied Materials Inc.",
    "MU": "Micron Technology Inc.",
    # Finance
    "JPM": "JPMorgan Chase & Co.",
    "BAC": "Bank of America Corporation",
    "WFC": "Wells Fargo & Company",
    "GS": "Goldman Sachs Group Inc.",
    "MS": "Morgan Stanley",
    "C": "Citigroup Inc.",
    "BLK": "BlackRock Inc.",
    "SCHW": "Charles Schwab Corporation",
    "AXP": "American Express Company",
    "V": "Visa Inc.",
    "MA": "Mastercard Inc.",
    # Healthcare
    "JNJ": "Johnson & Johnson",
    "UNH": "UnitedHealth Group Inc.",
    "PFE": "Pfizer Inc.",
    "ABBV": "AbbVie Inc.",
    "MRK": "Merck & Co. Inc.",
    "LLY": "Eli Lilly and Company",
    "TMO": "Thermo Fisher Scientific Inc.",
    "ABT": "Abbott Laboratories",
    "DHR": "Danaher Corporation",
    "BMY": "Bristol-Myers Squibb Company",
    # Consumer
    "WMT": "Walmart Inc.",
    "PG": "Procter & Gamble Company",
    "KO": "Coca-Cola Company",
    "PEP": "PepsiCo Inc.",
    "COST": "Costco Wholesale Corporation",
    "HD": "Home Depot Inc.",
    "NKE": "Nike Inc.",
    "MCD": "McDonald's Corporation",
    "SBUX": "Starbucks Corporation",
    "DIS": "Walt Disney Company",
    # Industrial
    "CAT": "Caterpillar Inc.",
    "BA": "Boeing Company",
    "HON": "Honeywell International Inc.",
    "GE": "General Electric Company",
    "MMM": "3M Company",
    "UPS": "United Parcel Service Inc.",
    "RTX": "Raytheon Technologies Corporation",
    "LMT": "Lockheed Martin Corporation",
    "DE": "Deere & Company",
    # Energy
    "XOM": "Exxon Mobil Corporation",
    "CVX": "Chevron Corporation",
    "COP": "ConocoPhillips",
    "SLB": "Schlumberger Limited",
    "EOG": "EOG Resources Inc.",
    # Telecom
    "T": "AT&T Inc.",
    "VZ": "Verizon Communications Inc.",
    "TMUS": "T-Mobile US Inc.",
}

# Reverse mapping for alias lookup
_CANONICAL_TO_TICKERS: dict[str, list[str]] = {}
for ticker, canonical in TICKER_TO_CANONICAL.items():
    _CANONICAL_TO_TICKERS.setdefault(canonical, []).append(ticker)


def normalize_entity_name(name: str) -> str:
    """Normalize an entity name for comparison.

    Performs the following normalizations:
    1. Strip leading/trailing whitespace
    2. Convert to lowercase
    3. Remove company suffixes (Inc., Corp., LLC, etc.)
    4. Collapse multiple spaces to single space
    5. Strip any remaining trailing punctuation

    Args:
        name: Raw entity name to normalize

    Returns:
        Normalized entity name for comparison

    Example:
        >>> normalize_entity_name("Apple Inc.")
        'apple'
        >>> normalize_entity_name("MICROSOFT CORPORATION")
        'microsoft'
        >>> normalize_entity_name("  Intel Corp.  ")
        'intel'
    """
    if not name:
        return ""

    # Strip and lowercase
    normalized = name.strip().lower()

    # Remove company suffixes (may need multiple passes for "Company, Inc.")
    for _ in range(3):  # Max 3 iterations to handle nested suffixes
        prev = normalized
        normalized = _SUFFIX_PATTERN.sub("", normalized)
        if prev == normalized:
            break

    # Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized)

    # Strip trailing punctuation and whitespace
    normalized = normalized.rstrip(".,;:-").strip()

    return normalized


def get_canonical_name(identifier: str) -> str | None:
    """Get canonical company name from ticker symbol or known alias.

    Checks if the identifier is a known ticker symbol and returns
    the canonical company name. Also handles common variations.

    Args:
        identifier: Ticker symbol or company name variant

    Returns:
        Canonical company name if found, None otherwise

    Example:
        >>> get_canonical_name("AAPL")
        'Apple Inc.'
        >>> get_canonical_name("aapl")
        'Apple Inc.'
        >>> get_canonical_name("UNKNOWN")
        None
    """
    if not identifier:
        return None

    # Try direct ticker lookup (case-insensitive)
    upper = identifier.strip().upper()
    if upper in TICKER_TO_CANONICAL:
        logger.debug("Ticker resolved to canonical", ticker=upper)
        return TICKER_TO_CANONICAL[upper]

    return None


def is_excluded_term(name: str) -> bool:
    """Check if an entity name is a generic excluded term.

    Generic terms like "The Company", "Management", "Board" should
    not be matched against other entities as they are too common
    and would create false positives.

    Args:
        name: Entity name to check

    Returns:
        True if the name should be excluded from matching
    """
    if not name:
        return True

    # Check both the raw lowercased name and normalized form
    raw_lower = name.strip().lower()
    normalized = normalize_entity_name(name)

    # Exclude if:
    # 1. Raw name matches an excluded term
    # 2. Normalized name matches an excluded term
    # 3. Normalized name is too short (< 2 chars)
    if raw_lower in EXCLUDED_TERMS:
        return True
    if normalized in EXCLUDED_TERMS:
        return True
    return len(normalized) < 2


def get_all_known_aliases(canonical_name: str) -> list[str]:
    """Get all known aliases for a canonical company name.

    Returns ticker symbols and the normalized form of the canonical name.

    Args:
        canonical_name: The canonical company name

    Returns:
        List of known aliases (tickers, normalized forms)
    """
    aliases = [canonical_name, normalize_entity_name(canonical_name)]

    # Add ticker symbols
    if canonical_name in _CANONICAL_TO_TICKERS:
        aliases.extend(_CANONICAL_TO_TICKERS[canonical_name])

    return list(set(aliases))
