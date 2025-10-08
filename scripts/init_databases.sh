#!/bin/bash
# Initialize Agentic RAG databases (PostgreSQL and Neo4j)

set -e

echo "==================================="
echo "Initializing Agentic RAG Databases"
echo "==================================="

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "Warning: .env file not found. Using environment variables."
fi

# Set default values if not provided
USE_LOCAL_POSTGRES=${USE_LOCAL_POSTGRES:-true}
USE_LOCAL_NEO4J=${USE_LOCAL_NEO4J:-true}
USE_LOCAL_REDIS=${USE_LOCAL_REDIS:-false}
ENABLE_REDIS_CACHE=${ENABLE_REDIS_CACHE:-false}

POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-password}

# Function to check if service is ready
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1

    echo "Waiting for $service on port $port..."

    while ! nc -z localhost $port 2>/dev/null; do
        if [ $attempt -eq $max_attempts ]; then
            echo "ERROR: $service failed to start after $max_attempts attempts"
            exit 1
        fi

        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "$service is ready!"
}

# Function to check if Docker is running
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker is not installed"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo "ERROR: Docker daemon is not running"
        exit 1
    fi
}

# Start PostgreSQL if using local instance
if [ "$USE_LOCAL_POSTGRES" = "true" ]; then
    check_docker

    echo "Starting PostgreSQL with pgvector..."

    # Stop and remove existing container if it exists
    docker stop agentic-rag-postgres 2>/dev/null || true
    docker rm agentic-rag-postgres 2>/dev/null || true

    # Start PostgreSQL with pgvector
    docker run -d \
        --name agentic-rag-postgres \
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
        -e POSTGRES_DB=agentic_rag \
        -p 5432:5432 \
        -v agentic_rag_pgdata:/var/lib/postgresql/data \
        pgvector/pgvector:pg16

    wait_for_service "PostgreSQL" 5432

    # Wait a bit more for PostgreSQL to fully initialize
    echo "Waiting for PostgreSQL to fully initialize..."
    sleep 5

    # Set DATABASE_URL for local PostgreSQL
    export DATABASE_URL="postgresql://postgres:$POSTGRES_PASSWORD@localhost:5432/agentic_rag"
fi

# Start Neo4j if using local instance
if [ "$USE_LOCAL_NEO4J" = "true" ]; then
    check_docker

    echo "Starting Neo4j..."

    # Stop and remove existing container if it exists
    docker stop agentic-rag-neo4j 2>/dev/null || true
    docker rm agentic-rag-neo4j 2>/dev/null || true

    # Start Neo4j
    docker run -d \
        --name agentic-rag-neo4j \
        -e NEO4J_AUTH=$NEO4J_USER/$NEO4J_PASSWORD \
        -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
        -e NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.* \
        -p 7474:7474 \
        -p 7687:7687 \
        -v agentic_rag_neodata:/data \
        neo4j:5

    wait_for_service "Neo4j" 7687

    # Wait additional time for Neo4j to fully initialize
    echo "Waiting for Neo4j to fully initialize..."
    sleep 10

    # Set Neo4j environment variables
    export NEO4J_URI="bolt://localhost:7687"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="$NEO4J_PASSWORD"
fi

# Start Redis if caching is enabled
if [ "$ENABLE_REDIS_CACHE" = "true" ] && [ "$USE_LOCAL_REDIS" = "true" ]; then
    check_docker

    echo "Starting Redis..."

    # Stop and remove existing container if it exists
    docker stop agentic-rag-redis 2>/dev/null || true
    docker rm agentic-rag-redis 2>/dev/null || true

    docker run -d \
        --name agentic-rag-redis \
        -p 6379:6379 \
        redis:7-alpine

    wait_for_service "Redis" 6379

    export REDIS_URL="redis://localhost:6379"
fi

echo ""
echo "Running PostgreSQL migrations..."
python -m src.agentic_rag.storage.migrations.postgres_migrations

echo ""
echo "Initializing Neo4j with custom indexes..."
python -m src.agentic_rag.storage.migrations.neo4j_init

echo ""
echo "Running health checks..."
python -c "
import asyncio
from src.agentic_rag.storage.connection_manager import get_connection_manager

async def check_health():
    manager = await get_connection_manager()
    health = await manager.health_check()

    print('\nHealth Check Results:')
    print(f\"  PostgreSQL: {'✓' if health['services']['postgresql']['healthy'] else '✗'}\")
    print(f\"  Neo4j: {'✓' if health['services']['neo4j']['healthy'] else '✗'}\")
    if 'redis' in health['services']:
        print(f\"  Redis: {'✓' if health['services']['redis']['healthy'] else '✗'}\")
    print(f\"  Overall: {health['overall_health']}\")

    await manager.close()

asyncio.run(check_health())
"

echo ""
echo "==================================="
echo "Database initialization complete!"
echo "==================================="
echo ""
echo "Services running:"
echo "  - PostgreSQL: ${DATABASE_URL:-$SUPABASE_URL}"
echo "  - Neo4j: ${NEO4J_URI}"
if [ "$ENABLE_REDIS_CACHE" = "true" ]; then
    echo "  - Redis: ${REDIS_URL}"
fi
echo ""
echo "Neo4j Browser: http://localhost:7474"
echo ""
echo "You can now run the application with:"
echo "  python -m src.agentic_rag.api.app"
echo ""
echo "To stop the services:"
echo "  docker stop agentic-rag-postgres agentic-rag-neo4j agentic-rag-redis"
echo ""
echo "To remove the services and data:"
echo "  docker rm agentic-rag-postgres agentic-rag-neo4j agentic-rag-redis"
echo "  docker volume rm agentic_rag_pgdata agentic_rag_neodata"
echo ""
