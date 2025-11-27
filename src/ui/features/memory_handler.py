from collections.abc import AsyncIterator
from typing import Any

import structlog
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from src.clients import get_mem0_client

from .streaming_handler import StreamingHandler

logger = structlog.get_logger(__name__)


class MemoryHandler(StreamingHandler):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.memory_client: Any = None
        self.user_id = config.get("user_id", "streamlit_user")

    def _setup_hook(self) -> None:
        logger.info(
            "MemoryHandler._setup_hook() called",
            enable_memory=self.config.get("enable_memory", True),
            user_id=self.user_id,
        )

        super()._setup_hook()

        if self.config.get("enable_memory", True):
            try:
                logger.info("Initializing Mem0 client for memory management...")
                self.memory_client = get_mem0_client()
                logger.info("Mem0 client initialized successfully", user_id=self.user_id)
            except Exception as e:
                logger.exception(
                    "Failed to initialize Mem0 client", error=str(e), error_type=type(e).__name__
                )
                self.memory_client = None
        else:
            logger.info("Memory disabled in config, skipping Mem0 client initialization")

    def get_memories(self, query: str) -> str:
        logger.debug(
            "MemoryHandler.get_memories() called",
            query_length=len(query),
            query_preview=query[:50] + "..." if len(query) > 50 else query,
            has_memory_client=self.memory_client is not None,
        )

        if not self.memory_client:
            logger.debug("No memory client available, returning empty memories")
            return ""

        try:
            memory_limit = self.config.get("memory_limit", 3)
            logger.debug(
                "Searching Mem0 for relevant memories", user_id=self.user_id, limit=memory_limit
            )

            relevant_memories = self.memory_client.search(
                query=query, user_id=self.user_id, limit=memory_limit
            )

            results = relevant_memories.get("results", [])
            memory_count = len(results)

            memories_str = "\n".join(f"- {entry['memory']}" for entry in results)
            memories_length = len(memories_str)

            logger.info(
                "Memories retrieved successfully",
                memory_count=memory_count,
                memories_length=memories_length,
                user_id=self.user_id,
            )

            if memory_count > 0:
                logger.debug(
                    "Memory content preview",
                    first_memory=(
                        results[0].get("memory", "")[:100] + "..."
                        if results[0].get("memory", "")
                        else "empty"
                    ),
                )

            return memories_str

        except Exception as e:
            logger.exception(
                "Failed to retrieve memories from Mem0",
                error=str(e),
                error_type=type(e).__name__,
                user_id=self.user_id,
            )
            return ""

    def add_memory(self, user_input: str, agent_response: str | None = None) -> None:
        logger.debug(
            "MemoryHandler.add_memory() called",
            user_input_length=len(user_input),
            has_agent_response=agent_response is not None,
            agent_response_length=len(agent_response) if agent_response else 0,
            has_memory_client=self.memory_client is not None,
        )

        if not self.memory_client:
            logger.debug("No memory client available, skipping memory storage")
            return

        try:
            memory_messages = [{"role": "user", "content": user_input}]
            if agent_response:
                memory_messages.append({"role": "assistant", "content": agent_response})

            logger.info(
                "Storing interaction in Mem0",
                message_count=len(memory_messages),
                user_id=self.user_id,
            )

            self.memory_client.add(memory_messages, user_id=self.user_id)

            logger.info(
                "Memory stored successfully",
                user_id=self.user_id,
                messages_stored=len(memory_messages),
            )

        except Exception as e:
            logger.exception(
                "Failed to store memory in Mem0",
                error=str(e),
                error_type=type(e).__name__,
                user_id=self.user_id,
            )

    async def run_agent(  # type: ignore[override]
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        logger.info("=" * 80)
        logger.info(
            "MemoryHandler.run_agent() - MEMORY-AWARE streaming",
            user_input_length=len(user_input),
            message_history_count=len(message_history),
            has_memory_client=self.memory_client is not None,
            user_id=self.user_id,
        )

        # Step 1: Retrieve relevant memories
        logger.info("Step 1: Retrieving relevant memories...")
        memories_str = self.get_memories(user_input) if self.memory_client else ""
        logger.info(
            "Memory retrieval complete",
            has_memories=bool(memories_str),
            memories_length=len(memories_str),
        )

        # Step 2: Stream agent response with memories in context
        logger.info("Step 2: Streaming agent response with memory context...")
        full_response = ""
        chunk_count = 0

        try:
            async for chunk in super().run_agent(
                user_input, message_history, http_client, memories_str=memories_str, **kwargs
            ):
                chunk_count += 1

                # Accumulate full response for memory storage
                if chunk.get("type") == "delta":
                    full_response += chunk["content"]

                yield chunk

            logger.info("Agent streaming complete", chunk_count=chunk_count)

            # Step 3: Store interaction in memory
            if self.memory_client and chunk.get("type") == "complete":
                logger.info(
                    "Step 3: Storing interaction in memory",
                    full_response_length=len(full_response),
                )
                self.add_memory(user_input, full_response)
                logger.info("Memory storage complete")
            else:
                logger.debug(
                    "Skipping memory storage",
                    has_memory_client=self.memory_client is not None,
                    chunk_type=chunk.get("type") if "chunk" in locals() else "no_chunk",
                )

            logger.info(
                "MemoryHandler.run_agent() finished successfully",
                total_chunks=chunk_count,
                response_length=len(full_response),
            )

        except Exception as e:
            logger.exception(
                "MemoryHandler agent execution FAILED",
                error=str(e),
                error_type=type(e).__name__,
                chunks_before_failure=chunk_count,
            )
            raise
