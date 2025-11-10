"""
PDF Document Ingestion Script for Agentic RAG.

This script processes PDF files through the complete agentic RAG pipeline:
- PDF text extraction (pypdf)
- Semantic chunking
- Embedding generation (OpenAI text-embedding-3-small)
- Knowledge extraction (entities, relationships, facts via Graphiti)
- Dual storage (PostgreSQL vector store + Neo4j knowledge graph)

Usage:
    python scripts/ingest_pdfs.py --path docs/x-examples/ [--clean]
"""

import asyncio
import logging
import sys
from pathlib import Path

import structlog

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

from src.config import reload_settings

reload_settings()

from src.agentic_rag.ingestion.pipeline import DocumentIngestionPipeline
from src.rag_pipeline.common.text_processor import extract_text_from_pdf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
structlog_logger = structlog.get_logger(__name__)


async def ingest_pdf_directory(pipeline: DocumentIngestionPipeline, directory: Path):
    """
    Ingest all PDF files from a directory through the agentic RAG pipeline.

    Args:
        pipeline: DocumentIngestionPipeline instance (must be initialized)
        directory: Directory containing PDF files
    """
    # Ensure pipeline is initialized
    if not pipeline._initialized:
        raise RuntimeError(
            "Pipeline not initialized! Call await pipeline.initialize() first or use async with."
        )

    # Find all PDF files
    pdf_files = list(directory.glob("**/*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDF files found in {directory}")
        return

    logger.info(f"Found {len(pdf_files)} PDF files to ingest")
    logger.info("=" * 80)

    # Prepare documents
    documents = []
    for pdf_file in pdf_files:
        try:
            logger.info(f"Processing: {pdf_file.name}")

            # Read PDF binary content
            pdf_content = pdf_file.read_bytes()
            logger.info(f"  File size: {len(pdf_content) / 1024:.2f} KB")

            # Extract text using pypdf
            logger.info("  Extracting text from PDF...")
            text_content = extract_text_from_pdf(pdf_content)

            if not text_content or len(text_content.strip()) < 100:
                logger.warning(
                    f"  ⚠️  Skipping {pdf_file.name} - extracted text too short "
                    f"({len(text_content)} chars)"
                )
                continue

            logger.info(
                f"  ✅ Extracted {len(text_content)} characters, "
                f"{len(text_content.split())} words"
            )

            # Parse filename for metadata (e.g., "2022 Q3 AAPL.pdf")
            parts = pdf_file.stem.split()
            year = parts[0] if len(parts) > 0 else "Unknown"
            quarter = parts[1] if len(parts) > 1 else "Unknown"
            ticker = parts[2] if len(parts) > 2 else pdf_file.stem

            documents.append(
                {
                    "content": text_content,
                    "title": pdf_file.stem,
                    "source": str(pdf_file),
                    "metadata": {
                        "file_name": pdf_file.name,
                        "file_path": str(pdf_file.absolute()),
                        "file_type": "pdf",
                        "year": year,
                        "quarter": quarter,
                        "ticker": ticker,
                        "original_size_kb": len(pdf_content) / 1024,
                        "extracted_chars": len(text_content),
                    },
                }
            )

            logger.info(f"  ✅ Prepared document: {pdf_file.name}")

        except Exception as e:
            logger.error(f"  ❌ Failed to process {pdf_file.name}: {e}", exc_info=True)

    if not documents:
        logger.error("No documents could be loaded")
        return

    logger.info("=" * 80)
    logger.info(f"Starting batch ingestion of {len(documents)} documents...")
    logger.info("=" * 80)

    # Ingest in batch with reduced concurrency for large PDFs
    results = await pipeline.ingest_batch(documents, max_concurrent=2)

    # Print results
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    logger.info("\n" + "=" * 80)
    logger.info("🎉 INGESTION COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"Total documents: {len(results)}")
    logger.info(f"✅ Successful: {successful}")
    logger.info(f"❌ Failed: {failed}")

    # Print detailed stats
    stats = pipeline.get_stats()
    logger.info("\n📊 Statistics:")
    logger.info(f"  Chunks created: {stats['chunks_created']}")
    logger.info(f"  Entities extracted: {stats['entities_extracted']}")
    logger.info(f"  Facts extracted: {stats['facts_extracted']}")
    if stats["documents_processed"] > 0:
        logger.info(
            f"  Avg chunks/doc: {stats['chunks_created'] / stats['documents_processed']:.1f}"
        )
        logger.info(
            f"  Avg entities/doc: "
            f"{stats['entities_extracted'] / stats['documents_processed']:.1f}"
        )
        logger.info(
            f"  Avg facts/doc: {stats['facts_extracted'] / stats['documents_processed']:.1f}"
        )

    # Print successful documents
    if successful > 0:
        logger.info("\n✅ Successfully ingested:")
        for result in results:
            if result.success:
                logger.info(
                    f"  • {result.title}: {result.chunks_created} chunks, "
                    f"{result.entities_extracted} entities, "
                    f"{result.facts_extracted} facts "
                    f"({result.processing_time:.1f}s)"
                )

    # Print failures
    if failed > 0:
        logger.info("\n❌ Failed documents:")
        for result in results:
            if not result.success:
                logger.error(f"  • {result.title}: {', '.join(result.errors)}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest PDF documents through Agentic RAG pipeline"
    )
    parser.add_argument(
        "--path",
        type=str,
        default="docs/x-examples",
        help="Path to directory containing PDF files",
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

    # Resolve path
    path = Path(args.path)
    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        sys.exit(1)

    if not path.is_dir():
        logger.error(f"Path is not a directory: {path}")
        sys.exit(1)

    # Initialize pipeline
    logger.info("🚀 Initializing Agentic RAG Ingestion Pipeline...")
    logger.info("=" * 80)

    if args.rest_api:
        logger.info("→ Using Supabase REST API (forced by --rest-api flag)")
        use_rest_api = True
    else:
        logger.info("→ Attempting direct PostgreSQL + Neo4j connections...")
        use_rest_api = False

    # Use async context manager for automatic cleanup
    try:
        async with DocumentIngestionPipeline(use_rest_api=use_rest_api) as pipeline:
            logger.info("✅ Pipeline initialized successfully")
            logger.info("=" * 80)

            # Run ingestion
            await ingest_pdf_directory(pipeline, path)

            logger.info("\n" + "=" * 80)
            logger.info("✅ INGESTION COMPLETE!")
            logger.info("=" * 80)

    except Exception as e:
        if not use_rest_api:
            # PostgreSQL failed, fallback to REST API
            logger.warning(f"⚠️  PostgreSQL initialization failed: {e}")
            logger.info("→ Falling back to Supabase REST API...")

            async with DocumentIngestionPipeline(use_rest_api=True) as pipeline:
                logger.info("✅ Pipeline initialized with REST API fallback")
                await ingest_pdf_directory(pipeline, path)
                logger.info("\n✅ Ingestion complete!")
        else:
            logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Ingestion cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Ingestion failed: {e}", exc_info=True)
        sys.exit(1)
