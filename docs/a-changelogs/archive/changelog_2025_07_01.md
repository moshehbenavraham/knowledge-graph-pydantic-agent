# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-07-01

### Added
- Initial release with comprehensive AI agent implementation
- **RAG Pipeline**: Text chunking, embedding generation, vector database operations
- **RAG Pipeline - Google Drive Integration**: Drive connector, document processor, file watching
- **RAG Pipeline - Local Files**: Local file connector with file watching capabilities
- **Database Setup**: Supabase client, document metadata table, document rows table, pgvector extension, similarity search
- **Agent Core**: Base "Luminari" agent implementation, prompt templates, multi-provider LLM integration, local model support, conversation history
- **Memory System**: Session management, memory extraction, vector storage, retrieval system, deduplication
- **Document Tools**: Document listing, content retrieval, SQL query tool for tabular data
- **Web Tools**: Brave API web search, content summarizer, image analysis with OpenAI
- **Utility Tools**: Image analysis tool, code execution tool
- **Streamlit UI**: Chat interface, session management, chat history, styling and layout
- **UI Integration**: Agent connection, error handling, loading indicators
- **Environment Configuration**: `.env.example` setup, configuration loading, validation
- **Testing Infrastructure**: pytest configuration, test fixtures
- **Documentation**: Complete README.md with setup instructions
- **Client Architecture**: Separated embedding and LLM clients for better modularity
- **Security Dependencies**: Added RestrictedPython, pgvector, pillow to core dependencies

### Fixed
- Corrected `brave-search` package name to `brave-search-python-client` in `requirements.txt`
- Fixed duplicate environment variable `VISION_MODEL` in `.env.example`
- Updated project naming consistency across all documentation files
- Fixed missing dependencies in `pyproject.toml` and `requirements.txt`
- Updated file path references in documentation to match actual project structure

### Changed
- **Documentation Overhaul**: Completely rewrote README.md with comprehensive features, installation, and usage guide
- **Architecture Updates**: Updated `docs/ARCHITECTURE.md` with correct client structure and technical components
- **Configuration**: Enhanced `docs/CONFIGURATION.md` with additional environment variables
- **Installation Guide**: Updated `docs/INSTALL.md` with correct repository paths and commands
- **Usage Guide**: Fixed line number references in `docs/USAGE.md`
- **Dependencies**: Reorganized `pyproject.toml` with security dependencies and proper optional groups
- **Client Structure**: Separated embedding client from LLM client for better separation of concerns
- **Environment Variables**: Cleaned up `.env.example` to remove duplicates and ensure consistency
- Relocated Streamlit UI files from `temp_extras/Streamlit_UI/` to `src/ui/` to align with primary deployment role. Removed `temp_extras/` directory.

### Documentation
- Updated all dates to August 24, 2025 across documentation files
- Fixed file path references and links throughout documentation
- Ensured all environment variables are properly documented
- Added comprehensive troubleshooting section to README.md
- Enhanced project structure documentation with technical details
