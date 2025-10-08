# Architecture Diagrams

This document contains visual representations of the Agentic RAG system architecture using Mermaid diagrams.

## System Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Streamlit UI]
        CLI[CLI Interface]
        API_Client[API Clients]
    end

    subgraph "API Layer"
        FastAPI[FastAPI Server]
        Auth[Authentication]
        RateLimiter[Rate Limiter]
    end

    subgraph "Agent Layer"
        Agent[Pydantic AI Agent]
        Intent[Intent Analyzer]
        Router[Query Router]
        Tools[Tool System]
    end

    subgraph "Storage Layer"
        PG[(PostgreSQL/Supabase)]
        Neo4j[(Neo4j Graph)]
        Redis[(Redis Cache)]
        Mem0[(Memory Store)]
    end

    subgraph "Search Strategies"
        Vector[Vector Search]
        Graph[Graph Search]
        Hybrid[Hybrid Search]
    end

    UI --> FastAPI
    CLI --> FastAPI
    API_Client --> FastAPI
    FastAPI --> Auth
    FastAPI --> RateLimiter
    FastAPI --> Agent
    Agent --> Intent
    Agent --> Router
    Agent --> Tools
    Router --> Vector
    Router --> Graph
    Router --> Hybrid
    Vector --> PG
    Graph --> Neo4j
    Hybrid --> PG
    Hybrid --> Neo4j
    Agent --> Redis
    Agent --> Mem0
```

## RAG Pipeline Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Agent
    participant IntentAnalyzer
    participant Router
    participant Search
    participant Storage
    participant ResponseGen

    User->>API: Send Query
    API->>Agent: Process Request
    Agent->>IntentAnalyzer: Analyze Intent
    IntentAnalyzer-->>Agent: Intent Type
    Agent->>Router: Route Query
    Router->>Search: Execute Search Strategy
    Search->>Storage: Retrieve Data
    Storage-->>Search: Return Results
    Search-->>Router: Search Results
    Router-->>Agent: Processed Results
    Agent->>ResponseGen: Generate Response
    ResponseGen-->>Agent: Formatted Response
    Agent-->>API: Response with Sources
    API-->>User: Final Answer
```

## Ingestion Pipeline

```mermaid
flowchart LR
    subgraph "Input"
        Docs[Documents]
        PDFs[PDFs]
        Text[Text Files]
    end

    subgraph "Processing"
        Load[Document Loader]
        Chunk[Semantic Chunker]
        Embed[Embedder]
        Extract[Knowledge Extractor]
    end

    subgraph "Storage"
        PG_Store[PostgreSQL Storage]
        Neo4j_Store[Neo4j Storage]
        Cache_Store[Redis Cache]
    end

    Docs --> Load
    PDFs --> Load
    Text --> Load
    Load --> Chunk
    Chunk --> Embed
    Chunk --> Extract
    Embed --> PG_Store
    Extract --> Neo4j_Store
    Embed --> Cache_Store
```

## Search Strategy Decision Tree

```mermaid
graph TD
    Query[User Query]
    Analyze[Analyze Query Intent]

    Analyze --> IsEntity{Entity-focused?}
    IsEntity -->|Yes| GraphSearch[Graph Search]
    IsEntity -->|No| IsConcept{Concept/Topic?}

    IsConcept -->|Yes| VectorSearch[Vector Search]
    IsConcept -->|No| IsComplex{Complex Query?}

    IsComplex -->|Yes| HybridSearch[Hybrid Search]
    IsComplex -->|No| SmartSearch[Smart Search]

    GraphSearch --> Neo4j[(Neo4j)]
    VectorSearch --> PG[(PostgreSQL)]
    HybridSearch --> Both[Both DBs]
    SmartSearch --> Auto[Auto-Select]
```

## Tool Integration Architecture

```mermaid
graph LR
    subgraph "Core Agent"
        Agent[Agent Core]
        ToolManager[Tool Manager]
    end

    subgraph "Search Tools"
        VectorTool[Vector Search]
        GraphTool[Graph Search]
        HybridTool[Hybrid Search]
        SmartTool[Smart Search]
    end

    subgraph "External Tools"
        WebSearch[Web Search]
        CodeExec[Code Execution]
        ImageAnalysis[Image Analysis]
        SQLQuery[SQL Query]
    end

    subgraph "Utility Tools"
        Memory[Memory Tool]
        Cache[Cache Tool]
        Logger[Logging Tool]
    end

    Agent --> ToolManager
    ToolManager --> VectorTool
    ToolManager --> GraphTool
    ToolManager --> HybridTool
    ToolManager --> SmartTool
    ToolManager --> WebSearch
    ToolManager --> CodeExec
    ToolManager --> ImageAnalysis
    ToolManager --> SQLQuery
    ToolManager --> Memory
    ToolManager --> Cache
    ToolManager --> Logger
```

