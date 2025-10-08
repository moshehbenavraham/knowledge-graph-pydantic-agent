from typing import Any, AsyncIterator, Dict, List
from httpx import AsyncClient
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)

from .base_handler import BaseHandler
from src.agent import super_agent


class StreamingHandler(BaseHandler):
    async def run_agent(
        self,
        user_input: str,
        message_history: List[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        agent_deps = self.get_agent_deps(http_client, **kwargs)
        
        async with super_agent.iter(
            user_input, deps=agent_deps, message_history=message_history
        ) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent) and event.part.part_kind == "text":
                                yield {"type": "start", "content": event.part.content}
                            elif isinstance(event, PartDeltaEvent) and isinstance(
                                event.delta, TextPartDelta
                            ):
                                yield {"type": "delta", "content": event.delta.content_delta}
        
        yield {
            "type": "complete",
            "new_messages": run.result.new_messages(),
            "streaming": True
        }