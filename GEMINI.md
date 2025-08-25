# Google Gemini Integration Guide

This document provides guidance for using Google Gemini models with the Base Agent system.

## Configuration

### Environment Variables
```bash
# Google Gemini Configuration
LLM_PROVIDER=gemini
LLM_API_KEY=your-gemini-api-key
LLM_CHOICE=gemini-1.5-pro

# Note: Gemini doesn't provide embeddings, use OpenAI for embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your-openai-api-key
EMBEDDING_MODEL_CHOICE=text-embedding-3-small
```

### Supported Models
- `gemini-1.5-pro`: High-performance model for complex tasks
- `gemini-1.5-flash`: Fast model for simpler tasks
- `gemini-1.0-pro`: Stable production model

### Setup Instructions

1. **Get API Key**
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create or select a project
   - Generate an API key
   - Add it to your `.env` file as `LLM_API_KEY`

2. **Configure Provider**
   ```bash
   # In your .env file
   LLM_PROVIDER=gemini
   LLM_API_KEY=your-gemini-api-key
   LLM_CHOICE=gemini-1.5-pro
   ```

3. **Test Configuration**
   ```bash
   # Run a simple test
   python -c "from src.clients.llm import get_llm_client; print('Gemini configured successfully')"
   ```

## Features

### Strengths
- Excellent reasoning capabilities
- Long context windows (up to 1M tokens for Gemini-1.5-pro)
- Multi-modal support (text, images, video)
- Competitive performance on complex tasks

### Limitations
- No embedding model (requires separate embedding provider)
- Rate limits vary by model and region
- Some advanced features may not be available in all regions

## Usage Examples

### Basic Chat
```python
from src.clients.llm import get_llm_client

llm_client = get_llm_client()
response = await llm_client.chat(
    messages=[{"role": "user", "content": "Explain quantum computing"}]
)
print(response.choices[0].message.content)
```

### With Agentic RAG
```python
from EXAMPLE_agentic_rag_knowledge_graph.agent import AgenticRAGAgent

# Gemini will be used for reasoning and response generation
agent = AgenticRAGAgent()
response = await agent.chat("What are the latest developments in AI?")
```

## Performance Notes

- Gemini-1.5-pro: Best for complex reasoning tasks
- Gemini-1.5-flash: Faster responses for simpler queries
- Consider rate limits when processing large volumes

## Troubleshooting

### Common Issues
1. **API Key Not Working**
   - Verify key is correct and active
   - Check regional availability
   - Ensure billing is set up in Google Cloud

2. **Rate Limit Errors**
   - Implement exponential backoff
   - Consider upgrading quota limits
   - Use Gemini-1.5-flash for lower-priority tasks

3. **Model Not Found**
   - Check model name spelling
   - Verify model availability in your region
   - Try alternative model names

### Error Handling
The system includes automatic fallback mechanisms:
- Request retries with exponential backoff
- Graceful degradation to alternative models
- Comprehensive error logging

## Best Practices

1. **Model Selection**
   - Use Gemini-1.5-pro for complex analysis
   - Use Gemini-1.5-flash for speed-critical tasks
   - Monitor usage and costs

2. **Context Management**
   - Take advantage of large context windows
   - Include relevant document context
   - Optimize prompt structure

3. **Rate Limiting**
   - Implement request queuing
   - Monitor API usage
   - Set up alerts for quota limits

## Integration with Other Components

### With Vector Search
Gemini works seamlessly with the vector search system:
- Embeddings provided by OpenAI
- Reasoning and response generation by Gemini
- Optimal combination of retrieval and generation

### With Memory System
The mem0 integration works with Gemini:
- Memory encoding uses OpenAI embeddings
- Memory retrieval and application uses Gemini
- Consistent user experience across sessions

### With Tools
All agent tools work with Gemini:
- Code execution results processed by Gemini
- Web search results analyzed by Gemini
- Image analysis (if supported) through Gemini

---

**Note**: This integration is part of the multi-provider LLM support in Base Agent. The system automatically handles provider-specific configurations and optimizations.