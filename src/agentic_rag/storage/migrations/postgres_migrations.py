"""
PostgreSQL migration system with version tracking and checksum validation.
"""

import asyncio
import hashlib
import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)


class PostgreSQLMigration:
    """Custom migration system for PostgreSQL with vector support."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent / "sql"

    async def initialize_schema(self):
        """Initialize the database schema with all required extensions and tables."""
        conn = await asyncpg.connect(self.database_url)

        try:
            # Create migration tracking table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    executed_at TIMESTAMPTZ DEFAULT NOW(),
                    execution_time_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """
            )

            # Run migrations in order
            migrations = self._get_migration_files()

            for migration_file in migrations:
                await self._run_migration(conn, migration_file)

            # Optimize database after migrations
            await self._optimize_database(conn)

            logger.info(f"Successfully completed {len(migrations)} migrations")

        finally:
            await conn.close()

    def _get_migration_files(self) -> list[Path]:
        """Get migration files in order."""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory {self.migrations_dir} does not exist")
            return []

        migrations = sorted(self.migrations_dir.glob("*.sql"))
        return migrations

    async def _run_migration(self, conn: asyncpg.Connection, migration_file: Path):
        """Run a single migration file."""
        version = migration_file.stem
        content = migration_file.read_text()
        checksum = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

        # Check if migration already applied
        existing = await conn.fetchrow(
            "SELECT checksum FROM schema_migrations WHERE version = $1", version
        )

        if existing:
            if existing["checksum"] != checksum:
                raise ValueError(f"Migration {version} has been modified after execution!")
            logger.info(f"Migration {version} already applied, skipping")
            return

        logger.info(f"Running migration {version}")
        start_time = asyncio.get_event_loop().time()

        try:
            # Run migration in transaction
            async with conn.transaction():
                await conn.execute(content)

                # Record successful migration
                elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                await conn.execute(
                    """
                    INSERT INTO schema_migrations (version, checksum, execution_time_ms)
                    VALUES ($1, $2, $3)
                """,
                    version,
                    checksum,
                    elapsed_ms,
                )

            logger.info(f"Migration {version} completed in {elapsed_ms}ms")

        except Exception as e:
            logger.error(f"Migration {version} failed: {e}")

            # Record failed migration
            await conn.execute(
                """
                INSERT INTO schema_migrations (version, checksum, success, error_message)
                VALUES ($1, $2, FALSE, $3)
                ON CONFLICT (version) DO UPDATE
                SET success = FALSE, error_message = $3
            """,
                version,
                checksum,
                str(e),
            )

            raise

    async def _optimize_database(self, conn: asyncpg.Connection):
        """Optimize database settings for vector search."""
        optimizations = [
            # Memory settings
            "ALTER SYSTEM SET shared_buffers = '2GB'",
            "ALTER SYSTEM SET effective_cache_size = '6GB'",
            "ALTER SYSTEM SET maintenance_work_mem = '512MB'",
            "ALTER SYSTEM SET work_mem = '50MB'",
            # Parallel query settings
            "ALTER SYSTEM SET max_parallel_workers_per_gather = 4",
            "ALTER SYSTEM SET max_parallel_workers = 8",
            "ALTER SYSTEM SET max_parallel_maintenance_workers = 4",
            # Write performance
            "ALTER SYSTEM SET wal_buffers = '16MB'",
            "ALTER SYSTEM SET checkpoint_completion_target = 0.9",
            "ALTER SYSTEM SET max_wal_size = '2GB'",
            "ALTER SYSTEM SET min_wal_size = '1GB'",
            # Query planner
            "ALTER SYSTEM SET random_page_cost = 1.1",  # For SSD
            "ALTER SYSTEM SET effective_io_concurrency = 200",  # For SSD
            # Vector-specific
            "ALTER SYSTEM SET ivfflat.probes = 10",  # For pgvector
        ]

        for setting in optimizations:
            try:
                await conn.execute(setting)
            except Exception as e:
                logger.warning(f"Could not apply setting '{setting}': {e}")

        # Reload configuration
        try:
            await conn.execute("SELECT pg_reload_conf()")
        except Exception as e:
            logger.warning(f"Could not reload configuration: {e}")

        # Analyze tables for query planner
        await conn.execute("ANALYZE")

        logger.info("Database optimization completed")

    async def rollback(self, target_version: str | None = None):
        """Rollback migrations to a specific version."""
        conn = await asyncpg.connect(self.database_url)

        try:
            # Get current migrations
            current_migrations = await conn.fetch(
                """
                SELECT version FROM schema_migrations
                WHERE success = TRUE
                ORDER BY executed_at DESC
            """
            )

            if not current_migrations:
                logger.info("No migrations to rollback")
                return

            # Determine migrations to rollback
            for migration in current_migrations:
                if target_version and migration["version"] == target_version:
                    break

                # Look for rollback file
                rollback_file = self.migrations_dir / f"{migration['version']}_rollback.sql"
                if rollback_file.exists():
                    logger.info(f"Rolling back migration {migration['version']}")
                    rollback_sql = rollback_file.read_text()

                    async with conn.transaction():
                        await conn.execute(rollback_sql)
                        await conn.execute(
                            "DELETE FROM schema_migrations WHERE version = $1", migration["version"]
                        )
                else:
                    logger.warning(f"No rollback file for {migration['version']}")

        finally:
            await conn.close()

    async def status(self) -> list[dict]:
        """Get migration status."""
        conn = await asyncpg.connect(self.database_url)

        try:
            # Get applied migrations
            applied = await conn.fetch(
                """
                SELECT version, checksum, executed_at, execution_time_ms, success
                FROM schema_migrations
                ORDER BY executed_at DESC
            """
            )

            # Get pending migrations
            applied_versions = {row["version"] for row in applied}
            all_migrations = self._get_migration_files()
            pending = [m.stem for m in all_migrations if m.stem not in applied_versions]

            return {
                "applied": [dict(row) for row in applied],
                "pending": pending,
                "total": len(all_migrations),
            }

        finally:
            await conn.close()


async def run_migrations(database_url: str):
    """Run all pending migrations."""
    migration = PostgreSQLMigration(database_url)
    await migration.initialize_schema()


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    asyncio.run(run_migrations(database_url))
