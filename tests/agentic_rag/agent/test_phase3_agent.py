"""
Comprehensive tests for Phase 3 Agent Intelligence.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import time

from src.agentic_rag.agent.intent_analyzer import (
    IntentAnalyzer, QueryIntent, SearchStrategy, AnalyzedQuery
)
from src.agentic_rag.agent.agent import rag_agent, AgentDependencies, run_query
from src.agentic_rag.agent.response_generator import (
    ResponseGenerator, Citation, GeneratedResponse
)
from src.agentic_rag.agent.router import QueryRouter, RoutingDecision, AdaptiveRouter
from src.agentic_rag.agent.config import AgentConfig, get_agent_config, load_preset
from src.agentic_rag.agent.providers import get_llm_model, get_model_capabilities


class TestIntentAnalyzer:
    """Test intent analysis functionality."""

    @pytest.mark.asyncio
    async def test_factual_query_classification(self):
        """Test classification of factual queries."""
        analyzer = IntentAnalyzer()
        
        queries = [
            "What is OpenAI?",
            "Who founded Microsoft?",
            "How many employees does Google have?"
        ]
        
        for query in queries:
            result = await analyzer.analyze(query)
            assert result.primary_intent == QueryIntent.FACTUAL
            assert result.search_strategy in [
                SearchStrategy.VECTOR_ONLY,
                SearchStrategy.VECTOR_FIRST
            ]

    @pytest.mark.asyncio
    async def test_relationship_query_classification(self):
        """Test classification of relationship queries."""
        analyzer = IntentAnalyzer()
        
        queries = [
            "How is Microsoft related to OpenAI?",
            "What companies has Google acquired?",
            "Who are Apple's main competitors?"
        ]
        
        for query in queries:
            result = await analyzer.analyze(query)
            assert result.primary_intent == QueryIntent.RELATIONSHIP
            assert result.search_strategy in [
                SearchStrategy.GRAPH_FIRST,
                SearchStrategy.HYBRID
            ]

    @pytest.mark.asyncio
    async def test_temporal_query_classification(self):
        """Test classification of temporal queries."""
        analyzer = IntentAnalyzer()
        
        query = "Show me the timeline of AI developments in 2023"
        result = await analyzer.analyze(query)
        
        assert result.primary_intent == QueryIntent.TEMPORAL
        assert result.temporal_context is not None
        assert result.search_strategy == SearchStrategy.GRAPH_FIRST

    @pytest.mark.asyncio
    async def test_entity_extraction(self):
        """Test entity extraction from queries."""
        analyzer = IntentAnalyzer()
        
        query = "Compare Google and Microsoft's AI strategies"
        result = await analyzer.analyze(query)
        
        # Check for entities (case-insensitive)
        entities_lower = [e.lower() for e in result.entities]
        assert "google" in entities_lower or "Google" in result.entities
        assert "microsoft" in entities_lower or "Microsoft" in result.entities

    @pytest.mark.asyncio
    async def test_complexity_scoring(self):
        """Test query complexity scoring."""
        analyzer = IntentAnalyzer()
        
        simple_query = "What is AI?"
        complex_query = ("Analyze the competitive dynamics between major tech companies "
                        "in the AI space, considering their investments, partnerships, "
                        "and technical capabilities")
        
        simple_result = await analyzer.analyze(simple_query)
        complex_result = await analyzer.analyze(complex_query)
        
        assert simple_result.complexity_score < 0.5
        assert complex_result.complexity_score > 0.7

    @pytest.mark.asyncio
    async def test_secondary_intents(self):
        """Test detection of secondary intents."""
        analyzer = IntentAnalyzer()
        
        query = "What is the relationship between OpenAI and Microsoft, and how has it changed over time?"
        result = await analyzer.analyze(query)
        
        assert QueryIntent.RELATIONSHIP in [result.primary_intent] + result.secondary_intents
        assert QueryIntent.TEMPORAL in result.secondary_intents

    @pytest.mark.asyncio
    async def test_confidence_calculation(self):
        """Test confidence calculation for analysis."""
        analyzer = IntentAnalyzer()
        
        clear_query = "What is machine learning?"
        vague_query = "Tell me about that thing with computers"
        
        clear_result = await analyzer.analyze(clear_query)
        vague_result = await analyzer.analyze(vague_query)
        
        assert clear_result.confidence > vague_result.confidence


class TestQueryRouter:
    """Test query routing functionality."""

    def test_routing_decisions(self):
        """Test routing decisions for different intents."""
        router = QueryRouter()
        
        # Mock analyzed queries
        factual_query = Mock(
            primary_intent=QueryIntent.FACTUAL,
            entities=[],
            temporal_context=None,
            confidence=0.9,
            complexity_score=0.3
        )
        
        relationship_query = Mock(
            primary_intent=QueryIntent.RELATIONSHIP,
            entities=["Microsoft", "OpenAI"],
            temporal_context=None,
            confidence=0.85,
            complexity_score=0.5
        )
        
        # Test factual routing
        factual_decision = router.route(factual_query)
        assert factual_decision.primary_strategy == SearchStrategy.VECTOR_FIRST
        assert len(factual_decision.fallback_strategies) > 0
        
        # Test relationship routing
        relationship_decision = router.route(relationship_query)
        assert relationship_decision.primary_strategy == SearchStrategy.GRAPH_FIRST
        assert "graph_search" in relationship_decision.recommended_tools

    def test_fallback_strategies(self):
        """Test fallback strategy selection."""
        router = QueryRouter()
        
        # Test each primary strategy has fallbacks
        for intent in QueryIntent:
            mock_query = Mock(
                primary_intent=intent,
                entities=[],
                temporal_context=None,
                confidence=0.5,
                complexity_score=0.5
            )
            
            decision = router.route(mock_query)
            assert len(decision.fallback_strategies) > 0

    def test_entity_based_adjustment(self):
        """Test strategy adjustment based on entities."""
        router = QueryRouter()
        
        # Query with multiple entities
        multi_entity_query = Mock(
            primary_intent=QueryIntent.FACTUAL,
            entities=["Google", "Microsoft", "Apple"],
            temporal_context=None,
            confidence=0.8,
            complexity_score=0.4
        )
        
        decision = router.route(multi_entity_query)
        # Should upgrade from VECTOR_FIRST to HYBRID due to multiple entities
        assert decision.primary_strategy in [SearchStrategy.HYBRID, SearchStrategy.GRAPH_FIRST]

    def test_search_params_generation(self):
        """Test generation of search parameters."""
        router = QueryRouter()
        
        mock_query = Mock(
            primary_intent=QueryIntent.FACTUAL,
            entities=[],
            temporal_context=None,
            confidence=0.8,
            complexity_score=0.3
        )
        
        params = router.get_search_params(mock_query)
        assert "limit" in params
        assert "confidence_threshold" in params
        assert params["limit"] > 0

    def test_adaptive_router(self):
        """Test adaptive router with learning."""
        router = AdaptiveRouter()
        
        # Record some outcomes
        router.record_outcome(QueryIntent.FACTUAL, SearchStrategy.VECTOR_ONLY, True, 0.9)
        router.record_outcome(QueryIntent.FACTUAL, SearchStrategy.VECTOR_ONLY, True, 0.85)
        router.record_outcome(QueryIntent.FACTUAL, SearchStrategy.HYBRID, False, 0.3)
        
        # Get best strategy
        best = router.get_best_strategy_for_intent(QueryIntent.FACTUAL, min_samples=2)
        assert best == SearchStrategy.VECTOR_ONLY


class TestResponseGenerator:
    """Test response generation functionality."""

    @pytest.mark.asyncio
    async def test_citation_generation(self):
        """Test citation generation from search results."""
        generator = ResponseGenerator()
        
        search_results = {
            "vector_results": [
                {
                    "content": "Test content 1",
                    "score": 0.9,
                    "document_title": "Doc 1",
                    "document_id": "doc1",
                    "chunk_id": "chunk1"
                }
            ],
            "graph_results": {
                "facts": [
                    {
                        "fact": "Test fact 1",
                        "confidence": 0.85,
                        "source_chunk": "chunk2"
                    }
                ]
            }
        }
        
        content = generator._extract_relevant_content(search_results)
        citations = generator._generate_citations(content)
        
        assert len(citations) > 0
        assert citations[0].document_title == "Doc 1"
        assert citations[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_confidence_calculation(self):
        """Test confidence calculation for responses."""
        generator = ResponseGenerator()
        
        # High confidence scenario
        high_conf_content = [
            {"content": "High relevance", "score": 0.95, "source_type": "vector"},
            {"content": "Supporting fact", "score": 0.9, "source_type": "graph"}
        ]
        
        mock_query = Mock(complexity_score=0.3)
        
        confidence = generator._calculate_confidence(high_conf_content, mock_query)
        assert confidence > 0.8
        
        # Low confidence scenario
        low_conf_content = [
            {"content": "Low relevance", "score": 0.5, "source_type": "vector"}
        ]
        
        mock_complex_query = Mock(complexity_score=0.9)
        
        confidence = generator._calculate_confidence(low_conf_content, mock_complex_query)
        assert confidence < 0.6

    @pytest.mark.asyncio
    async def test_result_merging(self):
        """Test merging results from multiple sources."""
        generator = ResponseGenerator()
        
        vector_results = {
            "results": [
                {"content": "Vector result", "score": 0.8}
            ]
        }
        
        graph_results = {
            "facts": [
                {"fact": "Graph fact", "confidence": 0.9}
            ]
        }
        
        mock_query = Mock()
        
        merged = await generator.merge_results(
            vector_results,
            graph_results,
            mock_query
        )
        
        assert merged["type"] == "hybrid"
        assert len(merged["merged_results"]) == 2
        # Graph result should be ranked higher due to confidence
        assert "Graph fact" in str(merged["merged_results"])

    @pytest.mark.asyncio
    async def test_follow_up_generation(self):
        """Test follow-up question generation."""
        generator = ResponseGenerator()
        
        content_pieces = [
            {
                "content": "OpenAI develops GPT models",
                "score": 0.9,
                "entities": ["OpenAI", "GPT"]
            }
        ]
        
        follow_ups = generator._generate_follow_ups("What is OpenAI?", content_pieces)
        
        assert len(follow_ups) > 0
        assert any("OpenAI" in q for q in follow_ups)

    @pytest.mark.asyncio
    async def test_response_generation_end_to_end(self):
        """Test complete response generation pipeline."""
        generator = ResponseGenerator()
        
        search_results = {
            "search_type": "hybrid",
            "vector_results": [
                {
                    "content": "AI is artificial intelligence",
                    "score": 0.9,
                    "document_title": "AI Basics",
                    "document_id": "doc1",
                    "chunk_id": "chunk1"
                }
            ]
        }
        
        mock_query = Mock(
            complexity_score=0.3,
            primary_intent=QueryIntent.FACTUAL
        )
        
        response = await generator.generate_response(
            "What is AI?",
            search_results,
            mock_query
        )
        
        assert isinstance(response, GeneratedResponse)
        assert response.answer
        assert len(response.citations) > 0
        assert response.confidence > 0
        assert response.search_strategy_used == "hybrid"


class TestAgentConfiguration:
    """Test agent configuration functionality."""

    def test_config_from_env(self):
        """Test loading configuration from environment variables."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4",
            "LLM_TEMPERATURE": "0.5",
            "ENABLE_CACHING": "true"
        }):
            config = AgentConfig.from_env()
            assert config.llm_provider == "openai"
            assert config.llm_model == "gpt-4"
            assert config.llm_temperature == 0.5
            assert config.enable_caching is True

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = AgentConfig()
        assert config.validate() is True
        
        # Invalid temperature
        config.llm_temperature = 3.0
        assert config.validate() is False
        
        # Invalid confidence threshold
        config = AgentConfig()
        config.confidence_threshold = 1.5
        assert config.validate() is False

    def test_config_presets(self):
        """Test configuration presets."""
        dev_config = load_preset("development")
        assert dev_config.log_level == "DEBUG"
        assert dev_config.enable_caching is False
        
        prod_config = load_preset("production")
        assert prod_config.log_level == "INFO"
        assert prod_config.enable_caching is True

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = AgentConfig(
            llm_model="gpt-4",
            llm_temperature=0.5,
            enable_caching=True
        )
        
        # Convert to dict
        config_dict = config.to_dict()
        assert config_dict["llm_model"] == "gpt-4"
        assert config_dict["llm_temperature"] == 0.5
        
        # Create from dict
        new_config = AgentConfig.from_dict(config_dict)
        assert new_config.llm_model == "gpt-4"
        assert new_config.llm_temperature == 0.5


