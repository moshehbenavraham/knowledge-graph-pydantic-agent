"""
Data models for Constitution Compliance Validator.

All entities use Pydantic models for runtime validation and type safety.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, field_validator

# =============================================================================
# Enumerations
# =============================================================================


class RuleCategory(str, Enum):
    """Categories of validation rules."""

    ARCHITECTURE = "architecture"  # Principle I - Unified Agent
    CONFIGURATION = "configuration"  # Principle II - Centralized Config
    DATABASE = "database"  # Principle III - Dual-Database RAG
    TESTING = "testing"  # Principle IV - Test-Driven Quality
    OBSERVABILITY = "observability"  # Principle V - Logging/Metrics
    ATTRIBUTION = "attribution"  # Principle VI - Git Attribution


class ConfidenceLevel(str, Enum):
    """Confidence in violation detection accuracy."""

    HIGH = "high"  # >95% accurate (e.g., direct os.getenv() in src/)
    MEDIUM = "medium"  # 80-95% accurate (e.g., class named "Agent")
    LOW = "low"  # 60-80% accurate (e.g., missing logger in short function)


# =============================================================================
# Constitution Entities
# =============================================================================


class ConstitutionalPrinciple(BaseModel):
    """Individual principle within the constitution."""

    model_config = {"frozen": True}

    principle_id: str = Field(
        ..., description="Unique identifier (I, II, III, IV, V, VI)", pattern="^(I|II|III|IV|V|VI)$"
    )
    name: str = Field(
        ...,
        description="Principle name (e.g., 'Unified Agent Architecture')",
        min_length=5,
        max_length=100,
    )
    description: str = Field(
        ..., description="Full text description from constitution document", min_length=10
    )
    rationale: str = Field(
        ..., description="Why this principle exists (context for violations)", min_length=10
    )
    related_files: list[str] = Field(
        default_factory=list, description="Key files that implement this principle"
    )


class Constitution(BaseModel):
    """Complete constitution loaded from .specify/memory/constitution.md."""

    model_config = {"frozen": True}

    file_path: Path = Field(
        default=Path(".specify/memory/constitution.md"),
        description="Path to constitution markdown file",
    )
    version: str = Field(
        ...,
        description="Semantic version of constitution (from frontmatter)",
        pattern=r"^\d+\.\d+\.\d+$",
    )
    loaded_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when constitution was loaded"
    )
    principles: list[ConstitutionalPrinciple] = Field(
        ..., description="All six constitutional principles", min_length=6, max_length=6
    )
    raw_content: str = Field(..., description="Full markdown content for reference", min_length=100)
    checksum: str = Field(
        ...,
        description="SHA256 hash of constitution file (for cache invalidation)",
        pattern=r"^[a-f0-9]{64}$",
    )

    @field_validator("principles")
    @classmethod
    def validate_principle_ids(
        cls, principles: list[ConstitutionalPrinciple]
    ) -> list[ConstitutionalPrinciple]:
        """Ensure all six principles are present with correct IDs."""
        expected_ids = {"I", "II", "III", "IV", "V", "VI"}
        actual_ids = {p.principle_id for p in principles}

        if actual_ids != expected_ids:
            missing = expected_ids - actual_ids
            extra = actual_ids - expected_ids
            raise ValueError(f"Invalid principle IDs. Missing: {missing}, Extra: {extra}")

        return principles


# =============================================================================
# Validation Rule Entities
# =============================================================================


class ValidationRule(BaseModel):
    """A specific check for constitutional compliance."""

    model_config = {"frozen": True, "use_enum_values": True}

    rule_id: str = Field(
        ...,
        description="Unique rule identifier (e.g., 'CONST-II-001')",
        pattern=r"^CONST-(I|II|III|IV|V|VI)-\d{3}$",
    )
    principle_id: str = Field(
        ...,
        description="Which constitutional principle this checks",
        pattern="^(I|II|III|IV|V|VI)$",
    )
    category: RuleCategory = Field(..., description="High-level category for grouping")
    name: str = Field(..., description="Human-readable rule name", min_length=5, max_length=100)
    description: str = Field(..., description="What this rule checks for", min_length=10)
    violation_message_template: str = Field(
        ..., description="Template for violation message (uses {var} substitution)"
    )
    remediation_guidance: str = Field(
        ..., description="How to fix violations of this rule", min_length=20
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.HIGH, description="Expected accuracy of this rule"
    )
    enabled: bool = Field(default=True, description="Whether this rule is active")
    severity: Literal["error", "warning", "info"] = Field(
        default="error", description="How serious violations are"
    )

    # AST-based rules
    ast_node_types: list[str] | None = Field(
        default=None, description="AST node types to visit (e.g., ['Call', 'ClassDef'])"
    )

    # Pattern-based rules (git commits, file names)
    regex_pattern: str | None = Field(
        default=None, description="Regex pattern for text-based matching"
    )

    # File filtering
    included_paths: list[str] = Field(
        default_factory=lambda: ["src/**/*.py"], description="Glob patterns for files to check"
    )
    excluded_paths: list[str] = Field(
        default_factory=lambda: ["tests/**", ".venv/**"],
        description="Glob patterns for files to skip",
    )


class RuleRegistry(BaseModel):
    """Collection of all validation rules."""

    rules: list[ValidationRule] = Field(..., description="All registered validation rules")

    def get_by_principle(self, principle_id: str) -> list[ValidationRule]:
        """Get all rules for a specific principle."""
        return [r for r in self.rules if r.principle_id == principle_id]

    def get_enabled_rules(self) -> list[ValidationRule]:
        """Get only enabled rules."""
        return [r for r in self.rules if r.enabled]

    def get_by_id(self, rule_id: str) -> ValidationRule | None:
        """Get specific rule by ID."""
        return next((r for r in self.rules if r.rule_id == rule_id), None)


# =============================================================================
# Violation Record Entities
# =============================================================================


class ViolationLocation(BaseModel):
    """Precise location of a violation in source code."""

    file_path: Path = Field(..., description="Absolute or relative path to file")
    line_number: int = Field(..., description="Line number where violation occurs", ge=1)
    column_number: int | None = Field(default=None, description="Column offset (from AST)", ge=0)
    context_lines: str | None = Field(
        default=None, description="Surrounding code lines for context (5 lines)"
    )

    def __str__(self) -> str:
        """Human-readable location string."""
        if self.column_number is not None:
            return f"{self.file_path}:{self.line_number}:{self.column_number}"
        return f"{self.file_path}:{self.line_number}"


class ViolationRecord(BaseModel):
    """A detected violation of constitutional principles."""

    rule_id: str = Field(
        ...,
        description="Which rule detected this violation",
        pattern=r"^CONST-(I|II|III|IV|V|VI)-\d{3}$",
    )
    principle_id: str = Field(
        ..., description="Which principle was violated", pattern="^(I|II|III|IV|V|VI)$"
    )
    location: ViolationLocation = Field(..., description="Where the violation occurred")
    message: str = Field(..., description="Specific violation description", min_length=10)
    remediation: str = Field(..., description="How to fix this specific violation", min_length=10)
    confidence: ConfidenceLevel = Field(..., description="How confident we are in this detection")
    severity: Literal["error", "warning", "info"] = Field(
        ..., description="How serious this violation is"
    )

    # Additional context
    detected_code: str | None = Field(
        default=None, description="Exact code snippet that violated the rule"
    )
    suggested_fix: str | None = Field(default=None, description="Suggested code replacement")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Rule-specific extra data (e.g., AST node type)"
    )

    # Suppression support
    suppressed: bool = Field(
        default=False, description="Whether violation is suppressed via # noqa comment"
    )
    suppression_reason: str | None = Field(
        default=None, description="Reason from # noqa comment (if suppressed)"
    )

    def __str__(self) -> str:
        """Human-readable violation string."""
        suppressed_mark = " [SUPPRESSED]" if self.suppressed else ""
        return f"[{self.rule_id}] {self.location}: {self.message}{suppressed_mark}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "rule_id": self.rule_id,
            "principle_id": self.principle_id,
            "file": str(self.location.file_path),
            "line": self.location.line_number,
            "column": self.location.column_number,
            "message": self.message,
            "remediation": self.remediation,
            "confidence": self.confidence.value,
            "severity": self.severity,
            "detected_code": self.detected_code,
            "suggested_fix": self.suggested_fix,
            "suppressed": self.suppressed,
            "suppression_reason": self.suppression_reason,
            "metadata": self.metadata,
        }


class ViolationGroup(BaseModel):
    """Group of violations for the same rule/type."""

    rule_id: str = Field(..., description="Common rule ID")
    violation_type: str = Field(..., description="Human-readable type name")
    locations: list[ViolationLocation] = Field(
        default_factory=list, description="All locations where this violation occurs"
    )
    message_template: str = Field(..., description="Template message")
    remediation: str = Field(..., description="How to fix all instances")
    count: int = Field(..., description="Total violations of this type", ge=0)

    @field_validator("count", mode="after")
    @classmethod
    def validate_count_matches_locations(cls, count: int, info) -> int:
        """Ensure count matches number of locations."""
        locations = info.data.get("locations", [])
        if count != len(locations):
            raise ValueError(f"Count {count} != len(locations) {len(locations)}")
        return count


# =============================================================================
# Compliance Report Entities
# =============================================================================


class PrincipleViolationSummary(BaseModel):
    """Summary of violations for one principle."""

    principle_id: str = Field(..., pattern="^(I|II|III|IV|V|VI)$")
    principle_name: str = Field(..., min_length=5)
    violation_count: int = Field(..., ge=0)
    violation_groups: list[ViolationGroup] = Field(
        default_factory=list, description="Violations grouped by type"
    )
    compliant: bool = Field(..., description="Whether this principle passes")


class ComplianceReport(BaseModel):
    """Complete validation report for a codebase."""

    # Report metadata
    report_id: str = Field(
        ..., description="Unique report identifier (UUID)", pattern=r"^[a-f0-9-]{36}$"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this report was generated"
    )
    validator_version: str = Field(
        ...,
        description="Version of validator that produced this report",
        pattern=r"^\d+\.\d+\.\d+$",
    )
    constitution_version: str = Field(
        ..., description="Version of constitution used", pattern=r"^\d+\.\d+\.\d+$"
    )

    # Scan scope
    scanned_files: list[Path] = Field(..., description="All Python files that were scanned")
    excluded_files: list[Path] = Field(
        default_factory=list, description="Files excluded via .constitution-ignore"
    )
    scan_duration_ms: int = Field(..., description="Total validation time in milliseconds", ge=0)

    # Results
    violations: list[ViolationRecord] = Field(
        default_factory=list, description="All detected violations (unsuppressed only by default)"
    )
    suppressed_violations: list[ViolationRecord] = Field(
        default_factory=list, description="Violations suppressed via # noqa comments"
    )
    principle_summaries: list[PrincipleViolationSummary] = Field(
        default_factory=list, description="Per-principle violation summaries"
    )

    # Overall status
    passed: bool = Field(..., description="Whether validation passed (no errors)")
    error_count: int = Field(..., ge=0)
    warning_count: int = Field(..., ge=0)
    info_count: int = Field(..., ge=0)

    # Additional metrics
    coverage_percentage: float | None = Field(
        default=None, description="Test coverage % (from Principle IV check)", ge=0.0, le=100.0
    )
    unpushed_commits_checked: int | None = Field(
        default=None, description="Number of git commits checked (Principle VI)"
    )

    @computed_field
    @property
    def total_violations(self) -> int:
        """Total number of violations (excluding suppressed)."""
        return len(self.violations)

    @computed_field
    @property
    def scan_duration_seconds(self) -> float:
        """Scan duration in seconds."""
        return self.scan_duration_ms / 1000.0

    @field_validator("passed", mode="after")
    @classmethod
    def validate_passed_status(cls, passed: bool, info) -> bool:
        """Ensure passed status matches error count."""
        error_count = info.data.get("error_count", 0)
        if passed and error_count > 0:
            raise ValueError(f"Report marked as passed but has {error_count} errors")
        return passed

    def to_json_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "validator_version": self.validator_version,
            "constitution_version": self.constitution_version,
            "scan_summary": {
                "scanned_files": len(self.scanned_files),
                "excluded_files": len(self.excluded_files),
                "duration_ms": self.scan_duration_ms,
                "duration_seconds": self.scan_duration_seconds,
            },
            "results": {
                "passed": self.passed,
                "total_violations": self.total_violations,
                "error_count": self.error_count,
                "warning_count": self.warning_count,
                "info_count": self.info_count,
                "suppressed_count": len(self.suppressed_violations),
            },
            "coverage": {
                "percentage": self.coverage_percentage,
                "meets_minimum": (
                    self.coverage_percentage >= 75.0 if self.coverage_percentage else None
                ),
            },
            "git_attribution": {"commits_checked": self.unpushed_commits_checked},
            "violations_by_principle": [
                {
                    "principle_id": summary.principle_id,
                    "principle_name": summary.principle_name,
                    "compliant": summary.compliant,
                    "violation_count": summary.violation_count,
                    "violation_groups": [
                        {
                            "type": group.violation_type,
                            "count": group.count,
                            "message": group.message_template,
                            "remediation": group.remediation,
                            "locations": [str(loc) for loc in group.locations],
                        }
                        for group in summary.violation_groups
                    ],
                }
                for summary in self.principle_summaries
            ],
            "all_violations": [v.to_dict() for v in self.violations],
        }

    def print_summary(self) -> str:
        """Generate human-readable text summary."""
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            f"Constitution Compliance Report - {status}",
            f"Generated: {self.generated_at.isoformat()}",
            f"Scanned {len(self.scanned_files)} files in {self.scan_duration_seconds:.2f}s",
            "",
            f"Violations: {self.total_violations} total ({self.error_count} errors, {self.warning_count} warnings)",
            "",
        ]

        for summary in self.principle_summaries:
            status_icon = "✓" if summary.compliant else "✗"
            lines.append(
                f"{status_icon} Principle {summary.principle_id}: {summary.principle_name}"
            )
            lines.append(f"  {summary.violation_count} violations")

            for group in summary.violation_groups:
                lines.append(f"  - {group.violation_type}: {group.count} occurrences")

        return "\n".join(lines)


# =============================================================================
# Ignore Pattern Entities
# =============================================================================


class IgnorePattern(BaseModel):
    """A pattern for excluding files from validation."""

    pattern: str = Field(..., description="Gitignore-style glob pattern", min_length=1)
    reason: str | None = Field(default=None, description="Why this pattern is ignored")
    scope: Literal["global", "rule-specific"] = Field(
        default="global", description="Whether this applies to all rules or specific ones"
    )
    rule_ids: list[str] | None = Field(
        default=None, description="Specific rule IDs this applies to (if rule-specific)"
    )
    enabled: bool = Field(default=True, description="Whether this pattern is active")

    @field_validator("rule_ids", mode="after")
    @classmethod
    def validate_rule_specific_scope(cls, rule_ids: list[str] | None, info) -> list[str] | None:
        """Ensure rule_ids is set only for rule-specific scope."""
        scope = info.data.get("scope")
        if scope == "rule-specific" and not rule_ids:
            raise ValueError("rule_ids must be set for rule-specific scope")
        if scope == "global" and rule_ids:
            raise ValueError("rule_ids should not be set for global scope")
        return rule_ids


class IgnoreConfiguration(BaseModel):
    """Complete ignore configuration from .constitution-ignore."""

    patterns: list[IgnorePattern] = Field(default_factory=list, description="All ignore patterns")
    default_patterns: list[str] = Field(
        default_factory=lambda: [
            "tests/",
            ".venv/",
            "venv/",
            "__pycache__/",
            "*.pyc",
            ".git/",
            "vendor/",
            "*.egg-info/",
            "build/",
            "dist/",
        ],
        description="Built-in patterns always applied",
    )

    def compile_pathspec(self) -> Any:
        """Compile all patterns into a PathSpec for matching."""
        import pathspec

        all_patterns = self.default_patterns + [p.pattern for p in self.patterns if p.enabled]
        return pathspec.PathSpec.from_lines("gitwildmatch", all_patterns)

    def should_ignore(self, file_path: Path, rule_id: str | None = None) -> bool:
        """Check if a file should be ignored."""
        # Check global patterns
        spec = self.compile_pathspec()
        if spec.match_file(str(file_path)):
            return True

        # Check rule-specific patterns
        if rule_id:
            import pathspec

            rule_specific = [
                p
                for p in self.patterns
                if p.enabled and p.scope == "rule-specific" and rule_id in (p.rule_ids or [])
            ]
            if rule_specific:
                rule_spec = pathspec.PathSpec.from_lines(
                    "gitwildmatch", [p.pattern for p in rule_specific]
                )
                return rule_spec.match_file(str(file_path))

        return False

    @classmethod
    def from_file(cls, file_path: Path = Path(".constitution-ignore")) -> "IgnoreConfiguration":
        """Load ignore configuration from .constitution-ignore file."""
        if not file_path.exists():
            return cls()

        patterns = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Parse optional reason from comments
                reason = None
                if " # " in line:
                    pattern, reason = line.split(" # ", 1)
                else:
                    pattern = line

                patterns.append(
                    IgnorePattern(
                        pattern=pattern.strip(), reason=reason.strip() if reason else None
                    )
                )

        return cls(patterns=patterns)
