"""Health check and monitoring API endpoints."""

import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.utils.health import health_checker
from src.utils.monitoring import logger, monitor
from src.utils.rate_limiting import rate_limiter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def basic_health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "luminari-ai-agent",
        "version": os.getenv("APP_VERSION", "0.1.0"),
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with all component status."""
    try:
        health_status = await health_checker.get_health_status()

        # Convert to dict for JSON response
        response_data = {
            "status": health_status.status,
            "timestamp": health_status.timestamp.isoformat(),
            "uptime": health_status.uptime,
            "version": health_status.version,
            "checks": health_status.checks,
        }

        # Set appropriate HTTP status code
        status_code = 200
        if health_status.status == "degraded":
            status_code = 200  # Still operational
        elif health_status.status == "unhealthy":
            status_code = 503  # Service unavailable

        return JSONResponse(content=response_data, status_code=status_code)

    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            },
            status_code=503,
        )


@router.get("/metrics")
async def get_metrics():
    """Get system metrics and statistics."""
    try:
        system_stats = monitor.get_system_stats()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_stats,
            "prometheus_endpoint": f"http://localhost:{os.getenv('METRICS_PORT', '8000')}/metrics",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e!s}") from e


@router.get("/rate-limits/{user_id}")
async def get_rate_limit_status(user_id: str):
    """Get rate limiting status for a user."""
    try:
        stats = rate_limiter.get_all_stats(user_id)
        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get rate limit status: {e!s}"
        ) from e


@router.post("/rate-limits/{user_id}/tier")
async def set_user_tier(user_id: str, tier: str = Query(..., regex="^(free|premium|enterprise)$")):
    """Set user tier for rate limiting."""
    try:
        rate_limiter.user_limiter.set_user_tier(user_id, tier)
        return {"user_id": user_id, "tier": tier, "updated_at": datetime.utcnow().isoformat()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set user tier: {e!s}") from e


@router.get("/components/{component}")
async def get_component_health(component: str):
    """Get health status for a specific component."""
    try:
        if component == "database":
            health = await health_checker.check_database_health()
        elif component == "llm":
            health = await health_checker.check_llm_health()
        elif component == "embedding":
            health = await health_checker.check_embedding_health()
        elif component == "memory":
            health = await health_checker.check_memory_health()
        elif component == "web_search":
            health = await health_checker.check_web_search_health()
        else:
            raise HTTPException(status_code=404, detail=f"Unknown component: {component}")

        # Convert to dict
        response_data = {
            "name": health.name,
            "status": health.status,
            "response_time": health.response_time,
            "error": health.error,
            "last_check": health.last_check.isoformat(),
            "details": health.details,
        }

        # Set status code based on health
        status_code = 200
        if health.status == "degraded":
            status_code = 200
        elif health.status == "unhealthy":
            status_code = 503

        return JSONResponse(content=response_data, status_code=status_code)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to check component health: {e!s}"
        ) from e


@router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check critical components only
        db_health = await health_checker.check_database_health()
        llm_health = await health_checker.check_llm_health()

        if db_health.status == "unhealthy" or llm_health.status == "unhealthy":
            return JSONResponse(
                content={
                    "ready": False,
                    "timestamp": datetime.utcnow().isoformat(),
                    "critical_failures": [
                        comp.name for comp in [db_health, llm_health] if comp.status == "unhealthy"
                    ],
                },
                status_code=503,
            )

        return {"ready": True, "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        return JSONResponse(
            content={"ready": False, "timestamp": datetime.utcnow().isoformat(), "error": str(e)},
            status_code=503,
        )


@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    try:
        # Simple check that the service is running
        uptime = monitor.get_system_stats()["uptime"]

        return {"alive": True, "timestamp": datetime.utcnow().isoformat(), "uptime": uptime}

    except Exception as e:
        return JSONResponse(
            content={"alive": False, "timestamp": datetime.utcnow().isoformat(), "error": str(e)},
            status_code=503,
        )


@router.get("/startup")
async def startup_check():
    """Kubernetes startup probe endpoint."""
    try:
        # Check if all services have been initialized
        health_status = await health_checker.get_health_status()

        # Consider started if no components are completely unhealthy
        unhealthy_components = [
            name
            for name, check in health_status.checks.items()
            if check.get("status") == "unhealthy"
        ]

        if unhealthy_components:
            return JSONResponse(
                content={
                    "started": False,
                    "timestamp": datetime.utcnow().isoformat(),
                    "unhealthy_components": unhealthy_components,
                },
                status_code=503,
            )

        return {
            "started": True,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": health_status.uptime,
        }

    except Exception as e:
        return JSONResponse(
            content={"started": False, "timestamp": datetime.utcnow().isoformat(), "error": str(e)},
            status_code=503,
        )


# Initialize monitoring on module import
def initialize_monitoring():
    """Initialize monitoring and metrics collection."""
    try:
        # Start metrics server if enabled
        if os.getenv("ENABLE_METRICS", "true").lower() == "true":
            metrics_port = int(os.getenv("METRICS_PORT", "8000"))
            monitor.start_metrics_server(metrics_port)

        # Log initialization

        logger.info(
            "Monitoring initialized",
            metrics_enabled=os.getenv("ENABLE_METRICS", "true"),
            metrics_port=os.getenv("METRICS_PORT", "8000"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    except Exception as e:
        print(f"Failed to initialize monitoring: {e}")


# Initialize when module is imported
initialize_monitoring()