class TestAgentIntegration:
    """Integration tests for the complete agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization with dependencies."""
        deps = AgentDependencies(
            session_id="test_session",
            user_id="test_user"
        )
        
        assert deps.session_id == "test_session"
        assert deps.user_id == "test_user"
        assert deps.intent_analyzer is not None
        assert deps.response_generator is not None

    @pytest.mark.asyncio
    async def test_smart_search_tool(self):
        """Test smart search tool execution."""
        deps = AgentDependencies(session_id="test")
        
        # Mock the search functions
        with patch('src.agentic_rag.agent.agent.vector_search') as mock_vector:
            mock_vector.return_value = {
                "type": "vector",
                "results": [
                    {
                        "content": "Test content",
                        "score": 0.9
                    }
                ],
                "total_results": 1
            }
            
            # This would test the actual tool execution
            # In a real test, you'd need to properly set up the agent context

    @pytest.mark.asyncio
    async def test_run_query_function(self):
        """Test the main run_query function."""
        with patch('src.agentic_rag.agent.agent.rag_agent.run') as mock_run:
            mock_run.return_value = Mock(
                data={"answer": "Test answer"},
                model_used="gpt-4",
                tools_used=["smart_search"]
            )
            
            result = await run_query(
                query="What is AI?",
                session_id="test_session",
                user_id="test_user"
            )
            
            assert result["status"] == "success"
            assert result["query"] == "What is AI?"
            assert "response" in result

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in agent."""
        with patch('src.agentic_rag.agent.agent.rag_agent.run') as mock_run:
            mock_run.side_effect = Exception("Test error")
            
            result = await run_query(
                query="Test query",
                session_id="test_session"
            )
            
            assert result["status"] == "error"
            assert "Test error" in result["error"]


class TestPerformance:
    """Performance tests for agent components."""

    @pytest.mark.asyncio
    async def test_intent_analysis_performance(self):
        """Test intent analysis meets performance targets."""
        analyzer = IntentAnalyzer()
        
        queries = [
            "What is OpenAI?",
            "How are Microsoft and OpenAI related?",
            "Show me the timeline of AI developments",
            "Compare Google and Microsoft AI strategies"
        ] * 10  # 40 queries
        
        start = time.perf_counter()
        
        for query in queries:
            await analyzer.analyze(query)
        
        elapsed = time.perf_counter() - start
        avg_time = elapsed / len(queries)
        
        # Should analyze each query in under 100ms
        assert avg_time < 0.1

    @pytest.mark.asyncio
    async def test_response_generation_performance(self):
        """Test response generation performance."""
        generator = ResponseGenerator()
        
        # Mock search results
        search_results = {
            "vector_results": [
                {"content": f"Result {i}", "score": 0.8 + i*0.01}
                for i in range(20)
            ]
        }
        
        mock_query = Mock(complexity_score=0.5)
        
        start = time.perf_counter()
        
        for _ in range(10):
            response = await generator.generate_response(
                "Test query",
                search_results,
                mock_query
            )
        
        elapsed = time.perf_counter() - start
        avg_time = elapsed / 10
        
        # Should generate response in under 500ms
        assert avg_time < 0.5

    def test_routing_performance(self):
        """Test routing performance."""
        router = QueryRouter()
        
        mock_queries = [
            Mock(
                primary_intent=QueryIntent.FACTUAL,
                entities=["Entity1", "Entity2"],
                temporal_context=None,
                confidence=0.8,
                complexity_score=0.5
            )
            for _ in range(100)
        ]
        
        start = time.perf_counter()
        
        for query in mock_queries:
            decision = router.route(query)
        
        elapsed = time.perf_counter() - start
        avg_time = elapsed / len(mock_queries)
        
        # Should route each query in under 1ms
        assert avg_time < 0.001


class TestProviders:
    """Test LLM provider configuration."""
    
    def test_model_capabilities(self):
        """Test model capability retrieval."""
        from src.agentic_rag.agent.providers import get_model_capabilities
        
        capabilities = get_model_capabilities("gpt-4o")
        assert capabilities["supports_vision"] is True
        assert capabilities["supports_function_calling"] is True
        assert capabilities["max_tokens"] > 0
    
    @patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"})
    def test_get_llm_model(self):
        """Test LLM model configuration."""
        # This would test actual model initialization
        # In a real test, you'd mock the OpenAI client
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])