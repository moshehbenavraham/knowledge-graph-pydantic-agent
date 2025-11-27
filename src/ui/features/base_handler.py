from abc import ABC, abstractmethod
from typing import Any

import structlog
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from src.agent import UnifiedAgentDeps, super_agent
from src.clients import get_llm_client, get_supabase_client
from src.config import get_settings

logger = structlog.get_logger(__name__)


class BaseHandler(ABC):
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.embedding_client: Any = None
        self.supabase: Any = None
        self._initialized = False

    def initialize(self) -> None:
        logger.info("=" * 80)
        logger.info(
            "BaseHandler.initialize() called",
            handler_class=self.__class__.__name__,
            already_initialized=self._initialized,
        )

        if not self._initialized:
            logger.info("Initializing handler clients...")

            try:
                logger.debug("Creating LLM/embedding client...")
                self.embedding_client = get_llm_client()
                logger.info("LLM/embedding client created successfully")
            except Exception as e:
                logger.exception("Failed to create LLM/embedding client", error=str(e))
                raise

            try:
                logger.debug("Creating Supabase client...")
                self.supabase = get_supabase_client()
                logger.info("Supabase client created successfully")
            except Exception as e:
                logger.exception("Failed to create Supabase client", error=str(e))
                raise

            self._initialized = True
            logger.info("Handler marked as initialized")

            try:
                logger.debug("Calling _setup_hook() for subclass-specific initialization...")
                self._setup_hook()
                logger.info("_setup_hook() completed successfully")
            except Exception as e:
                logger.exception("_setup_hook() failed", error=str(e))
                raise

            logger.info(
                "Handler initialization COMPLETE",
                handler_class=self.__class__.__name__,
                has_embedding_client=self.embedding_client is not None,
                has_supabase=self.supabase is not None,
            )
        else:
            logger.debug(
                "Handler already initialized, skipping",
                handler_class=self.__class__.__name__,
            )

    def _setup_hook(self) -> None:
        pass

    @abstractmethod
    async def run_agent(
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs: Any,
    ) -> Any:  # Return type can be Any or AsyncIterator, depending on implementation
        pass

    def get_agent_deps(
        self, http_client: AsyncClient, memories_str: str = "", **kwargs: Any
    ) -> UnifiedAgentDeps:
        logger.debug(
            "Creating UnifiedAgentDeps for agent execution",
            has_memories=bool(memories_str),
            memories_length=len(memories_str) if memories_str else 0,
            extra_kwargs=list(kwargs.keys()) if kwargs else [],
        )

        settings = get_settings()

        logger.debug(
            "Settings loaded for agent deps",
            web_search_provider=settings.web_search_provider or "none",
            has_brave_key=bool(settings.brave_api_key),
            has_jina_key=bool(settings.jina_api_key),
            has_searxng_url=bool(settings.searxng_base_url),
        )

        deps = UnifiedAgentDeps(
            embedding_client=self.embedding_client,
            supabase=self.supabase,
            http_client=http_client,
            brave_api_key=settings.brave_api_key or "",
            searxng_base_url=settings.searxng_base_url or "",
            jina_api_key=settings.jina_api_key or "",
            web_search_provider=settings.web_search_provider or "",
            memories=memories_str,
        )

        logger.info(
            "UnifiedAgentDeps created successfully",
            has_embedding_client=deps.embedding_client is not None,
            has_supabase=deps.supabase is not None,
            has_http_client=deps.http_client is not None,
            web_search_provider=deps.web_search_provider or "none",
        )

        return deps


class SimpleHandler(BaseHandler):
    async def run_agent(
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs: Any,
    ) -> dict[str, Any]:
        logger.info("=" * 80)
        logger.info(
            "SimpleHandler.run_agent() - NON-STREAMING execution",
            user_input_length=len(user_input),
            message_history_count=len(message_history),
            user_input_preview=user_input[:100] + "..." if len(user_input) > 100 else user_input,
        )

        try:
            logger.debug("Getting agent dependencies...")
            agent_deps = self.get_agent_deps(http_client)

            logger.info("Executing super_agent.run() (blocking until complete)...")
            result = await super_agent.run(
                user_input, deps=agent_deps, message_history=message_history
            )

            output_length = len(result.output) if result.output else 0
            new_messages_count = len(result.new_messages())

            logger.info(
                "Agent execution COMPLETE",
                output_length=output_length,
                new_messages_count=new_messages_count,
                output_preview=(
                    result.output[:200] + "..."
                    if result.output and len(result.output) > 200
                    else result.output
                ),
            )

            return {
                "response": result.output,
                "new_messages": result.new_messages(),
                "streaming": False,
            }
        except Exception as e:
            logger.exception(
                "SimpleHandler agent execution FAILED",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
