"""
AST-based Python code scanner.

Parses Python files into Abstract Syntax Trees for rule execution.
"""

import ast
import hashlib
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class ASTScanner:
    """Scanner for parsing Python files into AST trees."""

    def __init__(self, cache_size: int = 1024):
        """
        Initialize AST scanner with caching.

        Args:
            cache_size: Number of parsed ASTs to cache (default 1024)
        """
        logger.debug("Initializing ASTScanner", cache_size=cache_size)
        self.cache_size = cache_size
        self._parse_cache: dict[str, ast.AST] = {}

    def parse_file(self, file_path: Path) -> ast.AST | None:
        """
        Parse a Python file into an AST.

        Args:
            file_path: Path to the Python file

        Returns:
            Parsed AST tree, or None if parsing fails
        """
        logger.debug("Parsing file", file=str(file_path))
        try:
            # Read file content
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Generate cache key from file hash
            file_hash = self._hash_content(content)
            cache_key = f"{file_path}:{file_hash}"

            # Check cache
            if cache_key in self._parse_cache:
                logger.debug("ast_cache_hit", file=str(file_path))
                return self._parse_cache[cache_key]

            # Parse the file
            tree = ast.parse(content, filename=str(file_path))

            # Store in cache (with LRU eviction if needed)
            if len(self._parse_cache) >= self.cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self._parse_cache))
                del self._parse_cache[oldest_key]
                logger.debug("Cache eviction", evicted_key=oldest_key)

            self._parse_cache[cache_key] = tree

            logger.debug("ast_parsed", file=str(file_path), nodes=len(list(ast.walk(tree))))
            return tree

        except SyntaxError as e:
            logger.warning("syntax_error_in_file", file=str(file_path), line=e.lineno, error=str(e))
            return None

        except UnicodeDecodeError as e:
            logger.warning("encoding_error_in_file", file=str(file_path), error=str(e))
            return None

        except Exception as e:
            logger.error("failed_to_parse_file", file=str(file_path), error=str(e), exc_info=True)
            return None

    def _hash_content(self, content: str) -> str:
        """
        Generate SHA256 hash of file content for caching.

        Args:
            content: File content string

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def clear_cache(self):
        """Clear the AST parse cache."""
        self._parse_cache.clear()
        logger.info("ast_cache_cleared")

    def get_cache_stats(
        self,
    ) -> dict[str, Any]:  # Constitution exception: CONST-V-001 - Simple stats accessor
        """
        Get cache statistics.

        Returns:
            Dictionary with cache size and capacity
        """
        return {
            "cache_size": len(self._parse_cache),
            "cache_capacity": self.cache_size,
            "cache_usage_percent": (len(self._parse_cache) / self.cache_size) * 100,
        }
