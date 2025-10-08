Agentic RAG System Documentation
=================================

Welcome to the comprehensive documentation for the Agentic RAG System - a production-ready AI agent with Retrieval-Augmented Generation, memory capabilities, and enterprise monitoring.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   guides/quickstart
   guides/installation
   guides/configuration
   guides/first_steps

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   guides/chat_interface
   guides/search_strategies
   guides/tool_usage
   guides/api_usage

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture/overview
   architecture/agent_system
   architecture/storage_layer
   architecture/search_pipeline
   architecture/ingestion

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/agent
   api/storage
   api/search
   api/tools
   api/ingestion
   api/endpoints

.. toctree::
   :maxdepth: 2
   :caption: Development

   development/setup
   development/testing
   development/contributing
   development/code_style

.. toctree::
   :maxdepth: 2
   :caption: Deployment

   deployment/docker
   deployment/kubernetes
   deployment/monitoring
   deployment/scaling

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources

   changelog
   troubleshooting
   faq
   glossary

Features
--------

* **Agentic RAG**: Combines vector search and knowledge graphs for intelligent retrieval
* **Multi-Model Support**: OpenAI, Anthropic, and Ollama LLM providers
* **Advanced Search**: Vector, graph, and hybrid search strategies
* **Memory System**: Long-term conversation memory with PostgreSQL backend
* **Tool Integration**: Web search, code execution, image analysis, and more
* **Production Ready**: Monitoring, caching, and performance optimization
* **Enterprise Features**: Security scanning, audit logging, and compliance

Quick Links
-----------

* :doc:`guides/quickstart` - Get up and running in 5 minutes
* :doc:`api/endpoints` - REST API documentation
* :doc:`architecture/overview` - System architecture guide
* :doc:`deployment/docker` - Docker deployment guide

System Requirements
-------------------

* Python 3.11 or higher
* PostgreSQL with pgvector extension (via Supabase)
* Neo4j database (local or cloud)
* Redis for caching
* 8GB RAM minimum (16GB recommended)

Support
-------

* GitHub Issues: `Report bugs and request features <https://github.com/luminari-ai/agentic-rag/issues>`_
* Documentation: You're reading it!
* Community: Join our Discord server

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
