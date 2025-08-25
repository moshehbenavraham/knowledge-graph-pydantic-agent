"""
Agent Intelligence Layer for Agentic RAG System.

This module provides intelligent query understanding, search orchestration,
and response generation capabilities.
"""

from .intent_analyzer import (
    IntentAnalyzer,
    QueryIntent,
    SearchStrategy,
    AnalyzedQuery
)

from .agent import (
    rag_agent,
    AgentDependencies,
    run_query,
    smart_search,
    vector_search,
    graph_search,
    get_entity_relationships,
    get_entity_timeline,
    comprehensive_search,
    generate_response
)

from .response_generator import (
    ResponseGenerator,
    Citation,
    GeneratedResponse
)

from .router import (
    QueryRouter,
    AdaptiveRouter,
    RoutingDecision
)

from .config import (
    AgentConfig,
    SearchConfig,
    CacheConfig,
    MetricsConfig,
    get_agent_config,
    get_search_config,
    get_cache_config,
    get_metrics_config,
    load_preset,
    PRESETS
)

from .providers import (
    get_llm_model,
    get_embedding_model,
    get_model_capabilities,
    MODEL_CAPABILITIES
)

from .prompts import (
    SYSTEM_PROMPT,
    TOOL_SELECTION_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    CITATION_FORMAT_PROMPT,
    ERROR_HANDLING_PROMPT,
    ENTITY_EXTRACTION_PROMPT,
    FACT_EXTRACTION_PROMPT,
    QUERY_EXPANSION_PROMPT,
    ANSWER_SYNTHESIS_PROMPT,
    FOLLOW_UP_GENERATION_PROMPT
)

from .tools import (
    comprehensive_search,
    get_document_context,
    explore_entity_network,
    temporal_analysis,
    extract_key_facts,
    search_with_reranking,
    validate_facts,
    tool_registry,
    VectorSearchInput,
    GraphSearchInput,
    HybridSearchInput,
    DocumentInput,
    EntityRelationshipInput
)

__version__ = "0.1.0"

__all__ = [
    # Intent Analyzer
    "IntentAnalyzer",
    "QueryIntent",
    "SearchStrategy",
    "AnalyzedQuery",
    
    # Agent
    "rag_agent",
    "AgentDependencies",
    "run_query",
    "smart_search",
    "vector_search",
    "graph_search",
    "get_entity_relationships",
    "get_entity_timeline",
    "comprehensive_search",
    "generate_response",
    
    # Response Generator
    "ResponseGenerator",
    "Citation",
    "GeneratedResponse",
    
    # Router
    "QueryRouter",
    "AdaptiveRouter",
    "RoutingDecision",
    
    # Configuration
    "AgentConfig",
    "SearchConfig",
    "CacheConfig",
    "MetricsConfig",
    "get_agent_config",
    "get_search_config",
    "get_cache_config",
    "get_metrics_config",
    "load_preset",
    "PRESETS",
    
    # Providers
    "get_llm_model",
    "get_embedding_model",
    "get_model_capabilities",
    "MODEL_CAPABILITIES",
    
    # Tools
    "tool_registry",
    "VectorSearchInput",
    "GraphSearchInput",
    "HybridSearchInput",
    "DocumentInput",
    "EntityRelationshipInput",
    
    # Version
    "__version__"
]