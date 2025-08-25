"""
Configuration for the agent intelligence layer.
"""

import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from functools import lru_cache
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for the Pydantic AI agent."""
    
    # LLM Settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    llm_timeout: int = 30
    
    # Agent Behavior
    max_tools_per_query: int = 5
    enable_streaming: bool = True
    enable_caching: bool = True
    confidence_threshold: float = 0.7
    
    # Search Settings
    default_search_limit: int = 10
    max_search_results: int = 50
    parallel_search_timeout: int = 5
    
    # Intent Analysis
    intent_cache_ttl: int = 300  # 5 minutes
    entity_extraction_model: Optional[str] = None  # Use default if None
    
    # Response Generation
    max_citations: int = 10
    include_confidence: bool = True
    generate_follow_ups: bool = True
    
    # Performance
    enable_query_cache: bool = True
    query_cache_ttl: int = 900  # 15 minutes
    embedding_cache_ttl: int = 3600  # 1 hour
    
    # Monitoring
    enable_metrics: bool = True
    log_level: str = "INFO"
    
    # Feature Flags
    enable_graph_search: bool = True
    enable_vector_search: bool = True
    enable_iterative_search: bool = True
    enable_entity_extraction: bool = True
    enable_temporal_analysis: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AgentConfig':
        """Create from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # LLM Settings
        config.llm_provider = os.getenv("LLM_PROVIDER", config.llm_provider)
        config.llm_model = os.getenv("LLM_MODEL", config.llm_model)
        config.llm_temperature = float(os.getenv("LLM_TEMPERATURE", str(config.llm_temperature)))
        config.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", str(config.llm_max_tokens)))
        config.llm_timeout = int(os.getenv("LLM_TIMEOUT", str(config.llm_timeout)))
        
        # Agent Behavior
        config.max_tools_per_query = int(os.getenv("MAX_TOOLS_PER_QUERY", str(config.max_tools_per_query)))
        config.enable_streaming = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
        config.enable_caching = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        config.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", str(config.confidence_threshold)))
        
        # Search Settings
        config.default_search_limit = int(os.getenv("DEFAULT_SEARCH_LIMIT", str(config.default_search_limit)))
        config.max_search_results = int(os.getenv("MAX_SEARCH_RESULTS", str(config.max_search_results)))
        config.parallel_search_timeout = int(os.getenv("PARALLEL_SEARCH_TIMEOUT", str(config.parallel_search_timeout)))
        
        # Feature Flags
        config.enable_graph_search = os.getenv("ENABLE_GRAPH_SEARCH", "true").lower() == "true"
        config.enable_vector_search = os.getenv("ENABLE_VECTOR_SEARCH", "true").lower() == "true"
        config.enable_iterative_search = os.getenv("ENABLE_ITERATIVE_SEARCH", "true").lower() == "true"
        config.enable_entity_extraction = os.getenv("ENABLE_ENTITY_EXTRACTION", "true").lower() == "true"
        config.enable_temporal_analysis = os.getenv("ENABLE_TEMPORAL_ANALYSIS", "true").lower() == "true"
        
        # Monitoring
        config.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        config.log_level = os.getenv("LOG_LEVEL", config.log_level)
        
        return config
    
    @classmethod
    def from_file(cls, file_path: str) -> 'AgentConfig':
        """Load configuration from JSON file."""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)
    
    def save(self, file_path: str):
        """Save configuration to JSON file."""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        errors = []
        
        # Validate temperature
        if not 0 <= self.llm_temperature <= 2:
            errors.append("LLM temperature must be between 0 and 2")
        
        # Validate confidence threshold
        if not 0 <= self.confidence_threshold <= 1:
            errors.append("Confidence threshold must be between 0 and 1")
        
        # Validate search limits
        if self.default_search_limit > self.max_search_results:
            errors.append("Default search limit cannot exceed max search results")
        
        # Validate timeouts
        if self.parallel_search_timeout <= 0:
            errors.append("Parallel search timeout must be positive")
        
        # Validate cache TTLs
        if self.query_cache_ttl < 0 or self.embedding_cache_ttl < 0:
            errors.append("Cache TTLs must be non-negative")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration validation error: {error}")
            return False
        
        return True


