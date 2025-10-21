# Data Model: Constitution Compliance Validator

**Feature**: Constitution Compliance Validator
**Date**: 2025-10-21
**Status**: Draft

## Overview

This document defines the core data entities for the Constitution Compliance Validator system. All entities use Pydantic models for runtime validation and type safety, following Python 3.11+ type hint conventions.

---

## Entity Definitions

### 1. Constitution

**Purpose**: Represents the loaded constitutional document that defines all governance principles and rules.

**Type**: `Constitution`

```python
from typing import List, Dict, Optional
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class ConstitutionalPrinciple(BaseModel):
    """Individual principle within the constitution."""

    principle_id: str = Field(
        ...,
        description="Unique identifier (I, II, III, IV, V, VI)",
        pattern="^(I|II|III|IV|V|VI)$"
    )
    name: str = Field(
        ...,
        description="Principle name (e.g., 'Unified Agent Architecture')",
        min_length=5,
        max_length=100
    )
    description: str = Field(
        ...,
        description="Full text description from constitution document",
        min_length=10
    )
    rationale: str = Field(
        ...,
        description="Why this principle exists (context for violations)",
        min_length=10
    )
    related_files: List[str] = Field(
        default_factory=list,
        description="Key files that implement this principle"
    )

    class Config:
        frozen = True  # Principles are immutable once loaded


class Constitution(BaseModel):
    """Complete constitution loaded from .specify/memory/constitution.md."""

    file_path: Path = Field(
        default=Path(".specify/memory/constitution.md"),
        description="Path to constitution markdown file"
    )
    version: str = Field(
        ...,
        description="Semantic version of constitution (from frontmatter)",
        pattern=r"^\d+\.\d+\.\d+$"
    )
    loaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when constitution was loaded"
    )
    principles: List[ConstitutionalPrinciple] = Field(
        ...,
        description="All six constitutional principles",
        min_length=6,
        max_length=6
    )
    raw_content: str = Field(
        ...,
        description="Full markdown content for reference",
        min_length=100
    )
    checksum: str = Field(
        ...,
        description="SHA256 hash of constitution file (for cache invalidation)",
        pattern=r"^[a-f0-9]{64}$"
    )

    @field_validator('principles')
    @classmethod
    def validate_principle_ids(cls, principles: List[ConstitutionalPrinciple]) -> List[ConstitutionalPrinciple]:
        """Ensure all six principles are present with correct IDs."""
        expected_ids = {"I", "II", "III", "IV", "V", "VI"}
        actual_ids = {p.principle_id for p in principles}

        if actual_ids != expected_ids:
            missing = expected_ids - actual_ids
            extra = actual_ids - expected_ids
            raise ValueError(
                f"Invalid principle IDs. Missing: {missing}, Extra: {extra}"
            )

        return principles

    class Config:
        frozen = True  # Constitution is immutable once loaded
```

**Relationships**:
- Has 6 `ConstitutionalPrinciple` entities (composition)
- Referenced by all `ValidationRule` entities

**Validation Rules**:
- Must have exactly 6 principles with IDs I-VI
- Version must follow semantic versioning (x.y.z)
- File must be readable and contain at least 100 characters
- Checksum must be valid SHA256 hex string

**State Transitions**:
- N/A (immutable once loaded)

---

### 2. ValidationRule

**Purpose**: Defines a specific check that detects violations of a constitutional principle.

**Type**: `ValidationRule`

