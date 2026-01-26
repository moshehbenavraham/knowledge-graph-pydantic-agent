# Development

Documentation for contributors and developers working on Knowledge Graph Pydantic Agent.

## Development Documentation

- **[Code Styling Guide](code-styling-guide.md)** - Coding standards and style conventions
- **[Testing Guide](testing-guide.md)** - Comprehensive testing documentation
- **[Development Tooling](dev-tooling.md)** - Development environment and tools
- **[Product Requirements (PRD)](prd.md)** - Product vision and requirements

## Getting Started with Development

1. **Setup Development Environment**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install uv && uv pip install -e .[dev,rag]
   pre-commit install
   ```

2. **Run Tests**
   ```bash
   make test              # Run test suite
   make test-coverage     # Run with coverage (75% minimum)
   ```

3. **Code Quality**
   ```bash
   make lint              # Check code style
   make format            # Auto-format code
   make security          # Security scanning
   make check             # Run all checks
   ```

## Development Workflow

1. Create feature branch
2. Make changes with proper tests
3. Run `make check` to ensure all checks pass
4. Submit pull request

## Key Development Principles

- **One Agent**: Extend `src/agent/unified_agent.py`, don't create new agents
- **Configuration**: Use `src/config/settings.py`, never `os.getenv()` directly
- **Testing**: Minimum 75% coverage required
- **Type Hints**: Required for all function signatures
- **Async First**: Use `async`/`await` for all I/O operations

## Quick Links

- [Back to Documentation Home](../README.md)
- [Architecture](../3-architecture/index.md)
- [Testing](testing-guide.md)
