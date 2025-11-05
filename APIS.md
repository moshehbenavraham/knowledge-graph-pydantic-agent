# API Surface

All routes are served from the FastAPI application defined in `src/api/main.py` with versioned prefix `/api/v1` for business endpoints and `/health` for probes.【F:src/api/main.py†L91-L176】 Models referenced below are declared in `src/api/models.py` unless noted.【F:src/api/models.py†L34-L199】

## Root & Status
| Method | Path | Description | Request | Response | Auth | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/` | API metadata listing available routes.【F:src/api/main.py†L152-L173】 | – | JSON | None | Static info only. |
| GET | `/api/v1/status` | Aggregated health (Postgres/Neo4j) and configuration snapshot.【F:src/api/main.py†L176-L200】 | – | `StatusResponse` (inline) | None | Pulls component status via dependency checks.【F:src/api/main.py†L176-L200】 |

## Chat
| Method | Path | Description | Request | Response | Auth | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/chat` | Synchronous chat with unified agent; optional caching and tool sourcing.【F:src/api/endpoints/chat.py†L38-L123】 | `ChatRequest` (`message`, `session_id`, `stream`, etc.).【F:src/api/models.py†L44-L55】 | `ChatResponse` (response text, sources, metrics).【F:src/api/models.py†L79-L90】 | None | Returns cached result if available; metrics included.【F:src/api/endpoints/chat.py†L52-L115】 |
| POST | `/api/v1/chat/stream` | Server-Sent Events streaming of agent responses.【F:src/api/endpoints/chat.py†L138-L185】 | `ChatRequest` | SSE stream of JSON chunks | None | Supports `max_tokens`/`temperature` overrides.【F:src/api/endpoints/chat.py†L150-L175】 |
| WS | `/api/v1/chat/ws` | WebSocket chat; handles chat and ping messages via connection manager.【F:src/api/endpoints/chat.py†L187-L235】 | JSON messages (`type`, `message`). | Streaming JSON messages | None | Uses `websocket_manager` for streaming tool output.【F:src/api/endpoints/chat.py†L205-L225】 |
| POST | `/api/v1/chat/feedback` | Submit rating/feedback for a chat response.【F:src/api/endpoints/chat.py†L237-L267】 | `FeedbackRequest` (message id, rating, notes).【F:src/api/models.py†L200-L260】 | `FeedbackResponse` (success flag, id).【F:src/api/models.py†L261-L296】 | None | Persistence TODO; currently generates UUID and logs.【F:src/api/endpoints/chat.py†L246-L260】 |
| GET | `/api/v1/chat/sessions/{session_id}/history` | Retrieve stored session transcript (stub).【F:src/api/endpoints/chat.py†L270-L295】 | Query `limit` (default 50) | JSON placeholder | None | Returns empty list until DB integration implemented.【F:src/api/endpoints/chat.py†L281-L288】 |

## Search
| Method | Path | Description | Request | Response | Auth | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/search` | Unified search; executes vector/hybrid/adaptive strategies with caching.【F:src/api/endpoints/search.py†L48-L120】 | `SearchRequest` (query, type, limit, threshold, filters).【F:src/api/models.py†L95-L104】 | `SearchResponse` (results, strategy, entities).【F:src/api/models.py†L134-L142】 | None | Cache TTL 10 min; returns metrics counters.【F:src/api/endpoints/search.py†L63-L111】 |
| GET | `/api/v1/search/suggest` | Query autocomplete placeholder.【F:src/api/endpoints/search.py†L134-L158】 | `query`, `limit` | JSON stub | None | Currently returns empty suggestion list (TODO). |
| GET | `/api/v1/search/entities/{entity_name}` | Fetch entity profile from graph (stub).【F:src/api/endpoints/search.py†L161-L193】 | Path `entity_name` | JSON stub | None | Returns placeholder when Graphiti enabled; 501 otherwise.【F:src/api/endpoints/search.py†L171-L193】 |
| GET | `/api/v1/search/relationships` | Find relationships between two entities (stub).【F:src/api/endpoints/search.py†L196-L230】 | Query `entity1`, `entity2`, `max_depth` | JSON stub | None | Requires Graphiti; currently returns empty set.【F:src/api/endpoints/search.py†L208-L223】 |

## Documents
| Method | Path | Description | Request | Response | Auth | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/documents` | Ingest a new document through the pipeline (chunks, embeddings, knowledge).【F:src/api/endpoints/documents.py†L35-L83】 | `IngestRequest` (`content`, `title`, `source`, metadata).【F:src/api/models.py†L148-L157】 | `IngestResponse` (doc id, counts).【F:src/api/models.py†L159-L168】 | None | Pipeline instantiated per request; Graph cleanup TODO.【F:src/api/endpoints/documents.py†L56-L90】 |
| GET | `/api/v1/documents` | Paginated metadata listing.【F:src/api/endpoints/documents.py†L103-L159】 | Query `page`, `page_size`, `source_filter` | `DocumentListResponse`.【F:src/api/models.py†L182-L189】 | None | Relies on Postgres store list/count operations.【F:src/api/endpoints/documents.py†L119-L150】 |
| GET | `/api/v1/documents/{document_id}` | Retrieve full document content (optional chunks).【F:src/api/endpoints/documents.py†L161-L199】 | Query `include_chunks` | `DocumentContent`.【F:src/api/models.py†L192-L198】 | None | Returns 404 if not found.【F:src/api/endpoints/documents.py†L173-L198】 |
| DELETE | `/api/v1/documents/{document_id}` | Soft/Hard delete in Postgres and (future) graph cleanup.【F:src/api/endpoints/documents.py†L214-L258】 | – | JSON `{status, document_id}` | None | Graph cleanup TODO; currently pass-through.【F:src/api/endpoints/documents.py†L236-L243】 |
| PATCH | `/api/v1/documents/{document_id}` | Update title/metadata fields.【F:src/api/endpoints/documents.py†L261-L319】 | JSON body with optional `title`, `metadata` | JSON `{status, updates}` | None | Validates presence of updates; uses store update_document.【F:src/api/endpoints/documents.py†L282-L309】 |
| POST | `/api/v1/documents/{document_id}/reindex` | Re-run embeddings and knowledge extraction (stub).【F:src/api/endpoints/documents.py†L322-L364】 | – | JSON status | None | Steps TODO; logs start/completion only.【F:src/api/endpoints/documents.py†L344-L353】 |
| GET | `/api/v1/documents/{document_id}/stats` | Return chunk/entity counts (partial).【F:src/api/endpoints/documents.py†L366-L413】 | – | JSON stats | None | Entity/relationship counts require Graphiti implementation.【F:src/api/endpoints/documents.py†L389-L395】 |

