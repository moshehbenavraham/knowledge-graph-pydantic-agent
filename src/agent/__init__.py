"""AI Agent module - Unified Super Agent."""

# Import the unified super-agent - THE ONLY AGENT
# Keep base classes for type definitions
from .base import AgentResponse, BaseAgent
from .unified_agent import UnifiedAgentDeps, run_unified_agent, super_agent

__all__ = [
    # Base classes for typing
    "AgentResponse",
    "BaseAgent",
    "UnifiedAgentDeps",
    "run_unified_agent",
    # The ONE agent to rule them all
    "super_agent",
]
