from typing import Any, Dict, List
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from .memory_handler import MemoryHandler
from src.agent import super_agent


class MCPHandler(MemoryHandler):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.enable_mcp = config.get("enable_mcp", True)
    
    async def run_agent(
        self,
        user_input: str,
        message_history: List[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs
    ):
        if not self.enable_mcp:
            async for chunk in super().run_agent(
                user_input, message_history, http_client, **kwargs
            ):
                yield chunk
            return
        
        async with super_agent.run_mcp_servers():
            async for chunk in super().run_agent(
                user_input, message_history, http_client, **kwargs
            ):
                yield chunk