## Analytics
| Method | Path | Description | Request | Response | Auth | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/analytics/search-metrics` | Aggregated search latency & strategy metrics.【F:src/api/endpoints/analytics.py†L25-L62】 | Query `window` | JSON metrics | None | Delegates to `DashboardHandler` against analytics tables.【F:src/api/endpoints/analytics.py†L48-L62】 |
| GET | `/api/v1/analytics/intent-distribution` | Query intent percentages.【F:src/api/endpoints/analytics.py†L65-L98】 | Query `window` | JSON dict | None | Requires analytics tables populated.【F:src/api/endpoints/analytics.py†L88-L95】 |
| GET | `/api/v1/analytics/performance-metrics` | Latency percentiles and cache stats.【F:src/api/endpoints/analytics.py†L100-L138】 | Query `window` | JSON metrics | None | Logs partial failures when data missing.【F:src/api/endpoints/analytics.py†L123-L135】 |
| GET | `/api/v1/analytics/time-series` | Time-series data for selected metric.【F:src/api/endpoints/analytics.py†L140-L178】 | Query `window`, `metric` | JSON array | None | Validates metric name via regex.【F:src/api/endpoints/analytics.py†L146-L176】 |
| GET | `/api/v1/analytics/tool-usage` | Tool execution counts & success rates.【F:src/api/endpoints/analytics.py†L181-L218】 | Query `window` | JSON metrics | None | Returns warnings when partial data.【F:src/api/endpoints/analytics.py†L205-L218】 |
| GET | `/api/v1/analytics/agent-interactions` | Agent feedback/interaction stats.【F:src/api/endpoints/analytics.py†L221-L258】 | Query `window` | JSON metrics | None | Logs partial failures on missing tables.【F:src/api/endpoints/analytics.py†L244-L258】 |
| GET | `/api/v1/analytics/health` | Analytics subsystem health check.【F:src/api/endpoints/analytics.py†L261-L318】 | – | JSON status | None | Verifies DB connectivity and required tables.【F:src/api/endpoints/analytics.py†L283-L308】 |

## Health & Telemetry
| Method | Path | Description | Notes |
| --- | --- | --- | --- |
| GET | `/health/` | Basic health payload (status, version).【F:src/api/health_endpoints.py†L16-L25】 | Uses settings for version info. |
| GET | `/health/detailed` | Component-by-component health summary.【F:src/api/health_endpoints.py†L28-L60】 | Returns `degraded`/`unhealthy` HTTP 503 when needed. |
| GET | `/health/metrics` | System stats + Prometheus endpoint pointer.【F:src/api/health_endpoints.py†L63-L77】 | Wraps `monitor.get_system_stats()`. |
| GET | `/health/rate-limits/{user_id}` | Retrieve rate limit counters.【F:src/api/health_endpoints.py†L80-L90】 | Reads from shared rate limiter. |
| POST | `/health/rate-limits/{user_id}/tier` | Set user tier for throttling.【F:src/api/health_endpoints.py†L93-L104】 | Validates tier pattern. |
| GET | `/health/components/{component}` | Targeted component health (db, llm, etc.).【F:src/api/health_endpoints.py†L106-L147】 | Returns 503 for unhealthy components. |
| GET | `/health/readiness` | Kubernetes readiness probe.【F:src/api/health_endpoints.py†L150-L176】 | Ensures DB/LLM healthy before returning ready. |
| GET | `/health/liveness` | Kubernetes liveness probe.【F:src/api/health_endpoints.py†L179-L193】 | Uses monitor uptime. |
| GET | `/health/startup` | Startup probe verifying services initialized.【F:src/api/health_endpoints.py†L195-L220】 | Wraps health checker aggregate. |

## Streaming Helpers
- `/metrics`: Prometheus scrape endpoint exposed via `/metrics` handled in `main.py` using `prometheus_client.generate_latest`.【F:src/api/main.py†L11-L147】
- SSE/WebSocket utilities live in `src/api/streaming.py` and `src/api/endpoints/chat.py` for streaming interactions.【F:src/api/endpoints/chat.py†L138-L235】【F:src/api/streaming.py†L1-L120】

## Authentication & Rate Limiting
No authentication middleware is enforced yet; rate limiting is handled via middleware and `/health/rate-limits` endpoints but not tied to auth tokens.【F:src/api/main.py†L105-L135】【F:src/api/health_endpoints.py†L80-L104】 Future enterprise deployments should integrate OAuth/OIDC via the existing config scaffolding.
