# Benchmark Plan

## Goals
Validate retrieval and answer quality across graph, SQL/vector, and hybrid scenarios using repeatable datasets.

## Test Dataset
1. **Synthetic knowledge base** – Generate ~100 documents mixing factual narratives and tabular data, embedding both graph-friendly entities and numerical summaries. Use ingestion pipeline CLI to load dataset.
   ```bash
   python scripts/generate_benchmark_corpus.py --docs 100 --entities 50 --output data/benchmark
   make run-rag SOURCE=local
   ```
   *(Add script; pipeline already supports local directory ingestion.)*【F:src/rag_pipeline/pipeline.py†L13-L55】
2. **Graph seeding** – After ingestion, run Neo4j initializer and verify Graphiti sync queue processed (see `RUNBOOK.md`).【F:src/agentic_rag/storage/migrations/neo4j_init.py†L17-L170】

## Benchmark Queries
- **Graph Topology (4)**
  1. “List partnerships between Company A and Company B in the last year.”
  2. “Who are the investors connected to Startup X within two hops?”
  3. “Timeline of events involving Entity Y and Entity Z.”
  4. “What facts link Person Q to Organization R?”

- **SQL/Vector (3)**
  5. “Summarize quarterly revenue trends for Product M.”
  6. “What documents mention ‘compliance audit’ with similarity ≥0.75?”
  7. “Average response time recorded in analytics metrics for hybrid searches.”

- **Hybrid (3)**
  8. “Explain how Company A collaborates with Vendor B, including supporting documents.”
  9. “How did Technology T adoption affect revenue in Region Z?”
 10. “Provide key entities and facts about Project Phoenix.”

## Metrics
- **Latency**: P50/P95 per query class (graph, vector, hybrid) using API timers or manual measurement.
- **Recall@k**: Compare returned chunks/entities against ground truth metadata embedded in generated corpus.
- **Groundedness**: Validate ChatResponse sources include supporting chunk ids (manually or via script).
- **Token Cost**: Extract from `ChatResponse.metrics.tokens_*`.【F:src/api/models.py†L68-L90】【F:src/api/endpoints/chat.py†L38-L123】
- **Throughput**: Measure QPS at 1/5/10 concurrent requests using Locust or k6 (Locust file already present).【F:Makefile†L174-L193】

## Execution Commands
1. **API Smoke Loop**
   ```bash
   python scripts/run_benchmark_queries.py --input benchmarks/queries.yaml --base-url http://localhost:8000
   ```
   Script should post to `/api/v1/search` or `/api/v1/chat` depending on query type, logging latency and response metadata.【F:src/api/endpoints/search.py†L48-L120】【F:src/api/endpoints/chat.py†L38-L123】
2. **Load testing**
   ```bash
   locust -f tests/load/locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 5 --run-time 10m
   ```
   Locust scenarios already defined for chat/search flows.【F:Makefile†L174-L193】
3. **Result Evaluation** – Extend evaluation script to compute recall/precision by comparing returned chunk_ids to known ground truth stored in corpus metadata (`metadata` field saved during ingestion).【F:src/agentic_rag/storage/postgres_store.py†L25-L102】

## Reporting
- Produce CSV/JSON summary including average latency, P95, recall@5, number of grounded citations per query class.
- Store artifacts under `benchmarks/results/` and publish in CI for regression tracking.
