# Contributing to Luminari Agent

Thank you for your interest in contributing to Luminari Agent! This guide will help you get started with contributing to our production-ready AI assistant with Agentic RAG capabilities.

## 🤝 Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## 🚀 Quick Start for Contributors

### Prerequisites
- **Python 3.11+**
- **Git** for version control
- **Make** (recommended for development commands)
- **Docker** (optional, for containerized development)

### Development Setup

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/base_agent.git
   cd base_agent
   ```

2. **Set Up Development Environment**
   ```bash
   # Install dependencies and pre-commit hooks
   make setup

   # Alternative: Manual installation
   python -m pip install -e .[dev]
   pre-commit install
   ```

3. **Configure Environment**
   ```bash
   # Copy example configuration
   cp .env.example .env
   # Edit .env with your test credentials
   ```

   **Note:** We use a centralized configuration system. Always use `from src.config import get_settings` instead of direct `os.getenv()` calls.

4. **Run Tests**
   ```bash
   # Verify your setup works
   make test
   ```

## 🏗️ Architecture Guidelines

### Configuration System
We use a **centralized Pydantic-based configuration** system:
- All settings are in `src/config/settings.py`
- Use module facades (`api_config`, `agent_config`, etc.) for clean access
- Never use `os.getenv()` directly - always go through the config system
- Add new settings with proper validation and defaults

### Unified Agent
- There is ONE agent: `src/agent/unified_agent.py`
- All tools and capabilities are integrated here
- Don't create separate agent implementations

### UI System
- Single configurable UI in `src/ui/streamlit_app.py`
- Three modes: Simple, Standard, Advanced
- Add new features as modular handlers in `src/ui/features/`

## 📋 How to Contribute

### Types of Contributions

We welcome several types of contributions:

1. **🐛 Bug Reports**: Report issues with clear reproduction steps
2. **✨ Feature Requests**: Propose new features with detailed specifications
3. **🔧 Bug Fixes**: Fix identified issues with tests
4. **🚀 New Features**: Implement approved feature requests
5. **📚 Documentation**: Improve or add documentation
6. **🧪 Tests**: Add or improve test coverage
7. **🎨 Code Quality**: Refactoring, optimization, code style improvements

### Contributing Workflow

1. **Check Existing Issues**
   - Search [existing issues](https://github.com/your-repo/issues) before creating new ones
   - Comment on issues you'd like to work on

2. **Create a Branch**
   ```bash
   # Create a descriptive branch name
   git checkout -b feature/add-new-search-strategy
   git checkout -b fix/memory-leak-in-embedding
   git checkout -b docs/update-api-documentation
   ```

3. **Make Changes**
   - Follow our coding standards (see below)
   - Write or update tests for your changes
   - Update documentation as needed

4. **Test Your Changes**
   ```bash
   # Run the full test suite
   make check

   # Individual checks
   make test          # Run tests
   make lint          # Check code style
   make security      # Security scan
   make format        # Auto-format code
   ```

5. **Commit Changes**
   ```bash
   # Use conventional commit format
   git commit -m "feat: add hybrid search strategy for better retrieval"
   git commit -m "fix: resolve memory leak in embedding cache"
   git commit -m "docs: update API documentation for new endpoints"
   ```

6. **Push and Create PR**
   ```bash
   git push origin your-branch-name
   # Create pull request on GitHub
   ```

## 🎯 Development Guidelines

### Code Style and Standards

We use automated tools to maintain code quality:

- **Black**: Code formatting (100-character line length)
- **Ruff**: Fast Python linter with comprehensive rules
- **MyPy**: Static type checking
- **Pre-commit**: Automated checks before commits

```bash
# Format code
make format

# Check style and types
make lint

# Run all checks
make check
```

### Testing Requirements

- **Minimum 75% test coverage** (enforced by pytest-cov)
- **All new features must include tests**
- **Bug fixes must include regression tests**
- **Use pytest with async support**

```bash
# Run tests with coverage
make test-coverage

# Run specific test files
pytest tests/test_agent.py -v