```python
from typing import Callable, Literal, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class RuleCategory(str, Enum):
    """Categories of validation rules."""
    ARCHITECTURE = "architecture"      # Principle I - Unified Agent
    CONFIGURATION = "configuration"    # Principle II - Centralized Config
    DATABASE = "database"              # Principle III - Dual-Database RAG
    TESTING = "testing"                # Principle IV - Test-Driven Quality
    OBSERVABILITY = "observability"    # Principle V - Logging/Metrics
    ATTRIBUTION = "attribution"        # Principle VI - Git Attribution


class ConfidenceLevel(str, Enum):
    """Confidence in violation detection accuracy."""
    HIGH = "high"      # >95% accurate (e.g., direct os.getenv() in src/)
    MEDIUM = "medium"  # 80-95% accurate (e.g., class named "Agent")
    LOW = "low"        # 60-80% accurate (e.g., missing logger in short function)


class ValidationRule(BaseModel):
    """A specific check for constitutional compliance."""

    rule_id: str = Field(
        ...,
        description="Unique rule identifier (e.g., 'CONST-II-001')",
        pattern=r"^CONST-(I|II|III|IV|V|VI)-\d{3}$"
    )
    principle_id: str = Field(
        ...,
        description="Which constitutional principle this checks",
        pattern="^(I|II|III|IV|V|VI)$"
    )
    category: RuleCategory = Field(
        ...,
        description="High-level category for grouping"
    )
    name: str = Field(
        ...,
        description="Human-readable rule name",
        min_length=5,
        max_length=100,
        examples=["Detect direct os.getenv() usage"]
    )
    description: str = Field(
        ...,
        description="What this rule checks for",
        min_length=10,
        examples=["Detects direct environment variable access via os.getenv() or os.environ"]
    )
    violation_message_template: str = Field(
        ...,
        description="Template for violation message (uses {var} substitution)",
        examples=["Direct os.getenv() call found at {file}:{line}"]
    )
    remediation_guidance: str = Field(
        ...,
        description="How to fix violations of this rule",
        min_length=20,
        examples=["Use get_settings() from src/config/settings.py instead"]
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.HIGH,
        description="Expected accuracy of this rule"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this rule is active"
    )
    severity: Literal["error", "warning", "info"] = Field(
        default="error",
        description="How serious violations are"
    )

    # AST-based rules
    ast_node_types: Optional[List[str]] = Field(
        default=None,
        description="AST node types to visit (e.g., ['Call', 'ClassDef'])",
        examples=[["Call"], ["ClassDef", "FunctionDef"]]
    )

    # Pattern-based rules (git commits, file names)
    regex_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern for text-based matching",
        examples=[r"Co-Authored-By:.*Claude"]
    )

    # File filtering
    included_paths: List[str] = Field(
        default_factory=lambda: ["src/**/*.py"],
        description="Glob patterns for files to check"
    )
    excluded_paths: List[str] = Field(
        default_factory=lambda: ["tests/**", ".venv/**"],
        description="Glob patterns for files to skip"
    )

    class Config:
        frozen = True  # Rules are immutable once defined
        use_enum_values = True


class RuleRegistry(BaseModel):
    """Collection of all validation rules."""

    rules: List[ValidationRule] = Field(
        ...,
        description="All registered validation rules"
    )

    def get_by_principle(self, principle_id: str) -> List[ValidationRule]:
        """Get all rules for a specific principle."""
        return [r for r in self.rules if r.principle_id == principle_id]

    def get_enabled_rules(self) -> List[ValidationRule]:
        """Get only enabled rules."""
        return [r for r in self.rules if r.enabled]

    def get_by_id(self, rule_id: str) -> Optional[ValidationRule]:
        """Get specific rule by ID."""
        return next((r for r in self.rules if r.rule_id == rule_id), None)
```

**Relationships**:
- References one `ConstitutionalPrinciple` (via `principle_id`)
- Produces multiple `ViolationRecord` entities when executed
- Grouped by `RuleCategory` for reporting

**Validation Rules**:
- `rule_id` must follow format `CONST-{principle_id}-{number}`
- `principle_id` must match one of I-VI
- At least one of `ast_node_types` or `regex_pattern` must be set
- `included_paths` and `excluded_paths` must be valid glob patterns

**State Transitions**:
- Enabled ↔ Disabled (via configuration updates)

---

### 3. ViolationRecord

**Purpose**: Captures a single detected violation of a constitutional principle.

**Type**: `ViolationRecord`

