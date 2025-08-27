"""AI Agent module - Unified Super Agent."""

# Import the unified super-agent - THE ONLY AGENT
from .unified_agent import UnifiedAgentDeps, super_agent, run_unified_agent

# Keep base classes for type definitions
from .base import AgentResponse, BaseAgent

__all__ = [
    # The ONE agent to rule them all
    "super_agent",
    "UnifiedAgentDeps", 
    "run_unified_agent",
    
    # Base classes for typing
    "AgentResponse",
    "BaseAgent",
]
