"""Base agent class for the AI agent system.

Note: This module contains legacy agent interfaces maintained for backward compatibility.
The unified agent (src/agent/unified_agent.py) should be used for new implementations.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class AgentResponse(BaseModel):
    """Response from the agent."""

    content: str
    metadata: dict[str, Any] | None = None
    sources: list[str] | None = None


# constitution-validator: disable (Principle I - legacy interface for backward compatibility)
class BaseAgent(ABC):
    """Abstract base class for AI agents.

    DEPRECATED: Use UnifiedAgentDeps and super_agent from src/agent/unified_agent.py instead.
    This class is maintained for backward compatibility only.
    """

    def __init__(self, name: str, temperature: float = 0.7):
        self.name = name
        self.temperature = temperature

    @abstractmethod
    async def process_message(
        self, message: str, context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """Process a message and return a response."""
        pass

    @abstractmethod
    async def reset_conversation(self) -> None:
        """Reset the conversation state."""
        pass
