# Changelog

All notable changes to the Luminari Agent project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Previous changelogs**: See `/docs/a-changelogs/archive/` for historical changes

---
Start Changelog Entries
---

## [2.11.10] - 2025-11-09

### Fixed
- **API Configuration**: Fixed APIConfig property access (use app_env property instead of _settings)
- **Dependency Injection**: Updated PostgresStore and Neo4jStore to accept connection manager for proper initialization
- **Docker Production**: Added HOME=/app environment variable to production Docker image
- **Authentication**: Changed pyotp version from >=3.0.0 to >=2.0.0 for compatibility
- **Python Compatibility**: Pinned wrapt>=1.14.0 for Python 3.11 compatibility
- **Module Imports**: Added PYTHONPATH=/app for proper module resolution in Docker
- **Dockerfile**: Removed non-existent sql/ directory copy command

### Added
- **Coolify Deployment**: Complete deployment infrastructure for Coolify platform
- **Async Support**: Added nest-asyncio>=1.5.0 dependency for async event loop handling
- **Package Management**: Replaced pip with uv for faster, more reliable dependency resolution

### Changed
- **Installation**: Install ALL optional dependencies (rag+auth+security) in production Docker image
- **UV Package Manager**: Use --prefix with uv instead of --system for better compatibility

---
End Changelog Entries
---

# FOOTER

## Previous Versions & Brief History

**Previous changelogs**: See `/docs/a-changelogs/archive/` for historical changes

[EXAMPLE!!!]
| Version | Release Date | Key Features |
|---------|--------------|--------------|
| **2.11.9** | 2025-11-03 | Test Suite: Phase 2 Auth & UI Tests (45% Failure Reduction, 25 Tests Fixed) - Fixed all breach detection tests (5/5, 100% pass) with HIBP API format, async context manager, datetime timezone fixes - Fixed 15/24 streamlit auth tests (63% reduction) by correcting 8 systematic module patch paths - Auth suite improved from 91.4% to 97.6% pass rate (413/423 tests) - Overall test health: 99.3% passing (4,164/4,194 tests) - Files modified: test_breach_detection_comprehensive.py (5 fixes), test_streamlit_auth_comprehensive.py (15 fixes), breach_detection.py (1 fix) - Documented 9 remaining auth failures (streamlit-authenticator mocking complexity) and 20 UI failures (property deleters, session_state mocking) - Updated testing_fixes_todo.md with complete Phase 2 analysis and Phase 3/4 roadmaps - Lessons: Mock at source, async __aexit__ handling, timezone awareness - Next: Phase 3 Remaining Auth Tests (9 failures, 2-3 hours) |
| **2.11.8** | 2025-11-03 | Test Suite: Phase 1 Async Mock Fixes Complete (P0 Blocking Issue) - Fixed critical async coroutine warnings (4 instances) - Changed AsyncMock(return_value=asyncio.sleep(0)) to AsyncMock(return_value=None) pattern - File: test_connection_manager_comprehensive.py - Verification: 308 tests passing, zero async warnings - Created comprehensive async mock best practices guide - Documentation: async_mock_best_practices.md and testing_fixes_todo.md updated - Impact: Eliminated P0 blocking warnings, established proper async mock patterns for future tests - Next: Phase 2 Authentication System Failures (101 tests, P1) |
| **2.11.7** | 2025-11-03 | Test Infrastructure: Fixed 6 Hanging CLI Tests and --quiet Flag Bug - Fixed indefinite test hangs by adding comprehensive mocking (loaders, scanners, all 6 rule classes) - Fixed --quiet flag production bug (was outputting full report instead of summary) - Performance improvement: Infinite hang to <2 seconds - Tests fixed: test_validate_quiet_mode_minimal_output, test_validate_staged_flag, test_validate_verbose_mode_detailed_output, test_validate_skip_git_flag, test_validate_json_format, test_validate_text_format - Root cause: Tests running real coverage/git checks instead of mocks - Impact: Improved test reliability, faster CI/CD, fixed CI/CD quiet mode usage |
| **2.11.6** | 2025-11-03 | Phase 10 Complete: Test Performance and Cleanup - Parallel test execution (pytest-xdist) for 60-70% speedup - CI/CD enhancements: coverage enforcement (75%), test reporting, timeout protection - Makefile targets: test-parallel, test-parallel-coverage, test-durations - datetime.utcnow() migration documentation (4 occurrences identified) - Expected performance: 44 min serial to 15-18 min parallel - Documentation: datetime_utcnow_migration.md and phase10_test_performance.md created |
| **2.11.5** | 2025-11-03 | Phase 9 Complete: Enable Skipped Tests (19 Tests Enabled, 1 Bug Fixed) - Reduced permanent skips from 23 to 7 (target achieved) - Added ENABLE_INTEGRATION_TESTS flag for 13 integration tests - Fixed CLI imports: enabled 18 tests - Fixed chunk_refs None handling bug: enabled 1 test - Fixed e2e tool imports: resolved 5 conditional skips - Enhanced skip documentation: 7 files updated with detailed reasons - Final breakdown: 7 permanent + 14 conditional (integration tests) + 5-10 dynamic skips - Documentation: phase9_skip_analysis.md and phase9_completion_summary.md created |
| **2.11.4** | 2025-11-03 | Phase 8 Complete: Test Execution Fixes (600+ Tests) - All 6 remaining Phase 8 files processed - Fixed critical mocking issues: Path.exists(), shutil.which, property patching - Test improvements: cli.py (45+ tests), streamlit_app.py (437/457 passing), streamlit_auth.py (59/83 passing), google_drive.py (32/55 passing), oauth_profile (4/4 passing), oauth_analytics (22/22 passing) - Established proper patterns for property decorators, async tests, import path resolution - Overall 85%+ pass rate improvement |

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version (X.0.0) for incompatible API changes
- **MINOR** version (0.X.0) for new functionality in a backward compatible manner
- **PATCH** version (0.0.X) for backward compatible bug fixes
