"""
Document reference model for tracking entity-document relationships.

This module provides the DocumentReference Pydantic model used to store
structured metadata about which documents reference each entity in Neo4j.
"""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DocumentReference(BaseModel):
    """
    Represents a reference from an entity to a source document.

    Stores structured metadata extracted from document filenames and metadata,
    enabling cross-document entity queries like "Which entities appear in
    multiple documents?" or "Show entities from Q4 2024 filings."

    Attributes:
        filename: Source document filename (sanitized, ASCII-only)
        company: Company ticker or name extracted from filename (e.g., 'INTC')
        quarter: Fiscal quarter if applicable (e.g., 'Q1', 'Q2', 'Q3', 'Q4')
        year: Fiscal year if applicable (e.g., 2024)
        mention_count: Number of times entity is mentioned in this document
    """

    filename: str = Field(..., description="Source document filename")
    company: str | None = Field(default=None, description="Company ticker or name")
    quarter: str | None = Field(default=None, description="Fiscal quarter (Q1-Q4)")
    year: int | None = Field(default=None, description="Fiscal year")
    mention_count: int = Field(default=1, ge=1, description="Mention count in document")

    @field_validator("filename")
    @classmethod
    def sanitize_filename(cls, v: str) -> str:
        """Sanitize filename to ASCII-only characters."""
        # Remove non-ASCII characters
        sanitized = v.encode("ascii", errors="ignore").decode("ascii")
        # Replace problematic characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", sanitized)
        return sanitized.strip() or "unknown"

    @field_validator("quarter")
    @classmethod
    def validate_quarter(cls, v: str | None) -> str | None:
        """Validate quarter format."""
        if v is None:
            return None
        v_upper = v.upper().strip()
        if v_upper in ("Q1", "Q2", "Q3", "Q4"):
            return v_upper
        return None

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int | None) -> int | None:
        """Validate year is reasonable."""
        if v is None:
            return None
        if 1900 <= v <= 2100:
            return v
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Neo4j storage."""
        return {
            "filename": self.filename,
            "company": self.company,
            "quarter": self.quarter,
            "year": self.year,
            "mention_count": self.mention_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentReference":
        """Create DocumentReference from dictionary."""
        return cls(
            filename=data.get("filename", "unknown"),
            company=data.get("company"),
            quarter=data.get("quarter"),
            year=data.get("year"),
            mention_count=data.get("mention_count", 1),
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on filename (for deduplication)."""
        if not isinstance(other, DocumentReference):
            return False
        return self.filename == other.filename

    def __hash__(self) -> int:
        """Hash based on filename for set operations."""
        return hash(self.filename)


def extract_document_metadata(
    source: str,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> DocumentReference:
    """
    Extract document metadata from source path and metadata.

    Parses filenames like 'INTC_Q4_2024.pdf' or 'AMD_annual_report_2023.pdf'
    to extract company, quarter, and year information.

    Args:
        source: Document source path or filename
        title: Optional document title
        metadata: Optional additional metadata dict

    Returns:
        DocumentReference with extracted metadata
    """
    # Extract filename from path
    filename = source.split("/")[-1].split("\\")[-1]

    # Initialize extraction values
    company = None
    quarter = None
    year = None

    # Check metadata first for explicit values
    if metadata:
        company = metadata.get("company")
        quarter = metadata.get("quarter")
        year_val = metadata.get("year")
        if isinstance(year_val, int):
            year = year_val
        elif isinstance(year_val, str) and year_val.isdigit():
            year = int(year_val)

    # Extract from filename if not in metadata
    # Pattern: COMPANY_Q#_YEAR or COMPANY_YEAR_Q# or variations
    filename_upper = filename.upper()

    # Extract company (first word-like segment, typically ticker)
    if company is None:
        company_match = re.match(r"^([A-Z]{2,5})[-_\s]", filename_upper)
        if company_match:
            company = company_match.group(1)

    # Extract quarter
    if quarter is None:
        quarter_match = re.search(r"(Q[1-4])", filename_upper)
        if quarter_match:
            quarter = quarter_match.group(1)

    # Extract year
    if year is None:
        year_match = re.search(r"(20\d{2}|19\d{2})", filename)
        if year_match:
            year = int(year_match.group(1))

    return DocumentReference(
        filename=filename,
        company=company,
        quarter=quarter,
        year=year,
        mention_count=1,
    )
