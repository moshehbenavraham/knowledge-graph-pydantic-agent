#!/usr/bin/env python3
"""
Documentation Link Validator

Validates all markdown links in the documentation to ensure:
- Internal links point to existing files
- Relative paths are correct
- No broken references

Usage:
    python scripts/validate_docs.py [--fix]
"""

import re
from collections import defaultdict
from pathlib import Path


class LinkValidator:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.docs_dir = root_dir / "docs"
        self.broken_links: list[tuple[str, str, str]] = []
        self.link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    def find_markdown_files(self) -> list[Path]:
        """Find all markdown files in the project."""
        # Root level markdown files
        root_files = list(self.root_dir.glob("*.md"))

        # All markdown files in docs/
        docs_files = list(self.docs_dir.rglob("*.md"))

        return sorted(root_files + docs_files)

    def extract_links(self, file_path: Path) -> list[tuple[str, str, int]]:
        """Extract all markdown links from a file.

        Returns:
            List of (link_text, link_url, line_number) tuples
        """
        links = []
        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    matches = self.link_pattern.findall(line)
                    for text, url in matches:
                        links.append((text, url, line_num))
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")

        return links

    def resolve_link(self, source_file: Path, link_url: str) -> tuple[bool, str]:
        """Resolve a link and check if the target exists.

        Returns:
            (exists: bool, resolved_path: str)
        """
        # Skip external links
        if link_url.startswith(("http://", "https://", "mailto:", "tel:")):
            return True, link_url

        # Skip anchors only
        if link_url.startswith("#"):
            return True, link_url

        # Remove anchor from URL for file existence check
        url_without_anchor = link_url.split("#")[0]

        if not url_without_anchor:
            # Pure anchor link
            return True, link_url

        # Resolve relative path
        source_dir = source_file.parent
        target_path = source_dir / url_without_anchor

        try:
            resolved = target_path.resolve()
            exists = resolved.exists()
            return exists, str(resolved.relative_to(self.root_dir))
        except Exception:
            return False, url_without_anchor

    def validate_file(self, file_path: Path) -> list[dict]:
        """Validate all links in a file.

        Returns:
            List of broken link dictionaries
        """
        broken = []
        links = self.extract_links(file_path)

        for text, url, line_num in links:
            # Skip external links for now (would need network requests)
            if url.startswith(("http://", "https://")):
                continue

            exists, resolved = self.resolve_link(file_path, url)

            if not exists:
                broken.append(
                    {
                        "file": str(file_path.relative_to(self.root_dir)),
                        "line": line_num,
                        "text": text,
                        "url": url,
                        "resolved": resolved,
                    }
                )

        return broken

    def validate_all(self) -> dict[str, list[dict]]:
        """Validate all markdown files.

        Returns:
            Dictionary mapping file paths to lists of broken links
        """
        all_broken = defaultdict(list)

        md_files = self.find_markdown_files()
        print(f"\n🔍 Validating {len(md_files)} markdown files...\n")

        for file_path in md_files:
            broken = self.validate_file(file_path)
            if broken:
                all_broken[str(file_path.relative_to(self.root_dir))] = broken

        return dict(all_broken)

    def print_report(self, broken_links: dict[str, list[dict]]):
        """Print a formatted report of broken links."""
        if not broken_links:
            print("✅ No broken links found!\n")
            return

        total_broken = sum(len(links) for links in broken_links.values())
        print(f"❌ Found {total_broken} broken links in {len(broken_links)} files:\n")

        for file_path, links in sorted(broken_links.items()):
            print(f"\n📄 {file_path}:")
            for link in links:
                print(f"   Line {link['line']}: [{link['text']}]({link['url']})")
                print(f"   → Resolved to: {link['resolved']}")

        print()

    def suggest_fixes(self, broken_links: dict[str, list[dict]]):
        """Suggest fixes for common broken link patterns."""
        print("\n💡 Suggested Fixes:\n")

        suggestions = {
            "docs/CONFIGURATION.md": "docs/4-configuration/environment.md or docs/2-getting-started/configuration.md",
            "docs/DEPLOYMENT.md": "docs/6-deployment/general.md",
            "docs/INSTALL.md": "docs/2-getting-started/installation.md",
            "docs/TROUBLESHOOTING.md": "docs/10-troubleshooting/index.md",
            "../operations/RUNBOOKS/": "../runbooks/ (wrong directory structure)",
            "../../observability/ALERTS.md": "../observability/alerts.md",
            "../../ARCHITECTURE.md": "../3-architecture/index.md",
            "docs/DB_AND_RAG.md": "docs/3-architecture/database-and-rag.md",
        }

        for old_path, new_path in suggestions.items():
            print(f"  {old_path}")
            print(f"  → {new_path}\n")


def main():
    root_dir = Path(__file__).parent.parent
    validator = LinkValidator(root_dir)

    print("=" * 70)
    print(" DOCUMENTATION LINK VALIDATION REPORT")
    print("=" * 70)

    broken_links = validator.validate_all()
    validator.print_report(broken_links)

    if broken_links:
        validator.suggest_fixes(broken_links)
        print("=" * 70)
        print(
            f"Summary: {sum(len(links) for links in broken_links.values())} broken links need fixing"
        )
        print("=" * 70)
        return 1
    print("=" * 70)
    print("All documentation links are valid! ✅")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
