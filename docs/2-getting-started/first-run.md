# Your First Agent Interaction

This guide walks you through your first interaction with the Knowledge Graph Pydantic Agent after installation.

## Starting the Application

Choose your preferred interface:

### Web Interface (Recommended)

```bash
# Start the Streamlit UI
make run-ui

# Alternative modes:
make run-ui-simple     # Lightweight mode
make run-ui-advanced   # Full features
```

Open your browser to `http://localhost:8501`

### API Server

```bash
# Start the FastAPI server
make run-api
```

API available at `http://localhost:8058`

## The Streamlit Interface

When you first open the web interface, you'll see:

### Sidebar Navigation
- **💬 Chat**: Main chat interface
- **📊 Dashboard**: Analytics and monitoring (if enabled)
- **⚙️ Settings**: Configuration options
- **📁 Files**: Document upload and management

### Main Chat Area
- **Message Input**: Text area for your questions
- **File Upload**: Support for documents, images, and data files
- **Response Area**: Streaming AI responses with tool visibility

## Your First Query

### 1. Simple Question
Try asking a straightforward question:

```
What is the capital of France?
```

The agent will:
- Recognize this as a simple factual question
- Use web search to find the answer
- Provide a direct response with source attribution

### 2. Document Analysis
Upload a document and ask about it:

**Steps:**
1. Click the file upload button in the chat
2. Select a PDF, text file, or image
3. Ask a question about the content

**Example:**
```
Upload: project_proposal.pdf
Question: What is the main objective of this project?
```

### 3. Code Execution
Ask the agent to run code:

```
Write a Python function that calculates fibonacci numbers
```

The agent will:
- Generate the code
- Execute it safely in a sandboxed environment
- Show the results

## Understanding Responses

### Response Components
- **Main Answer**: Direct response to your question
- **Tool Usage**: Shows which tools were used (if in advanced mode)
- **Source Citations**: Links to source documents or web pages
- **Follow-up Suggestions**: Related questions you might ask

### Response Streaming
- Responses stream in real-time as they're generated
- You can see partial responses as the agent thinks
- Tool execution happens in parallel for faster responses

## Advanced Features to Try

### 1. Memory and Context
In advanced mode, the agent remembers your conversation:

```
First: Tell me about machine learning
Later: What did I just ask about?
```

### 2. Knowledge Graph Features
If you have Neo4j configured, try entity-focused queries:

```
Who are the key people mentioned in the documents?
```

### 3. SQL Query Generation
Ask about data in your connected databases:

```
Show me the top 5 customers by revenue this month
```

## Common First-Time Issues

### "No API Key Configured"
**Problem**: Missing or invalid API credentials

**Solution**:
```bash
# Check your .env file
cat .env | grep LLM_API_KEY

# Verify the key works
python -c "
from src.clients.llm import LLMClient
client = LLMClient()
print('API key is valid')
"
```

### "Database Connection Failed"
**Problem**: Cannot connect to Supabase or PostgreSQL

**Solution**:
```bash
# Test database connection
python scripts/test_supabase_connection.py

# Check network access
curl -I $SUPABASE_URL/rest/v1/
```

### "No Documents Found"
**Problem**: No documents in the knowledge base for RAG features

**Solution**:
1. Upload some documents through the web interface
2. Or run the sample data ingestion:
   ```bash
   python -m src.agentic_rag.ingestion ingest --sample-data
   ```

## Getting Comfortable

### Explore the Dashboard
- Navigate to "📊 Dashboard" in the sidebar
- View system metrics and performance
- Explore the knowledge graph visualization (if enabled)

### Try Different Query Types
- **Factual Questions**: "What is quantum computing?"
- **Analysis Requests**: "Summarize this document"
- **Creative Tasks**: "Write a short story about AI"
- **Code Generation**: "Create a Flask web application"

### Experiment with File Uploads
- Upload PDFs, text files, or images
- Ask questions about the content
- Try different file types to see capabilities

## Performance Tips

### For Faster Responses
- Use simpler models for testing (`gpt-4o-mini` vs `gpt-4`)
- Enable Redis caching for repeated queries
- Configure appropriate chunk sizes for document processing

### For Better Accuracy
- Provide clear, specific questions
- Include relevant context when possible
- Use the knowledge graph features for entity-rich queries

## What's Next?

Now that you're comfortable with basic interactions:

- **[Configuration Guide](./configuration.md)** - Customize for your needs
- **[User Guides](../5-guides/)** - Learn advanced features
- **[Architecture Overview](../3-architecture/)** - Understand how it works

## Getting Help

If you encounter issues:

1. **Check the logs** - Look for error messages in the terminal
2. **Review troubleshooting** - See [Troubleshooting Guide](../10-troubleshooting/)
3. **Test components** - Use the provided test scripts
4. **Ask for help** - Use GitHub Issues or Discussions

---

**🎉 Welcome to Knowledge Graph Pydantic Agent!** You're now ready to explore all the capabilities.
