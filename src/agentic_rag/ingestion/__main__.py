"""
CLI interface for document ingestion pipeline.

Usage:
    python -m src.agentic_rag.ingestion.pipeline ingest [--path PATH] [--clean]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env with override to ignore cached shell variables
load_dotenv(override=True)

# Reload settings to pick up new environment variables
from src.config import reload_settings

reload_settings()

from .pipeline import DocumentIngestionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def ingest_directory(pipeline: DocumentIngestionPipeline, directory: Path) -> None:
    """
    Ingest all markdown files from a directory.

    Args:
        pipeline: DocumentIngestionPipeline instance (must be initialized)
        directory: Directory containing documents
    """
    # Ensure pipeline is initialized
    if not pipeline._initialized:
        raise RuntimeError(
            "Pipeline not initialized! Call await pipeline.initialize() first or use async with."
        )

    # Find all markdown files
    md_files = list(directory.glob("**/*.md"))

    if not md_files:
        logger.warning(f"No markdown files found in {directory}")
        return

    logger.info(f"Found {len(md_files)} markdown files to ingest")

    # Prepare documents
    documents = []
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            documents.append(
                {
                    "content": content,
                    "title": md_file.stem.replace("_", " ").title(),
                    "source": str(md_file),
                    "metadata": {
                        "file_name": md_file.name,
                        "file_path": str(md_file.absolute()),
                    },
                }
            )
        except Exception as e:
            logger.error(f"Failed to read {md_file}: {e}")

    if not documents:
        logger.error("No documents could be loaded")
        return

    # Ingest in batch
    logger.info(f"Starting batch ingestion of {len(documents)} documents...")
    results = await pipeline.ingest_batch(documents, max_concurrent=3)

    # Print results
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    logger.info(f"\n{'='*70}")
    logger.info("Ingestion Complete!")
    logger.info(f"{'='*70}")
    logger.info(f"Total documents: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    # Print detailed stats
    stats = pipeline.get_stats()
    logger.info("\nStatistics:")
    logger.info(f"  Chunks created: {stats['chunks_created']}")
    logger.info(f"  Entities extracted: {stats['entities_extracted']}")
    logger.info(f"  Facts extracted: {stats['facts_extracted']}")
    if "avg_chunks_per_doc" in stats:
        logger.info(f"  Avg chunks/doc: {stats['avg_chunks_per_doc']:.1f}")
        logger.info(f"  Avg entities/doc: {stats['avg_entities_per_doc']:.1f}")
        logger.info(f"  Avg facts/doc: {stats['avg_facts_per_doc']:.1f}")

    # Print failures
    if failed > 0:
        logger.info("\nFailed documents:")
        for result in results:
            if not result.success:
                logger.error(f"  - {result.title}: {', '.join(result.errors)}")


async def main() -> None:
    """Main CLI entry point with proper async initialization."""
    parser = argparse.ArgumentParser(description="Document ingestion pipeline")
    parser.add_argument(
        "command",
        choices=["ingest"],
        help="Command to execute",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="docs/example_docs",
        help="Path to directory containing documents",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing data before ingestion",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--rest-api",
        action="store_true",
        default=False,
        help="Force use of Supabase REST API (fallback when PostgreSQL ports blocked)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.command == "ingest":
        # Resolve path
        path = Path(args.path)
        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            sys.exit(1)

        if not path.is_dir():
            logger.error(f"Path is not a directory: {path}")
            sys.exit(1)

        # Initialize pipeline with proper async pattern
        logger.info("Initializing ingestion pipeline...")

        if args.rest_api:
            # User explicitly requested REST API
            logger.info("→ Using Supabase REST API (forced by --rest-api flag)")
            use_rest_api = True
        else:
            # Try PostgreSQL + Neo4j (full Agentic RAG)
            logger.info("→ Attempting direct PostgreSQL + Neo4j connections...")
            use_rest_api = False

        # Use async context manager for automatic cleanup
        try:
            async with DocumentIngestionPipeline(use_rest_api=use_rest_api) as pipeline:
                logger.info("✅ Pipeline initialized successfully")

                # Run ingestion
                await ingest_directory(pipeline, path)

                logger.info("\n✅ Ingestion complete!")

        except Exception as e:
            if not use_rest_api:
                # PostgreSQL failed, fallback to REST API
                logger.warning(f"⚠️  PostgreSQL initialization failed: {e}")
                logger.info("→ Falling back to Supabase REST API...")

                async with DocumentIngestionPipeline(use_rest_api=True) as pipeline:
                    logger.info("✅ Pipeline initialized with REST API fallback")
                    await ingest_directory(pipeline, path)
                    logger.info("\n✅ Ingestion complete!")
            else:
                raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nIngestion cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\nIngestion failed: {e}", exc_info=True)
        sys.exit(1)