## Monitoring Stack

```mermaid
graph TB
    subgraph "Application"
        App[FastAPI App]
        Metrics[Metrics Endpoint]
        Traces[OpenTelemetry]
    end

    subgraph "Collection"
        Prometheus[Prometheus]
        Jaeger[Jaeger]
        NodeExporter[Node Exporter]
        RedisExporter[Redis Exporter]
    end

    subgraph "Visualization"
        Grafana[Grafana]
        JaegerUI[Jaeger UI]
        RedisCommander[Redis Commander]
    end

    App --> Metrics
    App --> Traces
    Metrics --> Prometheus
    Traces --> Jaeger
    NodeExporter --> Prometheus
    RedisExporter --> Prometheus
    Prometheus --> Grafana
    Jaeger --> JaegerUI
```

## Database Schema Relationships

```mermaid
erDiagram
    DOCUMENTS ||--o{ CHUNKS : contains
    DOCUMENTS ||--o{ METADATA : has
    CHUNKS ||--o{ EMBEDDINGS : has
    CHUNKS ||--o{ ENTITIES : extracted_from
    ENTITIES ||--o{ RELATIONSHIPS : participates_in
    ENTITIES ||--o{ FACTS : related_to
    SESSIONS ||--o{ MESSAGES : contains
    SESSIONS ||--o{ MEMORY : stores

    DOCUMENTS {
        uuid id PK
        string title
        string source
        timestamp created_at
        jsonb metadata
    }

    CHUNKS {
        uuid id PK
        uuid document_id FK
        text content
        int chunk_index
        vector embedding
        jsonb metadata
    }

    ENTITIES {
        uuid id PK
        string name
        string type
        jsonb properties
        uuid chunk_id FK
    }

    RELATIONSHIPS {
        uuid id PK
        uuid source_entity FK
        uuid target_entity FK
        string relationship_type
        jsonb properties
    }
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/HAProxy]
    end

    subgraph "Application Tier"
        App1[App Instance 1]
        App2[App Instance 2]
        App3[App Instance 3]
    end

    subgraph "Cache Tier"
        Redis1[Redis Primary]
        Redis2[Redis Replica]
    end

    subgraph "Database Tier"
        PG_Primary[(PostgreSQL Primary)]
        PG_Replica[(PostgreSQL Replica)]
        Neo4j_Cluster[(Neo4j Cluster)]
    end

    subgraph "Monitoring"
        Monitor[Monitoring Stack]
    end

    LB --> App1
    LB --> App2
    LB --> App3
    App1 --> Redis1
    App2 --> Redis1
    App3 --> Redis1
    Redis1 --> Redis2
    App1 --> PG_Primary
    App2 --> PG_Primary
    App3 --> PG_Primary
    PG_Primary --> PG_Replica
    App1 --> Neo4j_Cluster
    App2 --> Neo4j_Cluster
    App3 --> Neo4j_Cluster
    App1 --> Monitor
    App2 --> Monitor
    App3 --> Monitor
```

## Performance Optimization Flow

```mermaid
flowchart TD
    Request[Incoming Request]
    CacheCheck{Cache Hit?}

    Request --> CacheCheck
    CacheCheck -->|Yes| ReturnCached[Return Cached Result]
    CacheCheck -->|No| ProcessRequest[Process Request]

    ProcessRequest --> Parallel{Can Parallelize?}
    Parallel -->|Yes| ParallelExec[Parallel Execution]
    Parallel -->|No| SequentialExec[Sequential Execution]

    ParallelExec --> Aggregate[Aggregate Results]
    SequentialExec --> Aggregate

    Aggregate --> CacheResult[Cache Result]
    CacheResult --> ReturnResult[Return Result]
    ReturnCached --> End[End]
    ReturnResult --> End
```

These diagrams provide a comprehensive visual overview of the Agentic RAG system architecture, data flows, and component interactions.
