#!/usr/bin/env python
"""
Initialize Agentic RAG databases (PostgreSQL and Neo4j).
Python alternative to the bash script for cross-platform compatibility.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agentic_rag.config import config
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.agentic_rag.storage.migrations.neo4j_init import Neo4jInitializer
from src.agentic_rag.storage.migrations.postgres_migrations import PostgreSQLMigration


def check_port(host: str, port: int) -> bool:
    """Check if a port is open."""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0


def wait_for_service(service_name: str, host: str, port: int, max_attempts: int = 30):
    """Wait for a service to be available."""
    print(f"Waiting for {service_name} on {host}:{port}...")

    for attempt in range(1, max_attempts + 1):
        if check_port(host, port):
            print(f"{service_name} is ready!")
            return True

        print(f"Attempt {attempt}/{max_attempts}: {service_name} not ready yet...")
        time.sleep(2)

    print(f"ERROR: {service_name} failed to start after {max_attempts} attempts")
    return False


def start_docker_services():
    """Start Docker services if configured."""
    print("\n=== Starting Docker Services ===\n")

    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("WARNING: Docker not found. Assuming services are already running.")
        return

    # Start PostgreSQL if configured
    if config.USE_LOCAL_POSTGRES:
        print("Starting PostgreSQL with pgvector...")

        # Stop existing container
        subprocess.run(
            ["docker", "stop", "agentic-rag-postgres"],
            check=False,
            capture_output=True,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rm", "agentic-rag-postgres"],
            check=False,
            capture_output=True,
            stderr=subprocess.DEVNULL,
        )

        # Start new container
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            "agentic-rag-postgres",
            "-e",
            f"POSTGRES_PASSWORD={config.POSTGRES_PASSWORD}",
            "-e",
            "POSTGRES_DB=agentic_rag",
            "-p",
            "5432:5432",
            "-v",
            "agentic_rag_pgdata:/var/lib/postgresql/data",
            "pgvector/pgvector:pg16",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print("PostgreSQL container started")

            if not wait_for_service("PostgreSQL", "localhost", 5432):
                sys.exit(1)

            # Extra wait for PostgreSQL initialization
            print("Waiting for PostgreSQL to fully initialize...")
            time.sleep(5)

        except subprocess.CalledProcessError as e:
            print(f"Failed to start PostgreSQL: {e}")
            sys.exit(1)

    # Start Neo4j if configured
    if config.USE_LOCAL_NEO4J:
        print("Starting Neo4j...")

        # Stop existing container
        subprocess.run(
            ["docker", "stop", "agentic-rag-neo4j"],
            check=False,
            capture_output=True,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rm", "agentic-rag-neo4j"],
            check=False,
            capture_output=True,
            stderr=subprocess.DEVNULL,
        )

        # Start new container
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            "agentic-rag-neo4j",
            "-e",
            f"NEO4J_AUTH={config.NEO4J_USER}/{config.NEO4J_PASSWORD}",
            "-e",
            'NEO4J_PLUGINS=["apoc", "graph-data-science"]',
            "-e",
            "NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*",
            "-p",
            "7475:7474",
            "-p",
            "7688:7687",
            "-v",
            "agentic_rag_neodata:/data",
            "neo4j:5",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print("Neo4j container started")

            if not wait_for_service("Neo4j", "localhost", 7688):
                sys.exit(1)

            # Extra wait for Neo4j initialization
            print("Waiting for Neo4j to fully initialize...")
            time.sleep(10)

        except subprocess.CalledProcessError as e:
            print(f"Failed to start Neo4j: {e}")
            sys.exit(1)

    # Start Redis if configured
    if config.ENABLE_REDIS_CACHE and config.USE_LOCAL_REDIS:
        print("Starting Redis...")

        # Stop existing container
        subprocess.run(
            ["docker", "stop", "agentic-rag-redis"],
            check=False,
            capture_output=True,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rm", "agentic-rag-redis"],
            check=False,
            capture_output=True,
            stderr=subprocess.DEVNULL,
        )

        # Start new container
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            "agentic-rag-redis",
            "-p",
            "6381:6379",
            "redis:7-alpine",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print("Redis container started")

            if not wait_for_service("Redis", "localhost", 6381):
                sys.exit(1)

        except subprocess.CalledProcessError as e:
            print(f"Failed to start Redis: {e}")
            sys.exit(1)


async def run_migrations():
    """Run database migrations."""
    print("\n=== Running Database Migrations ===\n")

    # PostgreSQL migrations
    print("Running PostgreSQL migrations...")
    try:
        pg_migration = PostgreSQLMigration(config.DATABASE_URL)
        await pg_migration.initialize_schema()

        # Get migration status
        status = await pg_migration.status()
        print(f"  Applied migrations: {len(status['applied'])}")
        print(f"  Pending migrations: {len(status['pending'])}")

    except Exception as e:
        print(f"PostgreSQL migration failed: {e}")
        sys.exit(1)

    # Neo4j initialization
    print("\nInitializing Neo4j...")
    try:
        neo4j_init = Neo4jInitializer(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD)
        await neo4j_init.initialize()

        # Get statistics
        stats = await neo4j_init.get_statistics()
        print(f"  Entity count: {stats.get('entity_count', 0)}")
        print(f"  Relationship count: {stats.get('relationship_count', 0)}")

    except Exception as e:
        print(f"Neo4j initialization failed: {e}")
        sys.exit(1)


async def health_check():
    """Run health checks on all services."""
    print("\n=== Running Health Checks ===\n")

    try:
        # Create connection manager
        conn_manager = ConnectionManager(config.dict())
        await conn_manager.initialize()

        # Run health check
        health = await conn_manager.health_check()

        # Display results
        print("Health Check Results:")

        # PostgreSQL
        pg_health = health["services"]["postgresql"]
        status = "✓" if pg_health["healthy"] else "✗"
        print(f"  PostgreSQL: {status}")
        if pg_health["healthy"]:
            metrics = pg_health["metrics"]
            print(f"    - Total connections: {metrics['total_connections']}")
            print(f"    - Total queries: {metrics['total_queries']}")

        # Neo4j
        neo4j_health = health["services"]["neo4j"]
        status = "✓" if neo4j_health["healthy"] else "✗"
        print(f"  Neo4j: {status}")
        if neo4j_health["healthy"]:
            metrics = neo4j_health["metrics"]
            print(f"    - Total queries: {metrics['total_queries']}")

        # Redis
        if "redis" in health["services"]:
            redis_health = health["services"]["redis"]
            status = "✓" if redis_health["healthy"] else "✗"
            print(f"  Redis: {status}")

        print(f"\n  Overall Health: {health['overall_health']}")

        # Close connections
        await conn_manager.close()

        return health["overall_health"] == "healthy"

    except Exception as e:
        print(f"Health check failed: {e}")
        return False


async def main():
    """Main initialization function."""
    print("===================================")
    print("Initializing Agentic RAG Databases")
    print("===================================")

    # Start Docker services if needed
    if any(
        [
            config.USE_LOCAL_POSTGRES,
            config.USE_LOCAL_NEO4J,
            (config.ENABLE_REDIS_CACHE and config.USE_LOCAL_REDIS),
        ]
    ):
        start_docker_services()

    # Run migrations
    await run_migrations()

    # Run health checks
    healthy = await health_check()

    if healthy:
        print("\n===================================")
        print("Database initialization complete!")
        print("===================================")
        print("\nServices running:")
        print(f"  - PostgreSQL: {config.DATABASE_URL}")
        print(f"  - Neo4j: {config.NEO4J_URI}")
        if config.ENABLE_REDIS_CACHE:
            print(f"  - Redis: {config.REDIS_URL}")
        print("\nNeo4j Browser: http://localhost:7475")
        print("\nYou can now run the application with:")
        print("  python -m src.agentic_rag.api.app")
        print("\nTo stop Docker services:")
        print("  docker stop agentic-rag-postgres agentic-rag-neo4j agentic-rag-redis")
    else:
        print("\n⚠️  Some services are not healthy. Please check the logs.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
