"""
Command-line interface for Constitution Compliance Validator.

Entry point: constitution-validate
"""

import os
import subprocess  # nosec B404 - Required for git operations
import sys
from pathlib import Path
from typing import Any

import click
import structlog

from . import __version__

logger = structlog.get_logger(__name__)


def _get_staged_files() -> list[Path]:
    """
    Get list of staged Python files from git.

    Returns:
        List of staged Python file paths

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    try:
        result = subprocess.run(  # nosec B607 - git is a trusted executable
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            check=True,
        )

        staged_files = []
        for line in result.stdout.strip().split("\n"):
            if line and line.endswith(".py"):
                file_path = Path(line)
                if file_path.exists():
                    staged_files.append(file_path)

        logger.info("Staged files discovered", count=len(staged_files))
        return staged_files

    except subprocess.CalledProcessError as e:
        logger.error("Failed to get staged files", error=str(e))
        raise


def _check_bypass() -> bool:
    """
    Check if validation bypass is requested via environment variable.

    Returns:
        True if bypass is requested, False otherwise
    """
    bypass_value = os.environ.get("SKIP_CONSTITUTION_CHECK", "").lower()
    return bypass_value in ("1", "true", "yes", "on")


def _discover_files(
    project_root: Path,
    target_paths: tuple[Path, ...],
    ignore_config: Any,
) -> list[Path]:
    """
    Discover Python files to scan.

    Args:
        project_root: Root directory of the project
        target_paths: Specific paths to scan (empty = scan all)
        ignore_config: Ignore configuration for filtering

    Returns:
        List of Python file paths to scan
    """

    files = []

    if target_paths:
        # Scan specific paths
        for path in target_paths:
            if path.is_file() and path.suffix == ".py":
                if not ignore_config.should_ignore(path):
                    files.append(path)
            elif path.is_dir():
                # Recursively find Python files in directory
                for py_file in path.rglob("*.py"):
                    if not ignore_config.should_ignore(py_file):
                        files.append(py_file)
    else:
        # Scan entire project
        for py_file in project_root.rglob("*.py"):
            if not ignore_config.should_ignore(py_file):
                files.append(py_file)

    return sorted(set(files))  # Remove duplicates and sort


class DependencyCheckError(Exception):
    """Raised when required dependency is missing."""

    pass


def check_dependencies() -> None:
    """
    Validate that required dependencies are installed.

    Checks for:
    - pytest-cov (for coverage validation)
    - git (for commit message validation)

    Raises:
        DependencyCheckError: If required dependency missing with install instructions
    """
    logger.debug("Checking dependencies")

    # Check pytest-cov
    try:
        import coverage  # noqa: F401
    except ImportError:
        error_msg = (
            "ERROR: Required dependency 'coverage' not found\n\n"
            "The constitution validator requires pytest-cov for test coverage validation.\n\n"
            "Install with:\n"
            "  pip install coverage>=7.0.0\n\n"
            "Or install the full dev dependencies:\n"
            "  pip install -e .[dev]"
        )
        logger.error("coverage package not installed")
        raise DependencyCheckError(error_msg)

    # Check git
    import shutil

    if not shutil.which("git"):
        error_msg = (
            "ERROR: git not found in PATH\n\n"
            "The constitution validator requires git for commit message validation.\n\n"
            "Install git:\n"
            "  - Ubuntu/Debian: sudo apt-get install git\n"
            "  - macOS: brew install git\n"
            "  - Windows: https://git-scm.com/download/win\n\n"
            "Or skip git validation with --skip-git flag"
        )
        logger.error("git not found in PATH")
        raise DependencyCheckError(error_msg)

    # Check GitPython
    try:
        import git  # noqa: F401
    except ImportError:
        error_msg = (
            "ERROR: Required dependency 'GitPython' not found\n\n"
            "The constitution validator requires GitPython for commit validation.\n\n"
            "Install with:\n"
            "  pip install GitPython>=3.1.45"
        )
        logger.error("GitPython package not installed")
        raise DependencyCheckError(error_msg)

    logger.debug("All dependencies found")


@click.group()
@click.version_option(version=__version__)
def cli():
    """Constitution Compliance Validator.

    Validates code changes against constitutional principles:
    - I. Unified Agent Architecture
    - II. Type-Safe Centralized Configuration
    - III. Dual-Database Agentic RAG
    - IV. Test-Driven Quality Assurance
    - V. Production-Ready Observability
    - VI. Git Attribution & Contribution Standards
    """
    pass


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all checks performed, not just violations",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Show only violation counts (suitable for CI/CD)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be checked without full validation",
)
@click.option(
    "--format",
    type=click.Choice(["json", "text"], case_sensitive=False),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Write report to file instead of stdout",
)
@click.option(
    "--skip-git",
    is_flag=True,
    help="Skip git commit validation",
)
@click.option(
    "--skip-coverage",
    is_flag=True,
    help="Skip test coverage validation",
)
@click.option(
    "--staged",
    is_flag=True,
    help="Validate only staged files (git diff --cached) for pre-commit mode",
)
def validate(
    paths: tuple[Path, ...],
    verbose: bool,
    quiet: bool,
    dry_run: bool,
    format: str,
    output: Path | None,
    skip_git: bool,
    skip_coverage: bool,
    staged: bool,
):
    """
    Validate code against constitutional principles.

    If no PATHS provided, validates entire codebase.

    \b
    Examples:
      constitution-validate                     # Full codebase scan
      constitution-validate src/config/settings.py   # Specific file
      constitution-validate src/agent/ --verbose     # Directory with details
      constitution-validate --staged                  # Pre-commit mode (staged files only)
      constitution-validate --quiet                   # CI/CD mode (counts only)
      constitution-validate --dry-run                 # Show what would be checked
      constitution-validate --format text --output report.txt  # Text report

    \b
    Bypass (use sparingly):
      Set environment variable to skip validation:
        SKIP_CONSTITUTION_CHECK=1 git commit -m "WIP"

      WARNING: Violations must be fixed before PR merge!
    """
    try:
        # Check for bypass first (T051)
        if _check_bypass():
            logger.warning(
                "Constitution validation BYPASSED via SKIP_CONSTITUTION_CHECK environment variable",
                warning="Violations must be fixed before PR merge",
            )
            click.echo(
                "WARNING: Constitution validation bypassed via SKIP_CONSTITUTION_CHECK\n"
                "Violations must be fixed before PR merge!",
                err=True,
            )
            sys.exit(0)  # Allow bypass to proceed

        # Check dependencies first
        check_dependencies()

        import time
        import uuid
        from datetime import datetime

        from src.constitution_validator.loader import ConstitutionLoader, IgnoreConfigurationLoader
        from src.constitution_validator.models import (
            ComplianceReport,
            PrincipleViolationSummary,
            ViolationGroup,
        )
        from src.constitution_validator.reporter import ReportGenerator
        from src.constitution_validator.rules.principle_i import UnifiedAgentRule
        from src.constitution_validator.rules.principle_ii import CentralizedConfigRule
        from src.constitution_validator.rules.principle_iii import DualDatabaseRule
        from src.constitution_validator.rules.principle_iv import TestCoverageRule
        from src.constitution_validator.rules.principle_v import ObservabilityRule
        from src.constitution_validator.rules.principle_vi import GitAttributionRule
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        start_time = time.time()

        logger.info(
            "Starting constitution validation",
            version=__version__,
            paths=len(paths) if paths else "all",
            verbose=verbose,
            quiet=quiet,
            dry_run=dry_run,
            staged=staged,
        )

        # Determine project root
        project_root = Path.cwd()

        # Load constitution
        logger.info("Loading constitution")
        constitution_loader = ConstitutionLoader()
        constitution = constitution_loader.load()

        # Load ignore configuration
        logger.info("Loading ignore configuration")
        ignore_loader = IgnoreConfigurationLoader()
        ignore_config = ignore_loader.load()

        # Discover files to scan (T049: incremental mode)
        logger.info("Discovering Python files")
        if staged:
            # Incremental mode: only staged files
            logger.info("Incremental mode: scanning staged files only")
            files_to_scan = _get_staged_files()
            # Filter by ignore config
            files_to_scan = [f for f in files_to_scan if not ignore_config.should_ignore(f)]
        else:
            # Normal mode: all files or specified paths
            files_to_scan = _discover_files(project_root, paths, ignore_config)

        if dry_run:
            click.echo(f"Would scan {len(files_to_scan)} files:")
            for file_path in files_to_scan[:20]:  # Show first 20
                click.echo(f"  {file_path}")
            if len(files_to_scan) > 20:
                click.echo(f"  ... and {len(files_to_scan) - 20} more")
            sys.exit(0)

        logger.info("Files to scan", count=len(files_to_scan))

        # Initialize scanners and rules
        ast_scanner = ASTScanner()

        rules = {
            "I": UnifiedAgentRule(),
            "II": CentralizedConfigRule(),
            "III": DualDatabaseRule(),
            "IV": TestCoverageRule(),
            "V": ObservabilityRule(),
            "VI": GitAttributionRule(),
        }

        # Execute validation
        all_violations = []

        # AST-based rules (Principles I, II, III, V)
        for file_path in files_to_scan:
            logger.debug("Scanning file", file=str(file_path))

            tree = ast_scanner.parse_file(file_path)
            if tree is None:
                logger.warning("Failed to parse file", file=str(file_path))
                continue

            # Run AST-based rules
            for principle_id in ["I", "II", "III", "V"]:
                rule = rules[principle_id]
                try:
                    violations = rule.execute(tree, file_path)
                    all_violations.extend(violations)

                    if verbose and violations:
                        for v in violations:
                            click.echo(f"[{principle_id}] {v.location}: {v.message}")

                except Exception as e:
                    logger.error(f"Rule {principle_id} failed", file=str(file_path), error=str(e))

        # Coverage check (Principle IV)
        if not skip_coverage:
            logger.info("Checking test coverage")
            try:
                coverage_violations = rules["IV"].execute_coverage_check(project_root)
                all_violations.extend(coverage_violations)

                if verbose and coverage_violations:
                    for v in coverage_violations:
                        click.echo(f"[IV] {v.message}")

            except Exception as e:
                logger.error("Coverage check failed", error=str(e))

        # Git attribution check (Principle VI)
        if not skip_git:
            logger.info("Checking git commits")
            try:
                git_violations = rules["VI"].execute_git_check(project_root)
                all_violations.extend(git_violations)

                if verbose and git_violations:
                    for v in git_violations:
                        click.echo(f"[VI] {v.message}")

            except Exception as e:
                logger.error("Git check failed", error=str(e))

        # Calculate metrics
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # Separate suppressed violations
        active_violations = [v for v in all_violations if not v.suppressed]
        suppressed_violations = [v for v in all_violations if v.suppressed]

        # Group violations by principle
        violations_by_principle = {}
        for v in active_violations:
            if v.principle_id not in violations_by_principle:
                violations_by_principle[v.principle_id] = []
            violations_by_principle[v.principle_id].append(v)

        # Create principle summaries
        principle_summaries = []
        for principle in constitution.principles:
            violations = violations_by_principle.get(principle.principle_id, [])

            # Group by rule_id
            groups_by_rule = {}
            for v in violations:
                if v.rule_id not in groups_by_rule:
                    groups_by_rule[v.rule_id] = []
                groups_by_rule[v.rule_id].append(v)

            # Create violation groups
            violation_groups = []
            for rule_id, rule_violations in groups_by_rule.items():
                group = ViolationGroup(
                    rule_id=rule_id,
                    violation_type=(
                        rule_violations[0].message.split(":")[0]
                        if ":" in rule_violations[0].message
                        else "violation"
                    ),
                    locations=[v.location for v in rule_violations],
                    message_template=rule_violations[0].message,
                    remediation=rule_violations[0].remediation,
                    count=len(rule_violations),
                )
                violation_groups.append(group)

            summary = PrincipleViolationSummary(
                principle_id=principle.principle_id,
                principle_name=principle.name,
                violation_count=len(violations),
                violation_groups=violation_groups,
                compliant=(len(violations) == 0),
            )
            principle_summaries.append(summary)

        # Count by severity
        error_count = sum(1 for v in active_violations if v.severity == "error")
        warning_count = sum(1 for v in active_violations if v.severity == "warning")
        info_count = sum(1 for v in active_violations if v.severity == "info")

        # Create compliance report
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            validator_version=__version__,
            constitution_version=constitution.version,
            scanned_files=list(files_to_scan),
            scan_duration_ms=duration_ms,
            violations=active_violations,
            suppressed_violations=suppressed_violations,
            principle_summaries=principle_summaries,
            passed=(error_count == 0),
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
        )

        # Generate output
        reporter = ReportGenerator()

        if format == "json":
            report_output = reporter.generate_json(report)
        else:  # text
            report_output = reporter.generate_text(report)

        # Write output
        if output:
            output.write_text(report_output)
            if not quiet:
                click.echo(f"Report written to {output}")
        else:
            click.echo(report_output)

        # Summary for quiet mode
        if quiet:
            status = "PASSED" if report.passed else "FAILED"
            click.echo(f"{status}: {error_count} errors, {warning_count} warnings")

        # Exit with appropriate code
        exit_code = 0 if report.passed else 1
        logger.info("Validation complete", passed=report.passed, exit_code=exit_code)
        sys.exit(exit_code)

    except DependencyCheckError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Validation failed", error=str(e))
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


# Alias for programmatic use (e.g., in tests)
validate_constitution = validate


if __name__ == "__main__":
    main()
