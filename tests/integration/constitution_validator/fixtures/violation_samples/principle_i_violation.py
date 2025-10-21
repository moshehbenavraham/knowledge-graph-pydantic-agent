"""
Example of Principle I violation: Multiple Agent Architecture.

VIOLATION: Creating a custom agent outside unified_agent.py
"""

from pydantic_ai import Agent


class CustomAgent:
    """
    ✗ VIOLATION: Custom agent implementation outside src/agent/unified_agent.py

    This violates Principle I: Unified Agent Architecture
    """

    def __init__(self):
        self.agent = Agent("openai:gpt-4")

    def run(self, prompt: str) -> str:
        """Run custom agent."""
        result = self.agent.run_sync(prompt)
        return result.data
