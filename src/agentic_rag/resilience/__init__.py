"""
Resilience module for error handling and fault tolerance.

Provides retry decorators, circuit breakers, graceful degradation,
and user-friendly error messaging for the Agentic GraphRAG system.

Example usage:
    from src.agentic_rag.resilience import (
        with_retry,
        with_circuit_breaker,
        with_resilience,
        neo4j_circuit_breaker,
        supabase_circuit_breaker,
        format_error_for_user,
    )

    # Retry decorator
    @with_retry(max_attempts=3)
    async def fetch_data():
        return await api.get()

    # Circuit breaker decorator
    @with_circuit_breaker(ServiceType.NEO4J)
    async def query_graph():
        return await neo4j.run(query)

    # Combined resilience
    @with_resilience(ServiceType.NEO4J, max_attempts=3)
    async def query_with_resilience():
        return await neo4j.run(query)
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
    get_circuit_breaker,
    get_circuit_breaker_registry,
)
from .decorators import (
    calculate_backoff_delay,
    with_circuit_breaker,
    with_resilience,
    with_retry,
)
from .error_types import (
    CircuitOpenError,
    ErrorCategory,
    ErrorContext,
    GracefulDegradationError,
    MaxRetriesExceededError,
    ResilienceError,
    ServiceType,
    categorize_exception,
)
from .handlers import (
    DegradationResult,
    DegradationState,
    GracefulDegradationHandler,
    SearchDegradationHandler,
    get_search_degradation_handler,
)
from .messages import (
    ErrorMessageFormatter,
    format_degradation_notice,
    format_error_for_user,
    format_retry_notice,
    get_service_display_name,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitOpenError",
    "CircuitState",
    "DegradationResult",
    "DegradationState",
    "ErrorCategory",
    "ErrorContext",
    "ErrorMessageFormatter",
    "GracefulDegradationError",
    "GracefulDegradationHandler",
    "MaxRetriesExceededError",
    "ResilienceError",
    "SearchDegradationHandler",
    "ServiceType",
    "calculate_backoff_delay",
    "categorize_exception",
    "embedding_circuit_breaker",
    "format_degradation_notice",
    "format_error_for_user",
    "format_retry_notice",
    "get_circuit_breaker",
    "get_circuit_breaker_registry",
    "get_search_degradation_handler",
    "get_service_display_name",
    "llm_circuit_breaker",
    "neo4j_circuit_breaker",
    "supabase_circuit_breaker",
    "with_circuit_breaker",
    "with_resilience",
    "with_retry",
]


def neo4j_circuit_breaker() -> CircuitBreaker:
    """
    Get the circuit breaker for Neo4j.

    Returns:
        CircuitBreaker instance for Neo4j service
    """
    return get_circuit_breaker(ServiceType.NEO4J)


def supabase_circuit_breaker() -> CircuitBreaker:
    """
    Get the circuit breaker for Supabase.

    Returns:
        CircuitBreaker instance for Supabase service
    """
    return get_circuit_breaker(ServiceType.SUPABASE)


def embedding_circuit_breaker() -> CircuitBreaker:
    """
    Get the circuit breaker for embedding API.

    Returns:
        CircuitBreaker instance for embedding API service
    """
    return get_circuit_breaker(ServiceType.EMBEDDING_API)


def llm_circuit_breaker() -> CircuitBreaker:
    """
    Get the circuit breaker for LLM API.

    Returns:
        CircuitBreaker instance for LLM API service
    """
    return get_circuit_breaker(ServiceType.LLM_API)
