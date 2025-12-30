import base64
from typing import Any

import structlog
from pydantic_ai import Agent, BinaryContent

logger = structlog.get_logger(__name__)

try:
    from pydantic_ai.models.openai import OpenAIChatModel
except ImportError:
    OpenAIChatModel = None  # type: ignore

try:
    from pydantic_ai.providers.openai import OpenAIProvider
except ImportError:
    OpenAIProvider = None  # type: ignore

try:
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.providers.anthropic import AnthropicProvider
except ImportError:
    AnthropicModel = None  # type: ignore
    AnthropicProvider = None  # type: ignore

from supabase.client import Client

from src.config import get_settings


async def image_analysis_tool(supabase: Client, document_id: str, query: str) -> str:
    logger.info("image_analysis_tool called", document_id=document_id, query_length=len(query))

    try:
        # Get configuration from centralized settings
        settings = get_settings()
        provider = settings.llm_provider.lower()
        llm = settings.vision_llm_choice
        api_key = settings.llm_api_key
        logger.debug("Vision model configuration loaded", provider=provider, model=llm)

        # Define the vision agent based on the provider
        model: Any
        if provider == "anthropic":
            if AnthropicModel is None or AnthropicProvider is None:
                raise ImportError("Anthropic model not available")

            # Map common model names to Anthropic's naming
            model_map = {
                "claude-4-sonnet": "claude-4-sonnet",  # Claude 4 Sonnet with vision
                "claude-3-opus": "claude-3-opus-20240229",
                "claude-3-sonnet": "claude-3-5-sonnet-20241022",
                "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
                "claude-3-haiku": "claude-3-haiku-20240307",
            }
            anthropic_model = model_map.get(llm, llm)
            model = AnthropicModel(anthropic_model, provider=AnthropicProvider(api_key=api_key))
        else:
            base_url = settings.llm_base_url
            model = OpenAIChatModel(
                llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key)
            )

        vision_agent = Agent(
            model,
            system_prompt="You are an image analyzer who looks at images provided and answers the accompanying query in detail.",
        )

        # Get the binary of the file from the database
        # Try to find by source field (filename) or by id
        # First try exact match on source field
        result = (
            supabase.from_("documents")
            .select("metadata, source")
            .eq("source", document_id)
            .limit(1)
            .execute()
        )

        # If not found, try by id
        if not result.data:
            result = (
                supabase.from_("documents")
                .select("metadata, source")
                .eq("id", document_id)
                .limit(1)
                .execute()
            )

        if not result.data:
            logger.warning("No document found", document_id=document_id)
            return f"No content found for document: {document_id}"

        # Get the binary and mime_type from the metadata
        metadata = result.data[0]["metadata"]
        logger.debug("Document retrieved successfully", document_id=document_id)

        # Support both upload formats: file_contents or image_data
        binary_str = metadata.get("file_contents") or metadata.get("image_data")
        mime_type = metadata.get("mime_type") or metadata.get("file_type", "image/png")

        if not binary_str:
            logger.warning("No file contents found in document metadata", document_id=document_id)
            return f"No file contents found for document: {document_id}"

        # Turn the binary string into binary and send it into the vision LLM
        logger.debug("Starting vision analysis", mime_type=mime_type, data_size=len(binary_str))
        binary = base64.b64decode(binary_str.encode("utf-8"))
        result = await vision_agent.run([query, BinaryContent(data=binary, media_type=mime_type)])

        logger.info("Image analysis completed successfully", output_length=len(result.output))
        return result.output

    except Exception as e:
        logger.exception("Error analyzing image", document_id=document_id, error=str(e))
        return f"Error analyzing image: {e!s}"
