from abc import ABC, abstractmethod
from typing import Any

from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from src.agent import UnifiedAgentDeps, super_agent
from src.clients import get_llm_client, get_supabase_client
from src.config import get_settings


class BaseHandler(ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.embedding_client = None
        self.supabase = None
        self._initialized = False

    def initialize(self):
        if not self._initialized:
            self.embedding_client = get_llm_client()
            self.supabase = get_supabase_client()
            self._initialized = True
            self._setup_hook()

    def _setup_hook(self):
        pass

    @abstractmethod
    async def run_agent(
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs,
    ):
        pass

    def get_agent_deps(
        self, http_client: AsyncClient, memories_str: str = "", **kwargs
    ) -> UnifiedAgentDeps:
        settings = get_settings()

        return UnifiedAgentDeps(
            embedding_client=self.embedding_client,
            supabase=self.supabase,
            http_client=http_client,
            brave_api_key=settings.brave_api_key or "",
            searxng_base_url=settings.searxng_base_url or "",
            jina_api_key=settings.jina_api_key or "",
            web_search_provider=settings.web_search_provider or "",
            memories=memories_str,
        )


class SimpleHandler(BaseHandler):
    async def run_agent(
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs,
    ):
        agent_deps = self.get_agent_deps(http_client)
        result = await super_agent.run(user_input, deps=agent_deps, message_history=message_history)
        return {
            "response": result.output,
            "new_messages": result.new_messages(),
            "streaming": False,
        }