```python
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

class ViolationLocation(BaseModel):
    """Precise location of a violation in source code."""

    file_path: Path = Field(
        ...,
        description="Absolute or relative path to file"
    )
    line_number: int = Field(
        ...,
        description="Line number where violation occurs",
        ge=1
    )
    column_number: Optional[int] = Field(
        default=None,
        description="Column offset (from AST)",
        ge=0
    )
    context_lines: Optional[str] = Field(
        default=None,
        description="Surrounding code lines for context (5 lines)"
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
        pattern=r"^CONST-(I|II|III|IV|V|VI)-\d{3}$"
    )
    principle_id: str = Field(
        ...,
        description="Which principle was violated",
        pattern="^(I|II|III|IV|V|VI)$"
    )
    location: ViolationLocation = Field(
        ...,
        description="Where the violation occurred"
    )
    message: str = Field(
        ...,
        description="Specific violation description",
        min_length=10,
        examples=["Direct os.getenv('API_KEY') call found"]
    )
    remediation: str = Field(
        ...,
        description="How to fix this specific violation",
        min_length=10
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="How confident we are in this detection"
    )
    severity: Literal["error", "warning", "info"] = Field(
        ...,
        description="How serious this violation is"
    )

    # Additional context
    detected_code: Optional[str] = Field(
        default=None,
        description="Exact code snippet that violated the rule",
        examples=["os.getenv('API_KEY')"]
    )
    suggested_fix: Optional[str] = Field(
        default=None,
        description="Suggested code replacement",
        examples=["get_settings().api_key"]
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Rule-specific extra data (e.g., AST node type)"
    )

    # Suppression support
    suppressed: bool = Field(
        default=False,
        description="Whether violation is suppressed via # noqa comment"
    )
    suppression_reason: Optional[str] = Field(
        default=None,
        description="Reason from # noqa comment (if suppressed)"
    )

    @field_validator('location', mode='after')
    @classmethod
    def validate_file_exists(cls, location: ViolationLocation) -> ViolationLocation:
        """Ensure file exists (catches AST parsing errors early)."""
        if not location.file_path.exists():
            raise ValueError(f"File does not exist: {location.file_path}")
        return location

    def __str__(self) -> str:
        """Human-readable violation string."""
        suppressed_mark = " [SUPPRESSED]" if self.suppressed else ""
        return f"[{self.rule_id}] {self.location}: {self.message}{suppressed_mark}"

    def to_dict(self) -> Dict[str, Any]:
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
            "metadata": self.metadata
        }


class ViolationGroup(BaseModel):
    """Group of violations for the same rule/type."""

    rule_id: str = Field(..., description="Common rule ID")
    violation_type: str = Field(..., description="Human-readable type name")
    locations: List[ViolationLocation] = Field(
        default_factory=list,
        description="All locations where this violation occurs"
    )
    message_template: str = Field(..., description="Template message")
    remediation: str = Field(..., description="How to fix all instances")
    count: int = Field(..., description="Total violations of this type", ge=0)

    @field_validator('count', mode='after')
    @classmethod
    def validate_count_matches_locations(cls, count: int, info) -> int:
        """Ensure count matches number of locations."""
        locations = info.data.get('locations', [])
        if count != len(locations):
            raise ValueError(f"Count {count} != len(locations) {len(locations)}")
        return count
```

**Relationships**:
- References one `ValidationRule` (via `rule_id`)
- References one `ConstitutionalPrinciple` (via `principle_id`)
- Contains one `ViolationLocation`
- Aggregated into `ViolationGroup` for reporting
- Included in `ComplianceReport`

**Validation Rules**:
- `rule_id` must match existing `ValidationRule.rule_id`
- `principle_id` must match I-VI
- `line_number` must be >= 1
- File at `location.file_path` must exist
- If `suppressed=True`, `suppression_reason` should be set

**State Transitions**:
- Active → Suppressed (via `# noqa` comment)
- Suppressed → Active (if comment removed)

---

### 4. ComplianceReport

**Purpose**: Aggregates all validation results into a structured report.

**Type**: `ComplianceReport`

