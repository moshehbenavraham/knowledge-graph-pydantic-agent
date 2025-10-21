"""
Constitution Compliance Validator.

A Python CLI tool that validates code changes against constitutional principles:
- I. Unified Agent Architecture
- II. Type-Safe Centralized Configuration
- III. Dual-Database Agentic RAG
- IV. Test-Driven Quality Assurance
- V. Production-Ready Observability
- VI. Git Attribution & Contribution Standards
"""

import logging

import structlog

__version__ = "1.0.0"

# Configure structured logging for the validator
# NOTE: This is library initialization, not user-facing configuration (Principle II exemption)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
