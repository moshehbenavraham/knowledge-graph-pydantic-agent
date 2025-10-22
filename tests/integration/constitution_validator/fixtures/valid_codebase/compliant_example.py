"""
Example of compliant code that follows all constitutional principles.

This file demonstrates proper usage of:
- Centralized configuration (Principle II)
- Observability (Principle V)
"""

import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


def process_data(input_data: str) -> dict:
    """
    Process input data with proper logging and configuration.

    Args:
        input_data: Data to process

    Returns:
        Processed result dictionary
    """
    logger.info("Processing data", input_length=len(input_data))

    # ✓ CORRECT: Use centralized configuration
    settings = get_settings()
    api_key = settings.api_key

    # ✓ CORRECT: Structured logging throughout
    logger.debug("Configuration loaded", has_api_key=bool(api_key))

    result = {"status": "success", "data": input_data.upper()}

    logger.info("Data processing complete", result_status=result["status"])

    return result


class CompliantService:
    """Example service following constitutional principles."""

    def __init__(self):
        """Initialize service with proper configuration."""
        logger.info("Initializing CompliantService")
        self.settings = get_settings()

    def execute(self, task_id: str) -> None:
        """
        Execute a task with logging.

        Args:
            task_id: Unique task identifier
        """
        logger.info("Executing task", task_id=task_id)

        # Service logic here
        logger.debug("Task processing", task_id=task_id)

        logger.info("Task completed", task_id=task_id)
