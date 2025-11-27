from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

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
from src.agentic_rag.analytics import (
    AgentInteractionEvent,
    ToolUsageEvent,
    get_analytics_logger,
)

from .base_handler import BaseHandler

logger = structlog.get_logger(__name__)


class StreamingHandler(BaseHandler):
    async def run_agent(  # type: ignore[override]
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs: Any,
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

        # Analytics tracking
        interaction_start_time = datetime.now()
        session_id = kwargs.get("session_id", uuid4())
        user_id = kwargs.get("user_id")
        tools_called = []
        tool_timings = {}  # Track tool execution times
        rag_used = False
        response_text = ""

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
                                        tool_name = event.part.tool_name

                                        # Track tool timing
                                        tool_timings[tool_name] = {
                                            "start": datetime.now(),
                                            "args": event.part.args,
                                        }
                                        tools_called.append(tool_name)

                                        # Check if RAG tool is being used
                                        if tool_name in [
                                            "smart_search",
                                            "retrieve_documents",
                                            "comprehensive_search",
                                        ]:
                                            rag_used = True

                                        logger.info(
                                            "Tool call event",
                                            tool_name=tool_name,
                                            args_keys=(
                                                list(event.part.args.keys())
                                                if isinstance(event.part.args, dict)
                                                else "non-dict"
                                            ),
                                        )
                                        yield {
                                            "type": "tool-call",
                                            "tool_name": tool_name,
                                            "args": event.part.args,
                                        }

                                    elif event.part.part_kind == "tool-return":
                                        event_counts["tool_return"] += 1
                                        tool_name = event.part.tool_name
                                        content_str = str(event.part.content)

                                        # Calculate execution time and log tool usage
                                        if tool_name in tool_timings:
                                            end_time = datetime.now()
                                            start_time = tool_timings[tool_name]["start"]
                                            execution_ms = (
                                                end_time - start_time
                                            ).total_seconds() * 1000

                                            # Log tool usage to analytics
                                            try:
                                                analytics_logger = get_analytics_logger()
                                                tool_event = ToolUsageEvent(
                                                    session_id=(
                                                        session_id
                                                        if isinstance(session_id, UUID)
                                                        else None
                                                    ),
                                                    tool_name=tool_name,
                                                    execution_time_ms=execution_ms,
                                                    success=True,
                                                    input_params=tool_timings[tool_name].get(
                                                        "args"
                                                    ),
                                                    result_summary={
                                                        "content_length": len(content_str)
                                                    },
                                                    triggered_by="agent_decision",
                                                    user_id=user_id,
                                                    source="ui",
                                                )
                                                await analytics_logger.log_tool_usage(tool_event)
                                                logger.debug(f"Logged tool usage for {tool_name}")
                                            except Exception as log_err:
                                                logger.warning(
                                                    f"Failed to log tool usage: {log_err}"
                                                )

                                        content_preview = (
                                            content_str[:100] + "..."
                                            if len(content_str) > 100
                                            else content_str
                                        )
                                        logger.info(
                                            "Tool return event",
                                            tool_name=tool_name,
                                            content_length=len(content_str),
                                            content_preview=content_preview,
                                        )
                                        yield {
                                            "type": "tool-return",
                                            "tool_name": tool_name,
                                            "content": event.part.content,
                                        }

                                elif isinstance(event, PartDeltaEvent) and isinstance(
                                    event.delta, TextPartDelta
                                ):
                                    event_counts["text_delta"] += 1
                                    response_text += event.delta.content_delta
                                    if event_counts["text_delta"] % 10 == 0:
                                        logger.debug(
                                            "Text delta streaming",
                                            delta_count=event_counts["text_delta"],
                                        )
                                    yield {"type": "delta", "content": event.delta.content_delta}

            new_messages_count = len(run.result.new_messages()) if run.result else 0

            # Log agent interaction to analytics
            interaction_end_time = datetime.now()
            response_time_ms = (
                interaction_end_time - interaction_start_time
            ).total_seconds() * 1000

            try:
                analytics_logger = get_analytics_logger()
                from src.config import get_settings

                settings = get_settings()

                interaction_event = AgentInteractionEvent(
                    session_id=session_id if isinstance(session_id, UUID) else uuid4(),
                    interaction_type="query",
                    user_message=user_input,
                    agent_response=response_text[:500],  # Truncate for storage
                    response_time_ms=response_time_ms,
                    model_used=settings.llm_model or "unknown",
                    tools_called=tools_called,
                    rag_used=rag_used,
                    user_id=user_id,
                    source="ui",
                    metadata={"event_counts": event_counts},
                )
                await analytics_logger.log_interaction(interaction_event)
                logger.info("Logged agent interaction to analytics")
            except Exception as log_err:
                logger.warning(f"Failed to log agent interaction: {log_err}")

            logger.info(
                "Stream COMPLETE - sending completion event",
                new_messages_count=new_messages_count,
                **event_counts,
            )

            yield {
                "type": "complete",
                "new_messages": run.result.new_messages() if run.result else [],
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