@dataclass
class SearchConfig:
    """Configuration for search operations."""
    
    use_vector: bool = True
    use_graph: bool = True
    vector_limit: int = 15
    graph_limit: int = 15
    vector_weight: float = 0.6
    confidence_threshold: float = 0.7
    include_timeline: bool = False
    max_facts: int = 20
    rerank_results: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CacheConfig:
    """Configuration for caching."""
    
    enable_embedding_cache: bool = True
    enable_query_cache: bool = True
    enable_result_cache: bool = True
    
    embedding_cache_size: int = 1000
    query_cache_size: int = 500
    result_cache_size: int = 100
    
    embedding_cache_ttl: int = 3600  # 1 hour
    query_cache_ttl: int = 900  # 15 minutes
    result_cache_ttl: int = 300  # 5 minutes
    
    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0


@dataclass
class MetricsConfig:
    """Configuration for metrics and monitoring."""
    
    enable_metrics: bool = True
    enable_tracing: bool = False
    enable_profiling: bool = False
    
    metrics_port: int = 9090
    metrics_path: str = "/metrics"
    
    trace_sample_rate: float = 0.1
    profile_sample_rate: float = 0.01
    
    log_slow_queries: bool = True
    slow_query_threshold_ms: int = 1000


# Global configuration instance
@lru_cache(maxsize=1)
def get_agent_config() -> AgentConfig:
    """Get the global agent configuration."""
    # Try to load from file first
    config_file = os.getenv("AGENT_CONFIG_FILE")
    if config_file and os.path.exists(config_file):
        logger.info(f"Loading agent config from file: {config_file}")
        config = AgentConfig.from_file(config_file)
    else:
        # Load from environment variables
        logger.info("Loading agent config from environment variables")
        config = AgentConfig.from_env()
    
    # Validate configuration
    if not config.validate():
        logger.warning("Configuration validation failed, using defaults")
        config = AgentConfig()
    
    return config


# Convenience function to get specific config sections
def get_search_config() -> SearchConfig:
    """Get search-specific configuration."""
    agent_config = get_agent_config()
    return SearchConfig(
        use_vector=agent_config.enable_vector_search,
        use_graph=agent_config.enable_graph_search,
        confidence_threshold=agent_config.confidence_threshold
    )


def get_cache_config() -> CacheConfig:
    """Get cache-specific configuration."""
    agent_config = get_agent_config()
    return CacheConfig(
        enable_embedding_cache=agent_config.enable_caching,
        enable_query_cache=agent_config.enable_query_cache,
        embedding_cache_ttl=agent_config.embedding_cache_ttl,
        query_cache_ttl=agent_config.query_cache_ttl
    )


def get_metrics_config() -> MetricsConfig:
    """Get metrics-specific configuration."""
    agent_config = get_agent_config()
    return MetricsConfig(
        enable_metrics=agent_config.enable_metrics
    )


# Configuration presets for different use cases
PRESETS = {
    "development": {
        "llm_model": "gpt-4o-mini",
        "llm_temperature": 0.7,
        "enable_caching": False,
        "enable_metrics": True,
        "log_level": "DEBUG",
        "default_search_limit": 5
    },
    "production": {
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "enable_caching": True,
        "enable_metrics": True,
        "log_level": "INFO",
        "default_search_limit": 10
    },
    "testing": {
        "llm_model": "gpt-4o-mini",
        "llm_temperature": 0.0,
        "enable_caching": False,
        "enable_metrics": False,
        "log_level": "WARNING",
        "default_search_limit": 3
    },
    "high_performance": {
        "llm_model": "gpt-4o",
        "llm_temperature": 0.2,
        "enable_caching": True,
        "enable_streaming": True,
        "parallel_search_timeout": 2,
        "max_tools_per_query": 3
    },
    "cost_optimized": {
        "llm_model": "gpt-4o-mini",
        "llm_temperature": 0.5,
        "llm_max_tokens": 1000,
        "enable_caching": True,
        "default_search_limit": 5,
        "max_citations": 5
    }
}


def load_preset(preset_name: str) -> AgentConfig:
    """Load a configuration preset."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    
    config = AgentConfig()
    preset = PRESETS[preset_name]
    
    for key, value in preset.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    logger.info(f"Loaded configuration preset: {preset_name}")
    return config