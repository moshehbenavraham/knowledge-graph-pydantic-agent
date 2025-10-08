import base64
import os

from pydantic_ai import Agent, BinaryContent

try:
    from pydantic_ai.models.openai import OpenAIModel
except ImportError:
    OpenAIModel = None

try:
    from pydantic_ai.providers.openai import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from pydantic_ai.models.anthropic import AnthropicModel
except ImportError:
    AnthropicModel = None

from supabase.client import Client


async def image_analysis_tool(supabase: Client, document_id: str, query: str) -> str:
    try:
        # Environment variables for the vision model
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        llm = os.getenv("VISION_LLM_CHOICE", "gpt-5-mini")
        api_key = os.getenv("LLM_API_KEY", "no-api-key-provided")

        # Define the vision agent based on the provider
        if provider == "anthropic":
            if not AnthropicModel:
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
            model = AnthropicModel(anthropic_model, api_key=api_key)
        else:
            base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
            model = OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))

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
            return f"No content found for document: {document_id}"

        # Get the binary and mime_type from the metadata
        metadata = result.data[0]["metadata"]

        # Support both upload formats: file_contents or image_data
        binary_str = metadata.get("file_contents") or metadata.get("image_data")
        mime_type = metadata.get("mime_type") or metadata.get("file_type", "image/png")

        if not binary_str:
            return f"No file contents found for document: {document_id}"

        # Turn the binary string into binary and send it into the vision LLM
        binary = base64.b64decode(binary_str.encode("utf-8"))
        result = await vision_agent.run([query, BinaryContent(data=binary, media_type=mime_type)])

        return result.output

    except Exception as e:
        print(f"Error analyzing image: {e}")
        return f"Error analyzing image: {e!s}"
