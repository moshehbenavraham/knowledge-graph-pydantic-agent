# .grok Directory

This directory contains context files for Grok CLI to understand your project better.

## Purpose
- **README.md** (this file): Describes your project context and goals
- ***.mdc files**: Markdown context files with specific instructions, coding standards, or project knowledge

## How it works
When you run `grok-cli --src /path/to/your/project`, Grok CLI will:
1. Read this README.md for project overview
2. Load all .mdc files for additional context and instructions
3. Include this context in every conversation with Grok

## Example .mdc files you might create:
- `coding-standards.mdc` - Your coding style and conventions
- `architecture.mdc` - System architecture and design patterns
- `api-docs.mdc` - API documentation and usage examples
- `troubleshooting.mdc` - Common issues and solutions

## Tips
- Keep .mdc files focused on specific topics
- Use clear, descriptive filenames
- Include examples and specific instructions
- Update context as your project evolves

---
*This directory is inspired by Cursor's .cursorrules concept*
