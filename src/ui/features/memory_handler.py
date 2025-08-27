from typing import Any, Dict, List
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from .streaming_handler import StreamingHandler
from src.clients import get_mem0_client


class MemoryHandler(StreamingHandler):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.memory_client = None
        self.user_id = config.get("user_id", "streamlit_user")
    
    def _setup_hook(self):
        super()._setup_hook()
        if self.config.get("enable_memory", True):
            self.memory_client = get_mem0_client()
    
    def get_memories(self, query: str) -> str:
        if not self.memory_client:
            return ""
        
        relevant_memories = self.memory_client.search(
            query=query,
            user_id=self.user_id,
            limit=self.config.get("memory_limit", 3)
        )
        return "\n".join(
            f"- {entry['memory']}" for entry in relevant_memories.get("results", [])
        )
    
    def add_memory(self, user_input: str, agent_response: str = None):
        if not self.memory_client:
            return
        
        memory_messages = [{"role": "user", "content": user_input}]
        if agent_response:
            memory_messages.append({"role": "assistant", "content": agent_response})
        
        self.memory_client.add(memory_messages, user_id=self.user_id)
    
    async def run_agent(
        self,
        user_input: str,
        message_history: List[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs
    ):
        memories_str = self.get_memories(user_input) if self.memory_client else ""
        
        full_response = ""
        async for chunk in super().run_agent(
            user_input, message_history, http_client, memories_str=memories_str, **kwargs
        ):
            if chunk.get("type") == "delta":
                full_response += chunk["content"]
            yield chunk
        
        if self.memory_client and chunk.get("type") == "complete":
            self.add_memory(user_input, full_response)