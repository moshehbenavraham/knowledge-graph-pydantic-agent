from collections.abc import AsyncIterator
from typing import Any

import structlog
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from src.agent import super_agent

from .memory_handler import MemoryHandler

logger = structlog.get_logger(__name__)


class MCPHandler(MemoryHandler):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.enable_mcp = config.get("enable_mcp", True)

    async def run_agent(  # type: ignore[override]
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        logger.info("=" * 80)
        logger.info(
            "MCPHandler.run_agent() - MCP-ENABLED streaming",
            user_input_length=len(user_input),
            message_history_count=len(message_history),
            enable_mcp=self.enable_mcp,
        )

        if not self.enable_mcp:
            logger.info("MCP disabled, delegating to parent MemoryHandler...")
            async for chunk in super().run_agent(
                user_input, message_history, http_client, **kwargs
            ):
                yield chunk
            logger.info("MCPHandler.run_agent() complete (MCP disabled)")
            return

        try:
            logger.info("MCP enabled, opening MCP context...")
            async with super_agent:
                logger.info("MCP context opened, delegating to MemoryHandler...")

                chunk_count = 0
                async for chunk in super().run_agent(
                    user_input, message_history, http_client, **kwargs
                ):
                    chunk_count += 1
                    yield chunk

                logger.info(
                    "MemoryHandler streaming complete inside MCP context", chunk_count=chunk_count
                )

            logger.info("MCP context closed successfully")
            logger.info("MCPHandler.run_agent() finished successfully", total_chunks=chunk_count)

        except Exception as e:
            logger.exception(
                "MCPHandler agent execution FAILED",
                error=str(e),
                error_type=type(e).__name__,
                enable_mcp=self.enable_mcp,
            )
            raise