# Run tests matching a pattern
pytest -k "test_rag" -v
```

### Documentation Standards

- **Docstrings**: All public functions and classes must have docstrings
- **Type hints**: Required for all function signatures
- **README updates**: Update README.md for significant features
- **API documentation**: Update relevant docs/ files

### Architecture Guidelines

- **Modular design**: Keep components loosely coupled
- **Async/await**: Use async patterns for I/O operations
- **Error handling**: Implement comprehensive error handling
- **Configuration**: Use environment variables for configuration
- **Security**: Follow secure coding practices

## 🔧 Working with Specific Components

### Agentic RAG System

When working on the Agentic RAG system (`src/agentic_rag/`):

- **Database**: Test changes with both PostgreSQL and Neo4j
- **Search strategies**: Ensure vector, graph, and hybrid search work
- **Knowledge extraction**: Test entity and relationship extraction
- **Performance**: Monitor query performance and storage efficiency

### Agent Tools

When adding or modifying tools (`src/tools/`):

- **Async patterns**: All tools must be async
- **Error handling**: Graceful failure with informative messages
- **Security**: Validate inputs, especially for code execution
- **Documentation**: Clear docstrings with usage examples

### UI Components

When working on interfaces (`src/ui/`):

- **Streamlit**: Follow Streamlit best practices
- **User experience**: Ensure intuitive and responsive design
- **Error feedback**: Provide clear error messages to users
- **Accessibility**: Consider accessibility standards

## 📊 Pull Request Guidelines

### PR Requirements

- **Clear title**: Descriptive title following conventional commit format
- **Detailed description**: Explain what changes and why
- **Tests**: Include tests for new functionality
- **Documentation**: Update relevant documentation
- **No breaking changes**: Unless properly discussed and documented

### PR Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Updated existing tests as needed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or properly documented)
```

### Review Process

1. **Automated checks**: All CI checks must pass
2. **Code review**: At least one maintainer review required
3. **Testing**: Verify changes work as expected
4. **Documentation**: Ensure docs are updated
5. **Merge**: Squash merge preferred for clean history

## 🛠️ Advanced Development

### Setting Up Full Development Environment

```bash
# Install all optional dependencies
python -m pip install -e .[dev,rag,security]

# Set up databases for testing
# PostgreSQL/Supabase: Use test project
# Neo4j: Use test instance

# Run with development settings
make dev
```

### Database Development

```bash
# PostgreSQL schema changes
# Update sql/ files and test thoroughly

# Neo4j schema changes
# Update graph initialization scripts

# Test database migrations
python -m src.agentic_rag.storage.neo4j_store init
```

### Performance Testing

```bash
# Run performance benchmarks
python -m tests.performance.benchmark_search
python -m tests.performance.benchmark_ingestion

# Monitor memory usage
python -m tests.performance.memory_profiling
```

## 🐛 Reporting Issues

### Bug Reports

Please include:

- **Environment**: OS, Python version, dependency versions
- **Steps to reproduce**: Clear, minimal reproduction steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Logs**: Relevant error messages or logs
- **Screenshots**: If applicable for UI issues

### Feature Requests

Please include:

- **Use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches considered
- **Implementation notes**: Any technical considerations

## 🏷️ Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Schedule

- **Patch releases**: As needed for critical fixes
- **Minor releases**: Monthly feature releases
- **Major releases**: Quarterly with breaking changes

## 📚 Resources

### Useful Commands

```bash
# Development commands
make setup          # Set up development environment
make check          # Run all checks
make test           # Run tests
make format         # Format code
make security       # Security scan
make clean          # Clean build artifacts

# Running services
make run-ui         # Start Streamlit UI
make run-rag        # Run RAG pipeline
make dev            # Development mode

# Docker
make docker-build   # Build containers
make docker-run     # Run with Docker
make docker-stop    # Stop containers
```

### Documentation

- **[Architecture](docs/3-architecture/index.md)**: System design and structure
- **[Configuration](docs/4-configuration/index.md)**: Environment setup
- **[Database & RAG](docs/3-architecture/database-and-rag.md)**: Database and RAG details
- **[Usage](docs/5-guides/usage.md)**: Usage examples and patterns
- **[Performance](docs/7-operations/performance.md)**: Performance guidelines

### Community

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community support
- **Documentation**: Check docs/ directory for guides

## ❓ Getting Help

If you need help:

1. **Check documentation**: Review docs/ directory
2. **Search issues**: Look for similar problems
3. **Ask questions**: Create a GitHub discussion
4. **Join the community**: Participate in project discussions

---

Thank you for contributing to Luminari Agent! Your efforts help make this project better for everyone. 🚀
