# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release with comprehensive AI agent implementation
- **RAG Pipeline**: Text chunking, embedding generation, vector database operations
- **RAG Pipeline - Google Drive Integration**: Drive connector, document processor, file watching
- **RAG Pipeline - Local Files**: Local file connector with file watching capabilities
- **Database Setup**: Supabase client, document metadata table, document rows table, pgvector extension, similarity search
- **Agent Core**: Base agent implementation, prompt templates, multi-provider LLM integration, local model support, conversation history
- **Memory System**: Session management, memory extraction, vector storage, retrieval system, deduplication
- **Document Tools**: Document listing, content retrieval, SQL query tool for tabular data
- **Web Tools**: Brave API web search, content summarizer, image analysis with OpenAI
- **Utility Tools**: Image analysis tool, code execution tool
- **Streamlit UI**: Chat interface, session management, chat history, styling and layout
- **UI Integration**: Agent connection, error handling, loading indicators
- **Environment Configuration**: `.env.example` setup, configuration loading, validation
- **Testing Infrastructure**: pytest configuration, test fixtures
- **Documentation**: Complete README.md with setup instructions

### Fixed
- Corrected `brave-search` package name to `brave-search-python-client` in `requirements.txt`.

### Changed
- Updated various documentation files (`docs/ARCHITECTURE.md`, `docs/DB_AND_RAG.md`, `docs/GEMINI.md`, `docs/INSTALL.md`, `docs/PRD.md`, `docs/TASKS.md`, `docs/USAGE.md`) to reflect project changes and improve clarity.
- Relocated Streamlit UI files from `temp_extras/Streamlit_UI/` to `src/ui/` to align with primary deployment role. Removed `temp_extras/` directory.
