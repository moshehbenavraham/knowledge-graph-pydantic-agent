"""Health check and system monitoring utilities."""

import asyncio
import contextlib
import time
from datetime import datetime

import httpx
from pydantic import BaseModel

from src.config import get_settings

try:
    from clients.database import get_supabase_client
except ImportError:
    get_supabase_client = None

try:
    from clients.llm import get_llm_client
except ImportError:
    get_llm_client = None

try:
    from clients.embedding import get_embedding_client
except ImportError:
    get_embedding_client = None

try:
    from clients.memory import get_mem0_client
except ImportError:
    get_mem0_client = None

from .monitoring import logger, monitor


class HealthStatus(BaseModel):
    """Health check status model."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    uptime: float
    version: str
    checks: dict[str, dict]


class ComponentHealth(BaseModel):
    """Individual component health status."""

    name: str
    status: str
    response_time: float | None = None
    error: str | None = None
    last_check: datetime
    details: dict | None = None


class HealthChecker:
    """System health monitoring and checks."""

    def __init__(self):
        settings = get_settings()
        self.start_time = time.time()
        self.version = settings.app_version
        self.check_interval = settings.health_check_interval
        self.component_checks = {}
        self.last_full_check = None

    async def check_database_health(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        start_time = time.time()

        try:
            if not get_supabase_client:
                raise ImportError("Database client not available")

            supabase = get_supabase_client()

            # Simple connectivity test
            result = supabase.rpc("execute_sql", {"query": "SELECT 1 as health_check"}).execute()

            response_time = time.time() - start_time

            if result.data and len(result.data) > 0:
                return ComponentHealth(
                    name="database",
                    status="healthy",
                    response_time=response_time,
                    last_check=datetime.utcnow(),
                    details={"connection": "ok", "query_time": response_time},
                )
            return ComponentHealth(
                name="database",
                status="degraded",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error="Empty response from database",
            )

        except Exception as e:
            response_time = time.time() - start_time
            logger.error("Database health check failed", error=str(e), response_time=response_time)

            return ComponentHealth(
                name="database",
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error=str(e),
            )

    async def check_llm_health(self) -> ComponentHealth:
        """Check LLM service connectivity and performance."""
        start_time = time.time()

        try:
            if not get_llm_client:
                raise ImportError("LLM client not available")

            settings = get_settings()
            client = get_llm_client()

            # Simple test request
            response = await client.chat.completions.create(
                model=settings.llm_choice,
                messages=[{"role": "user", "content": "Health check"}],
                max_tokens=5,
            )

            response_time = time.time() - start_time

            if response and response.choices:
                return ComponentHealth(
                    name="llm",
                    status="healthy",
                    response_time=response_time,
                    last_check=datetime.utcnow(),
                    details={
                        "model": response.model,
                        "tokens_used": response.usage.total_tokens if response.usage else 0,
                    },
                )
            return ComponentHealth(
                name="llm",
                status="degraded",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error="Empty response from LLM",
            )

        except Exception as e:
            response_time = time.time() - start_time
            logger.error("LLM health check failed", error=str(e), response_time=response_time)

            return ComponentHealth(
                name="llm",
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error=str(e),
            )

    async def check_embedding_health(self) -> ComponentHealth:
        """Check embedding service connectivity and performance."""
        start_time = time.time()

        try:
            if not get_embedding_client:
                raise ImportError("Embedding client not available")

            settings = get_settings()
            client = get_embedding_client()

            # Simple embedding test
            response = await client.embeddings.create(
                model=settings.embedding_model_choice,
                input="health check",
            )

            response_time = time.time() - start_time

            if response and response.data:
                return ComponentHealth(
                    name="embedding",
                    status="healthy",
                    response_time=response_time,
                    last_check=datetime.utcnow(),
                    details={
                        "model": response.model,
                        "embedding_dim": len(response.data[0].embedding),
                    },
                )
            return ComponentHealth(
                name="embedding",
                status="degraded",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error="Empty response from embedding service",
            )

        except Exception as e:
            response_time = time.time() - start_time
            logger.error("Embedding health check failed", error=str(e), response_time=response_time)

            return ComponentHealth(
                name="embedding",
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error=str(e),
            )

    async def check_memory_health(self) -> ComponentHealth:
        """Check memory service connectivity and performance."""
        start_time = time.time()

        try:
            if not get_mem0_client:
                raise ImportError("Memory client not available")

            client = get_mem0_client()

            # Simple memory test
            test_memory = "Health check memory test"
            result = client.add(test_memory, user_id="health_check")

            response_time = time.time() - start_time

            if result and result.get("id"):
                # Clean up test memory
                with contextlib.suppress(Exception):
                    client.delete(result["id"])

                return ComponentHealth(
                    name="memory",
                    status="healthy",
                    response_time=response_time,
                    last_check=datetime.utcnow(),
                    details={"test_memory_id": result["id"]},
                )
            return ComponentHealth(
                name="memory",
                status="degraded",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error="Failed to create test memory",
            )

        except Exception as e:
            response_time = time.time() - start_time
            logger.error("Memory health check failed", error=str(e), response_time=response_time)

            return ComponentHealth(
                name="memory",
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error=str(e),
            )

    async def check_web_search_health(self) -> ComponentHealth:
        """Check web search service connectivity."""
        start_time = time.time()

        try:
            settings = get_settings()
            brave_api_key = settings.brave_api_key
            searxng_url = settings.searxng_base_url

            if brave_api_key:
                # Test Brave API
                async with (
                    httpx.AsyncClient()  # noqa: CONST-III-001 - Health check ephemeral client as client
                ):  # noqa: CONST-III-001 - Health check uses ephemeral client
                    response = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        params={"q": "health check", "count": 1},
                        headers={"X-Subscription-Token": brave_api_key},
                        timeout=10.0,
                    )

                    response_time = time.time() - start_time

                    if response.status_code == 200:
                        return ComponentHealth(
                            name="web_search",
                            status="healthy",
                            response_time=response_time,
                            last_check=datetime.utcnow(),
                            details={"provider": "brave", "status_code": response.status_code},
                        )
                    return ComponentHealth(
                        name="web_search",
                        status="degraded",
                        response_time=response_time,
                        last_check=datetime.utcnow(),
                        error=f"Brave API returned status {response.status_code}",
                    )

            elif searxng_url:
                # Test SearXNG
                async with (
                    httpx.AsyncClient()  # noqa: CONST-III-001 - Health check ephemeral client as client
                ):  # noqa: CONST-III-001 - Health check uses ephemeral client
                    response = await client.get(
                        f"{searxng_url}/search",
                        params={"q": "health check", "format": "json"},
                        timeout=10.0,
                    )

                    response_time = time.time() - start_time

                    if response.status_code == 200:
                        return ComponentHealth(
                            name="web_search",
                            status="healthy",
                            response_time=response_time,
                            last_check=datetime.utcnow(),
                            details={"provider": "searxng", "status_code": response.status_code},
                        )
                    return ComponentHealth(
                        name="web_search",
                        status="degraded",
                        response_time=response_time,
                        last_check=datetime.utcnow(),
                        error=f"SearXNG returned status {response.status_code}",
                    )
            else:
                return ComponentHealth(
                    name="web_search",
                    status="unhealthy",
                    response_time=0,
                    last_check=datetime.utcnow(),
                    error="No web search provider configured",
                )

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(
                "Web search health check failed", error=str(e), response_time=response_time
            )

            return ComponentHealth(
                name="web_search",
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.utcnow(),
                error=str(e),
            )

    async def run_all_checks(self) -> list[ComponentHealth]:
        """Run all health checks concurrently."""
        checks = await asyncio.gather(
            self.check_database_health(),
            self.check_llm_health(),
            self.check_embedding_health(),
            self.check_memory_health(),
            self.check_web_search_health(),
            return_exceptions=True,
        )

        # Filter out exceptions and convert to ComponentHealth objects
        valid_checks = []
        for check in checks:
            if isinstance(check, ComponentHealth):
                valid_checks.append(check)
            elif isinstance(check, Exception):
                logger.error("Health check failed with exception", error=str(check))
                valid_checks.append(
                    ComponentHealth(
                        name="unknown",
                        status="unhealthy",
                        last_check=datetime.utcnow(),
                        error=str(check),
                    )
                )

        self.last_full_check = datetime.utcnow()
        return valid_checks

    async def get_health_status(self) -> HealthStatus:
        """Get overall system health status."""
        checks = await self.run_all_checks()

        # Determine overall status
        unhealthy_count = sum(1 for check in checks if check.status == "unhealthy")
        degraded_count = sum(1 for check in checks if check.status == "degraded")

        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        # Convert checks to dict format
        checks_dict = {}
        for check in checks:
            checks_dict[check.name] = {
                "status": check.status,
                "response_time": check.response_time,
                "error": check.error,
                "last_check": check.last_check.isoformat(),
                "details": check.details,
            }

        # Add system stats
        system_stats = monitor.get_system_stats()
        checks_dict["system"] = {
            "status": (
                "healthy"
                if system_stats["cpu_percent"] < 80 and system_stats["disk_usage"] < 90
                else "degraded"
            ),
            "uptime": system_stats["uptime"],
            "active_requests": system_stats["active_requests"],
            "active_sessions": system_stats["active_sessions"],
            "cpu_percent": system_stats["cpu_percent"],
            "memory_usage": system_stats["memory_usage"],
            "disk_usage": system_stats["disk_usage"],
        }

        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime=time.time() - self.start_time,
            version=self.version,
            checks=checks_dict,
        )


# Global health checker instance
health_checker = HealthChecker()
