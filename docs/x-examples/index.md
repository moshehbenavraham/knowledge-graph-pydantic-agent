# Example Documents

Sample documents for testing and demonstrating Luminari Agent's RAG capabilities.

## About These Examples

This directory contains example documents used for:

- **Testing RAG Ingestion** - Validating document processing pipeline
- **Demonstrating Search** - Showing vector and graph search capabilities
- **End-to-End Testing** - Full system integration tests
- **Benchmarking** - Performance and quality evaluation

## Example Topics

The example documents cover:

- AI company funding and investments
- Technology executive profiles
- Market analysis and trends
- Company acquisitions and partnerships
- Industry news and developments

## Using Examples

Ingest these documents to test the system:

```bash
# Ingest all examples
make ingest

# Or use the ingestion pipeline directly
python -m src.agentic_rag.ingestion ingest --path docs/x-examples

# Clean ingest (reset existing data)
python -m src.agentic_rag.ingestion ingest --path docs/x-examples --clean
```

## Quick Links

- [Back to Documentation Home](../README.md)
- [RAG Architecture](../3-architecture/agentic-rag.md)
- [Usage Guide](../5-guides/usage.md)
