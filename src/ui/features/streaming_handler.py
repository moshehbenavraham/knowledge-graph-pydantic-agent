from collections.abc import AsyncIterator
from typing import Any

import structlog
from httpx import AsyncClient
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)

from src.agent import super_agent

from .base_handler import BaseHandler

logger = structlog.get_logger(__name__)


class StreamingHandler(BaseHandler):
    async def run_agent(
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        logger.info("=" * 80)
        logger.info(
            "StreamingHandler.run_agent() - STREAMING execution",
            user_input_length=len(user_input),
            message_history_count=len(message_history),
            user_input_preview=user_input[:100] + "..." if len(user_input) > 100 else user_input,
            extra_kwargs=list(kwargs.keys()) if kwargs else [],
        )

        # Event tracking
        event_counts = {
            "text_start": 0,
            "text_delta": 0,
            "tool_call": 0,
            "tool_return": 0,
            "nodes_processed": 0,
        }

        try:
            logger.debug("Getting agent dependencies...")
            agent_deps = self.get_agent_deps(http_client, **kwargs)

            logger.info("Starting super_agent.iter() streaming context...")
            async with super_agent.iter(
                user_input, deps=agent_deps, message_history=message_history
            ) as run:
                logger.info("Stream context opened, processing nodes...")

                async for node in run:
                    event_counts["nodes_processed"] += 1
                    logger.debug(
                        "Processing node",
                        node_num=event_counts["nodes_processed"],
                        is_model_request=Agent.is_model_request_node(node),
                    )

                    if Agent.is_model_request_node(node):
                        logger.debug("Node is model request, opening stream...")

                        async with node.stream(run.ctx) as request_stream:
                            logger.debug("Request stream opened, listening for events...")

                            async for event in request_stream:
                                if isinstance(event, PartStartEvent):
                                    # Yield all part start events (text, tool-call, tool-return)
                                    if event.part.part_kind == "text":
                                        event_counts["text_start"] += 1
                                        content_preview = (
                                            event.part.content[:50] + "..."
                                            if len(event.part.content) > 50
                                            else event.part.content
                                        )
                                        logger.debug(
                                            "Text start event",
                                            content_length=len(event.part.content),
                                            content_preview=content_preview,
                                        )
                                        yield {"type": "start", "content": event.part.content}

                                    elif event.part.part_kind == "tool-call":
                                        event_counts["tool_call"] += 1
                                        logger.info(
                                            "Tool call event",
                                            tool_name=event.part.tool_name,
                                            args_keys=(
                                                list(event.part.args.keys())
                                                if isinstance(event.part.args, dict)
                                                else "non-dict"
                                            ),
                                        )
                                        yield {
                                            "type": "tool-call",
                                            "tool_name": event.part.tool_name,
                                            "args": event.part.args,
                                        }

                                    elif event.part.part_kind == "tool-return":
                                        event_counts["tool_return"] += 1
                                        content_str = str(event.part.content)
                                        content_preview = (
                                            content_str[:100] + "..."
                                            if len(content_str) > 100
                                            else content_str
                                        )
                                        logger.info(
                                            "Tool return event",
                                            tool_name=event.part.tool_name,
                                            content_length=len(content_str),
                                            content_preview=content_preview,
                                        )
                                        yield {
                                            "type": "tool-return",
                                            "tool_name": event.part.tool_name,
                                            "content": event.part.content,
                                        }

                                elif isinstance(event, PartDeltaEvent) and isinstance(
                                    event.delta, TextPartDelta
                                ):
                                    event_counts["text_delta"] += 1
                                    if event_counts["text_delta"] % 10 == 0:
                                        logger.debug(
                                            "Text delta streaming",
                                            delta_count=event_counts["text_delta"],
                                        )
                                    yield {"type": "delta", "content": event.delta.content_delta}

            new_messages_count = len(run.result.new_messages())
            logger.info(
                "Stream COMPLETE - sending completion event",
                new_messages_count=new_messages_count,
                **event_counts,
            )

            yield {
                "type": "complete",
                "new_messages": run.result.new_messages(),
                "streaming": True,
            }

            logger.info(
                "StreamingHandler.run_agent() finished successfully",
                total_events=sum(event_counts.values()),
                **event_counts,
            )

        except Exception as e:
            logger.exception(
                "StreamingHandler agent execution FAILED",
                error=str(e),
                error_type=type(e).__name__,
                events_before_failure=event_counts,
            )
            raise