```python
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, computed_field

class PrincipleViolationSummary(BaseModel):
    """Summary of violations for one principle."""

    principle_id: str = Field(
        ...,
        pattern="^(I|II|III|IV|V|VI)$"
    )
    principle_name: str = Field(..., min_length=5)
    violation_count: int = Field(..., ge=0)
    violation_groups: List[ViolationGroup] = Field(
        default_factory=list,
        description="Violations grouped by type"
    )
    compliant: bool = Field(..., description="Whether this principle passes")


class ComplianceReport(BaseModel):
    """Complete validation report for a codebase."""

    # Report metadata
    report_id: str = Field(
        ...,
        description="Unique report identifier (UUID)",
        pattern=r"^[a-f0-9-]{36}$"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this report was generated"
    )
    validator_version: str = Field(
        ...,
        description="Version of validator that produced this report",
        pattern=r"^\d+\.\d+\.\d+$"
    )
    constitution_version: str = Field(
        ...,
        description="Version of constitution used",
        pattern=r"^\d+\.\d+\.\d+$"
    )

    # Scan scope
    scanned_files: List[Path] = Field(
        ...,
        description="All Python files that were scanned"
    )
    excluded_files: List[Path] = Field(
        default_factory=list,
        description="Files excluded via .constitution-ignore"
    )
    scan_duration_ms: int = Field(
        ...,
        description="Total validation time in milliseconds",
        ge=0
    )

    # Results
    violations: List[ViolationRecord] = Field(
        default_factory=list,
        description="All detected violations (unsuppressed only by default)"
    )
    suppressed_violations: List[ViolationRecord] = Field(
        default_factory=list,
        description="Violations suppressed via # noqa comments"
    )
    principle_summaries: List[PrincipleViolationSummary] = Field(
        default_factory=list,
        description="Per-principle violation summaries"
    )

    # Overall status
    passed: bool = Field(
        ...,
        description="Whether validation passed (no errors)"
    )
    error_count: int = Field(..., ge=0)
    warning_count: int = Field(..., ge=0)
    info_count: int = Field(..., ge=0)

    # Additional metrics
    coverage_percentage: Optional[float] = Field(
        default=None,
        description="Test coverage % (from Principle IV check)",
        ge=0.0,
        le=100.0
    )
    unpushed_commits_checked: Optional[int] = Field(
        default=None,
        description="Number of git commits checked (Principle VI)"
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

    @field_validator('passed', mode='after')
    @classmethod
    def validate_passed_status(cls, passed: bool, info) -> bool:
        """Ensure passed status matches error count."""
        error_count = info.data.get('error_count', 0)
        if passed and error_count > 0:
            raise ValueError(f"Report marked as passed but has {error_count} errors")
        return passed

    def to_json_dict(self) -> Dict[str, Any]:
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
                "duration_seconds": self.scan_duration_seconds
            },
            "results": {
                "passed": self.passed,
                "total_violations": self.total_violations,
                "error_count": self.error_count,
                "warning_count": self.warning_count,
                "info_count": self.info_count,
                "suppressed_count": len(self.suppressed_violations)
            },
            "coverage": {
                "percentage": self.coverage_percentage,
                "meets_minimum": self.coverage_percentage >= 75.0 if self.coverage_percentage else None
            },
            "git_attribution": {
                "commits_checked": self.unpushed_commits_checked
            },
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
                            "locations": [
                                str(loc) for loc in group.locations
                            ]
                        }
                        for group in summary.violation_groups
                    ]
                }
                for summary in self.principle_summaries
            ],
            "all_violations": [
                v.to_dict() for v in self.violations
            ]
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
            ""
        ]

        for summary in self.principle_summaries:
            status_icon = "✓" if summary.compliant else "✗"
            lines.append(f"{status_icon} Principle {summary.principle_id}: {summary.principle_name}")
            lines.append(f"  {summary.violation_count} violations")

            for group in summary.violation_groups:
                lines.append(f"  - {group.violation_type}: {group.count} occurrences")

        return "\n".join(lines)
```

**Relationships**:
- Contains multiple `ViolationRecord` entities
- Contains multiple `PrincipleViolationSummary` entities (one per principle)
- Each summary contains multiple `ViolationGroup` entities
- References `Constitution` (via `constitution_version`)

