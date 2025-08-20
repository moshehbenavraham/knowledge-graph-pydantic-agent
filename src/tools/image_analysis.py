from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import Agent, BinaryContent
from supabase import Client
import base64
import os

async def image_analysis_tool(supabase: Client, document_id: str, query: str) -> str:
    try:
        # Environment variables for the vision model
        llm = os.getenv('VISION_LLM_CHOICE', 'gpt-4o-mini')
        base_url = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
        api_key = os.getenv('LLM_API_KEY', 'no-api-key-provided')

        # Define the vision agent based on the environment variables
        model = OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
        vision_agent = Agent(
            model, 
            system_prompt="You are an image analyzer who looks at images provided and answers the accompanying query in detail."
        )

        # Get the binary of the file from the database
        result = supabase.from_('documents') \
            .select('metadata') \
            .eq('metadata->>file_id', document_id) \
            .limit(1) \
            .execute()

        if not result.data:
            return f"No content found for document: {document_id}"            

        # Get the binary and mime_type from the metadata
        metadata = result.data[0]['metadata']
        binary_str = metadata['file_contents']
        mime_type = metadata['mime_type']

        if not binary_str:
            return f"No file contents found for document: {document_id}"

        # Turn the binary string into binary and send it into the vision LLM
        binary = base64.b64decode(binary_str.encode('utf-8'))
        result = await vision_agent.run([query, BinaryContent(data=binary, media_type=mime_type)])

        return result.data

    except Exception as e:
        print(f"Error analyzing image: {e}")
        return f"Error analyzing image: {str(e)}"