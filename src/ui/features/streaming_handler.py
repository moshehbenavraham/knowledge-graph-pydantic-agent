from collections.abc import AsyncIterator
from typing import Any

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


class StreamingHandler(BaseHandler):
    async def run_agent(
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        agent_deps = self.get_agent_deps(http_client, **kwargs)

        async with super_agent.iter(
            user_input, deps=agent_deps, message_history=message_history
        ) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent):
                                # Yield all part start events (text, tool-call, tool-return)
                                if event.part.part_kind == "text":
                                    yield {"type": "start", "content": event.part.content}
                                elif event.part.part_kind == "tool-call":
                                    yield {
                                        "type": "tool-call",
                                        "tool_name": event.part.tool_name,
                                        "args": event.part.args,
                                    }
                                elif event.part.part_kind == "tool-return":
                                    yield {
                                        "type": "tool-return",
                                        "tool_name": event.part.tool_name,
                                        "content": event.part.content,
                                    }
                            elif isinstance(event, PartDeltaEvent) and isinstance(
                                event.delta, TextPartDelta
                            ):
                                yield {"type": "delta", "content": event.delta.content_delta}

        yield {"type": "complete", "new_messages": run.result.new_messages(), "streaming": True}
