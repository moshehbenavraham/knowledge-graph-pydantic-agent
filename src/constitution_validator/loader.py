"""
Constitution and ignore pattern loaders.

Handles parsing of:
- .specify/memory/constitution.md (governance document)
- .constitution-ignore (file exclusion patterns)
"""

import hashlib
import re
from pathlib import Path

import structlog

from .models import Constitution, ConstitutionalPrinciple, IgnoreConfiguration

logger = structlog.get_logger(__name__)


class ConstitutionLoadError(Exception):
    """Raised when constitution cannot be loaded or parsed."""

    pass


def load_constitution(file_path: Path = Path(".specify/memory/constitution.md")) -> Constitution:
    """
    Load and parse the constitution markdown file.

    Args:
        file_path: Path to constitution.md file

    Returns:
        Constitution instance with all principles loaded

    Raises:
        ConstitutionLoadError: If file missing, corrupted, or invalid schema
    """
    logger.info("Loading constitution", file_path=str(file_path))

    # Validate file exists
    if not file_path.exists():
        error_msg = (
            f"Constitution file not found at {file_path}\n"
            f"Expected location: .specify/memory/constitution.md\n"
            f"This file is required for validation. Please restore from git:\n"
            f"  git checkout .specify/memory/constitution.md"
        )
        logger.error("Constitution file missing", path=str(file_path))
        raise ConstitutionLoadError(error_msg)

    # Read file content
    try:
        raw_content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        error_msg = (
            f"Failed to read constitution file at {file_path}\n"
            f"Error: {e}\n"
            f"Ensure the file has read permissions and valid UTF-8 encoding."
        )
        logger.error("Constitution read failed", path=str(file_path), error=str(e))
        raise ConstitutionLoadError(error_msg) from e

    # Validate minimum content
    if len(raw_content) < 100:
        error_msg = (
            f"Constitution file at {file_path} is too short ({len(raw_content)} bytes)\n"
            f"File may be corrupted. Expected a complete constitution document (>100 bytes).\n"
            f"Please restore from git: git checkout .specify/memory/constitution.md"
        )
        logger.error("Constitution file too short", length=len(raw_content))
        raise ConstitutionLoadError(error_msg)

    # Compute checksum for caching
    checksum = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
    logger.debug("Constitution checksum computed", checksum=checksum[:8])

    # Extract version from HTML comment
    version = _extract_version(raw_content)
    if not version:
        error_msg = (
            f"Constitution version not found in {file_path}\n"
            f"Expected version in HTML comment like: Version Change: INITIAL → 1.0.0\n"
            f"File may be corrupted or in wrong format."
        )
        logger.error("Constitution version missing")
        raise ConstitutionLoadError(error_msg)

    # Extract all six principles
    principles = _extract_principles(raw_content, file_path)

    # Validate we got exactly 6 principles
    if len(principles) != 6:
        error_msg = (
            f"Constitution must have exactly 6 principles, found {len(principles)}\n"
            f"Expected principles: I, II, III, IV, V, VI\n"
            f"Found: {', '.join(p.principle_id for p in principles)}\n"
            f"Constitution file may be corrupted."
        )
        logger.error("Invalid principle count", count=len(principles))
        raise ConstitutionLoadError(error_msg)

    logger.info(
        "Constitution loaded successfully",
        version=version,
        principles=len(principles),
        checksum=checksum[:8],
    )

    return Constitution(
        file_path=file_path,
        version=version,
        principles=principles,
        raw_content=raw_content,
        checksum=checksum,
    )


def _extract_version(content: str) -> str | None:
    """
    Extract version from HTML comment block.

    Looks for pattern: Version Change: INITIAL → 1.0.0
    or: Version: 1.0.0
    """
    # Try "Version Change: X → Y" pattern
    match = re.search(r"Version Change:.*?→\s*(\d+\.\d+\.\d+)", content, re.MULTILINE)
    if match:
        return match.group(1)

    # Try simple "Version: X.Y.Z" pattern
    match = re.search(r"Version:\s*(\d+\.\d+\.\d+)", content, re.MULTILINE)
    if match:
        return match.group(1)

    return None


def _extract_principles(content: str, file_path: Path) -> list[ConstitutionalPrinciple]:
    """
    Extract all constitutional principles from markdown content.

    Principles are level 3 headings (###) with format:
    ### I. Principle Name

    Each principle has:
    - A bold statement (first paragraph)
    - Bullet points with details
    - **Rationale:** section explaining why
    """
    principles = []

    # Split content into sections by ### headings
    sections = re.split(r"^### ([IVX]+)\.\s+(.+)$", content, flags=re.MULTILINE)

    # sections[0] is content before first principle
    # Then groups of 3: (principle_id, name, content)
    for i in range(1, len(sections), 3):
        if i + 2 >= len(sections):
            break

        principle_id = sections[i].strip()
        name = sections[i + 1].strip()
        principle_content = sections[i + 2].strip()

        # Validate principle ID format
        if principle_id not in {"I", "II", "III", "IV", "V", "VI"}:
            logger.warning("Skipping invalid principle ID", principle_id=principle_id)
            continue

        # Extract description (everything before **Rationale:**)
        parts = re.split(r"\*\*Rationale:\*\*", principle_content, maxsplit=1)
        if len(parts) != 2:
            logger.warning(
                "Principle missing rationale section",
                principle_id=principle_id,
                name=name,
            )
            description = principle_content
            rationale = "No rationale provided."
        else:
            description = parts[0].strip()
            rationale = parts[1].strip()

        # Extract related files from bullet points (files mentioned with backticks)
        related_files = re.findall(r"`([^`]+\.py)`", description)

        logger.debug(
            "Principle extracted",
            principle_id=principle_id,
            name=name,
            related_files=len(related_files),
        )

        principles.append(
            ConstitutionalPrinciple(
                principle_id=principle_id,
                name=name,
                description=description,
                rationale=rationale,
                related_files=related_files,
            )
        )

    return principles


def load_ignore_configuration(
    file_path: Path = Path(".constitution-ignore"),
) -> IgnoreConfiguration:
    """
    Load ignore configuration from .constitution-ignore file.

    File format (gitignore-style):
        # Comment
        tests/              # Reason for ignoring
        *.generated.py
        .venv/

    Args:
        file_path: Path to .constitution-ignore file

    Returns:
        IgnoreConfiguration with parsed patterns
    """
    logger.info("Loading ignore configuration", file_path=str(file_path))

    if not file_path.exists():
        logger.info("No .constitution-ignore file found, using defaults only")
        return IgnoreConfiguration()

    # Use the model's from_file method (already implemented in models.py)
    config = IgnoreConfiguration.from_file(file_path)

    logger.info(
        "Ignore configuration loaded",
        custom_patterns=len(config.patterns),
        default_patterns=len(config.default_patterns),
        total_patterns=len(config.patterns) + len(config.default_patterns),
    )

    return config


# Class-based API for test compatibility
class ConstitutionLoader:
    """Wrapper class for constitution loading functionality."""

    @staticmethod
    def load(file_path: Path = Path(".specify/memory/constitution.md")) -> Constitution:
        """Load constitution from file."""
        return load_constitution(file_path)


class IgnoreConfigurationLoader:
    """Wrapper class for ignore configuration loading functionality."""

    @staticmethod
    def load(file_path: Path = Path(".constitution-ignore")) -> IgnoreConfiguration:
        """Load ignore configuration from file."""
        return load_ignore_configuration(file_path)
