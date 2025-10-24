"""AI Agent module - Unified Super Agent."""

# Import the unified super-agent - THE ONLY AGENT
from .unified_agent import UnifiedAgentDeps, run_unified_agent, super_agent

__all__ = [
    "UnifiedAgentDeps",
    "run_unified_agent",
    # The ONE agent to rule them all
    "super_agent",
]