**Validation Rules**:
- `passed` must be `False` if `error_count > 0`
- `total_violations` must equal `len(violations)`
- `principle_summaries` must have exactly 6 entries (one per principle)
- All violation records must have valid `rule_id` and `principle_id`
- `scan_duration_ms` must be non-negative
- If `coverage_percentage` is set, must be 0-100

**State Transitions**:
- N/A (immutable once generated)

---

### 5. IgnorePattern

**Purpose**: Defines file paths or patterns to exclude from validation.

**Type**: `IgnorePattern`

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field
import pathspec

class IgnorePattern(BaseModel):
    """A pattern for excluding files from validation."""

    pattern: str = Field(
        ...,
        description="Gitignore-style glob pattern",
        min_length=1,
        examples=["tests/", "*.generated.py", ".venv/**"]
    )
    reason: Optional[str] = Field(
        default=None,
        description="Why this pattern is ignored",
        examples=["Test files", "Generated code", "Third-party dependencies"]
    )
    scope: Literal["global", "rule-specific"] = Field(
        default="global",
        description="Whether this applies to all rules or specific ones"
    )
    rule_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific rule IDs this applies to (if rule-specific)",
        examples=[["CONST-II-001", "CONST-II-002"]]
    )
    enabled: bool = Field(
        default=True,
        description="Whether this pattern is active"
    )

    @field_validator('rule_ids', mode='after')
    @classmethod
    def validate_rule_specific_scope(cls, rule_ids: Optional[List[str]], info) -> Optional[List[str]]:
        """Ensure rule_ids is set only for rule-specific scope."""
        scope = info.data.get('scope')
        if scope == 'rule-specific' and not rule_ids:
            raise ValueError("rule_ids must be set for rule-specific scope")
        if scope == 'global' and rule_ids:
            raise ValueError("rule_ids should not be set for global scope")
        return rule_ids


