"""Validation rules for constitutional principles."""

from .base import BaseValidationRule
from .principle_i import UnifiedAgentRule
from .principle_ii import PrincipleIIRule
from .principle_iii import DualDatabaseRule
from .principle_iv import TestCoverageRule
from .principle_v import ObservabilityRule
from .principle_vi import GitAttributionRule

# Aliases for test compatibility
CentralizedConfigRule = PrincipleIIRule

__all__ = [
    "BaseValidationRule",
    "CentralizedConfigRule",  # Alias
    "DualDatabaseRule",
    "GitAttributionRule",
    "ObservabilityRule",
    "PrincipleIIRule",
    "TestCoverageRule",
    "UnifiedAgentRule",
]
