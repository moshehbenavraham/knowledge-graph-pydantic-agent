"""
Temporal metadata parser for document filenames.

Extracts fiscal quarter, year, and company information from document filenames
following the pattern "YYYY QN TICKER.pdf" (e.g., "2023 Q3 INTC.pdf").

This module provides:
- TemporalMetadata dataclass for structured temporal data
- parse_filename function for extracting metadata from filenames
- get_company_name helper for ticker-to-company resolution
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Regex pattern for filename parsing: "YYYY QN TICKER.pdf"
# Captures: year (4 digits), quarter (Q1-Q4), ticker (uppercase letters)
# Handles variations: extra spaces, lowercase, with/without .pdf extension
FILENAME_PATTERN = re.compile(
    r"^\s*(\d{4})\s+[Qq]([1-4])\s+([A-Za-z]+)(?:\.pdf)?\s*$",
    re.IGNORECASE,
)

# Valid quarters
VALID_QUARTERS = {"1", "2", "3", "4"}


@dataclass(frozen=True)
class TemporalMetadata:
    """
    Structured temporal metadata extracted from document filenames.

    Attributes:
        fiscal_quarter: Quarter string (Q1, Q2, Q3, Q4) or None if not parseable
        fiscal_year: Year as integer or None if not parseable
        company_ticker: Stock ticker symbol (uppercase) or None if not parseable
        company_name: Full company name or None if ticker not mapped
        document_date: Combined date string in YYYY-QN format or None

    Example:
        >>> metadata = TemporalMetadata(
        ...     fiscal_quarter="Q3",
        ...     fiscal_year=2023,
        ...     company_ticker="INTC",
        ...     company_name="Intel Corporation",
        ...     document_date="2023-Q3"
        ... )
    """

    fiscal_quarter: str | None
    fiscal_year: int | None
    company_ticker: str | None
    company_name: str | None
    document_date: str | None

    def is_valid(self) -> bool:
        """
        Check if the metadata contains valid temporal information.

        Returns:
            True if fiscal_quarter, fiscal_year, and company_ticker are all present
        """
        return all(
            [
                self.fiscal_quarter is not None,
                self.fiscal_year is not None,
                self.company_ticker is not None,
            ]
        )

    def to_dict(self) -> dict[str, str | int | None]:
        """
        Convert metadata to dictionary for Neo4j property storage.

        Returns:
            Dictionary with all temporal fields
        """
        return {
            "fiscal_quarter": self.fiscal_quarter,
            "fiscal_year": self.fiscal_year,
            "company_ticker": self.company_ticker,
            "company_name": self.company_name,
            "document_date": self.document_date,
        }


def get_company_name(ticker: str) -> str | None:
    """
    Resolve stock ticker to company name.

    Uses the centralized TICKER_TO_COMPANY_MAP from settings.

    Args:
        ticker: Stock ticker symbol (case-insensitive)

    Returns:
        Company name or None if ticker not found in mapping

    Example:
        >>> get_company_name("AAPL")
        'Apple Inc.'
        >>> get_company_name("UNKNOWN")
        None
    """
    from src.config import get_settings

    settings = get_settings()
    return settings.get_company_name(ticker)


def parse_filename(filename: str) -> TemporalMetadata:
    """
    Parse document filename to extract temporal metadata.

    Handles the standard format "YYYY QN TICKER.pdf" and variations:
    - Case-insensitive matching
    - Extra whitespace tolerance
    - Optional .pdf extension

    Args:
        filename: Document filename to parse (e.g., "2023 Q3 INTC.pdf")

    Returns:
        TemporalMetadata with extracted values, or null fields if parsing fails

    Example:
        >>> metadata = parse_filename("2023 Q3 INTC.pdf")
        >>> metadata.fiscal_quarter
        'Q3'
        >>> metadata.fiscal_year
        2023
        >>> metadata.company_ticker
        'INTC'
        >>> metadata.document_date
        '2023-Q3'

    Edge Cases:
        >>> parse_filename("").fiscal_quarter is None
        True
        >>> parse_filename("invalid.pdf").fiscal_year is None
        True
        >>> parse_filename("2023 Q5 INTC.pdf").fiscal_quarter is None
        True
    """
    if not filename or not isinstance(filename, str):
        logger.debug("parse_filename called with empty or invalid filename", filename=filename)
        return TemporalMetadata(
            fiscal_quarter=None,
            fiscal_year=None,
            company_ticker=None,
            company_name=None,
            document_date=None,
        )

    # Strip and normalize filename
    filename = filename.strip()

    # Try to match the pattern
    match = FILENAME_PATTERN.match(filename)

    if not match:
        logger.debug(
            "Filename does not match expected pattern",
            filename=filename,
            pattern="YYYY QN TICKER.pdf",
        )
        return TemporalMetadata(
            fiscal_quarter=None,
            fiscal_year=None,
            company_ticker=None,
            company_name=None,
            document_date=None,
        )

    year_str, quarter_num, ticker = match.groups()

    # Validate quarter (should be 1-4)
    if quarter_num not in VALID_QUARTERS:
        logger.warning(
            "Invalid quarter in filename",
            filename=filename,
            quarter=quarter_num,
        )
        return TemporalMetadata(
            fiscal_quarter=None,
            fiscal_year=None,
            company_ticker=None,
            company_name=None,
            document_date=None,
        )

    # Parse year
    try:
        year = int(year_str)
        # Sanity check: year should be reasonable (1990-2100)
        if year < 1990 or year > 2100:
            logger.warning(
                "Year out of expected range",
                filename=filename,
                year=year,
            )
            return TemporalMetadata(
                fiscal_quarter=None,
                fiscal_year=None,
                company_ticker=None,
                company_name=None,
                document_date=None,
            )
    except ValueError:
        logger.warning(
            "Failed to parse year from filename",
            filename=filename,
            year_str=year_str,
        )
        return TemporalMetadata(
            fiscal_quarter=None,
            fiscal_year=None,
            company_ticker=None,
            company_name=None,
            document_date=None,
        )

    # Normalize ticker to uppercase
    ticker_upper = ticker.upper()

    # Build quarter string
    fiscal_quarter = f"Q{quarter_num}"

    # Build document date string
    document_date = f"{year}-Q{quarter_num}"

    # Resolve company name (may be None if ticker not in mapping)
    company_name = get_company_name(ticker_upper)

    logger.debug(
        "Filename parsed successfully",
        filename=filename,
        fiscal_quarter=fiscal_quarter,
        fiscal_year=year,
        company_ticker=ticker_upper,
        company_name=company_name,
        document_date=document_date,
    )

    return TemporalMetadata(
        fiscal_quarter=fiscal_quarter,
        fiscal_year=year,
        company_ticker=ticker_upper,
        company_name=company_name,
        document_date=document_date,
    )


def extract_temporal_properties(filename: str) -> dict[str, str | int | None]:
    """
    Extract temporal properties from filename for Neo4j node updates.

    Convenience function that parses a filename and returns properties
    ready for Neo4j SET operations.

    Args:
        filename: Document filename to parse

    Returns:
        Dictionary of temporal properties for Neo4j:
        - fiscal_quarter: str or None
        - fiscal_year: int or None
        - document_date: str or None
        - company: str or None (company name, not ticker)

    Example:
        >>> props = extract_temporal_properties("2023 Q3 INTC.pdf")
        >>> props["fiscal_quarter"]
        'Q3'
        >>> props["fiscal_year"]
        2023
        >>> props["company"]
        'Intel Corporation'
    """
    metadata = parse_filename(filename)

    return {
        "fiscal_quarter": metadata.fiscal_quarter,
        "fiscal_year": metadata.fiscal_year,
        "document_date": metadata.document_date,
        "company": metadata.company_name,
    }