class IgnoreConfiguration(BaseModel):
    """Complete ignore configuration from .constitution-ignore."""

    patterns: List[IgnorePattern] = Field(
        default_factory=list,
        description="All ignore patterns"
    )
    default_patterns: List[str] = Field(
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
            "dist/"
        ],
        description="Built-in patterns always applied"
    )

    def compile_pathspec(self) -> pathspec.PathSpec:
        """Compile all patterns into a PathSpec for matching."""
        all_patterns = self.default_patterns + [
            p.pattern for p in self.patterns if p.enabled
        ]
        return pathspec.PathSpec.from_lines('gitwildmatch', all_patterns)

    def should_ignore(self, file_path: Path, rule_id: Optional[str] = None) -> bool:
        """Check if a file should be ignored."""
        # Check global patterns
        spec = self.compile_pathspec()
        if spec.match_file(str(file_path)):
            return True

        # Check rule-specific patterns
        if rule_id:
            rule_specific = [
                p for p in self.patterns
                if p.enabled and p.scope == 'rule-specific' and rule_id in (p.rule_ids or [])
            ]
            if rule_specific:
                rule_spec = pathspec.PathSpec.from_lines(
                    'gitwildmatch',
                    [p.pattern for p in rule_specific]
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
                if not line or line.startswith('#'):
                    continue

                # Parse optional reason from comments
                reason = None
                if ' # ' in line:
                    pattern, reason = line.split(' # ', 1)
                else:
                    pattern = line

                patterns.append(IgnorePattern(
                    pattern=pattern.strip(),
                    reason=reason.strip() if reason else None
                ))

        return cls(patterns=patterns)
```

**Relationships**:
- Referenced by `ValidationRule` (via `excluded_paths`)
- Used by validation engine to filter files before scanning
- Can be rule-specific (references `ValidationRule.rule_id`)

**Validation Rules**:
- Pattern must be valid gitignore-style glob
- If `scope='rule-specific'`, `rule_ids` must be non-empty
- If `scope='global'`, `rule_ids` must be empty/None

**State Transitions**:
- Enabled ↔ Disabled (via configuration updates)

---

## Entity Relationships Diagram

```
Constitution
    ├── ConstitutionalPrinciple (6)
    │   └── referenced_by → ValidationRule (many)
    │
    └── version → ComplianceReport.constitution_version

ValidationRule
    ├── principle_id → ConstitutionalPrinciple
    ├── produces → ViolationRecord (many)
    ├── excluded_paths → IgnorePattern
    └── grouped_by → RuleCategory

ViolationRecord
    ├── rule_id → ValidationRule
    ├── principle_id → ConstitutionalPrinciple
    ├── location → ViolationLocation
    ├── grouped_into → ViolationGroup
    └── included_in → ComplianceReport

ComplianceReport
    ├── violations → ViolationRecord (many)
    ├── principle_summaries → PrincipleViolationSummary (6)
    │   └── violation_groups → ViolationGroup (many)
    └── constitution_version → Constitution.version

IgnorePattern
    ├── referenced_by → ValidationRule.excluded_paths
    └── optional → rule_ids → ValidationRule.rule_id (many)
```

---

## Data Flow

1. **Startup**: Load `Constitution` from `.specify/memory/constitution.md`
2. **Configuration**: Load `RuleRegistry` with all `ValidationRule` entities
3. **File Discovery**: Scan codebase, apply `IgnoreConfiguration` filters
4. **Rule Execution**: Each rule produces 0+ `ViolationRecord` entities
5. **Grouping**: Violations grouped by `principle_id` and `rule_id` into `ViolationGroup`
6. **Aggregation**: All results aggregated into `ComplianceReport`
7. **Output**: Report serialized to JSON via `ComplianceReport.to_json_dict()`

---

## Inline Suppression Format

Violations can be suppressed using special comments:

```python
# noqa: CONSTITUTION-II - Migration compatibility wrapper
db_client = Neo4jDriver(uri, auth)  # noqa: CONST-III-001 - Integration test fixture
```

**Parsing**:
- Pattern: `# noqa: CONST-{principle}-{number} - {reason}`
- Sets `ViolationRecord.suppressed=True`
- Stores reason in `ViolationRecord.suppression_reason`

---

## Example JSON Report Structure

```json
{
  "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "generated_at": "2025-10-21T10:30:45.123Z",
  "validator_version": "1.0.0",
  "constitution_version": "1.0.0",
  "scan_summary": {
    "scanned_files": 145,
    "excluded_files": 89,
    "duration_ms": 18234,
    "duration_seconds": 18.234
  },
  "results": {
    "passed": false,
    "total_violations": 12,
    "error_count": 8,
    "warning_count": 4,
    "info_count": 0,
    "suppressed_count": 3
  },
  "coverage": {
    "percentage": 78.5,
    "meets_minimum": true
  },
  "violations_by_principle": [
    {
      "principle_id": "II",
      "principle_name": "Centralized Configuration",
      "compliant": false,
      "violation_count": 5,
      "violation_groups": [
        {
          "type": "direct_os_getenv",
          "count": 5,
          "message": "Direct os.getenv() usage detected",
          "remediation": "Use get_settings() from src/config/settings.py",
          "locations": [
            "src/tools/example.py:45:12",
            "src/api/routes.py:78:8",
            "src/utils/helper.py:23:4"
          ]
        }
      ]
    }
  ]
}
```

---

## Performance Considerations

### Lazy Loading
- `Constitution.raw_content`: Only loaded if needed for detailed reports
- `ViolationRecord.context_lines`: Optional, only populated in verbose mode

### Caching
- `Constitution.checksum`: Enables AST cache invalidation
- Parsed AST trees cached by file hash (LRU cache, 1024 entries)

### Batch Processing
- `ViolationRecord` entities created in bulk per file
- Grouped into `ViolationGroup` before final `ComplianceReport` construction

### Memory Limits
- Maximum violations per report: 10,000 (prevent OOM on large codebases)
- Context lines limited to 5 lines before/after violation

---

## Version History

- **v1.0.0** (2025-10-21): Initial data model design
