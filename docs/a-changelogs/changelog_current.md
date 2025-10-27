# Changelog

All notable changes to the Luminari Agent project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Previous changelogs**: See `/docs/a-changelogs/archive/` for historical changes

---
---

## [Unreleased]

### Added

### Changed
- Event loop change warnings in connection_manager now log as INFO instead of WARNING (normal Streamlit behavior)

### Fixed
- Jina.ai 422 Unprocessable Entity errors now automatically fallback to Brave or SearXNG search providers
- Asyncio task cleanup errors - analytics logger now properly cancels and waits for all background tasks before shutdown
- Event loop warnings during Streamlit reruns - clarified as normal behavior in log messages

### Security

---
---

## Previous Versions

**Previous changelogs**: See `/docs/a-changelogs/archive/` for historical changes

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version (X.0.0) for incompatible API changes
- **MINOR** version (0.X.0) for new functionality in a backward compatible manner
- **PATCH** version (0.0.X) for backward compatible bug fixes
