"""Locust load testing scenarios for Agentic RAG API."""

import json
import random
import time
from typing import Dict, List

from locust import HttpUser, task, between, events
from locust.stats import stats_printer, stats_history
import structlog

logger = structlog.get_logger()

# Sample queries for testing
SAMPLE_QUERIES = [
    "What is the relationship between Sam Altman and OpenAI?",
    "Tell me about Microsoft's AI strategy",
    "How does Anthropic compare to OpenAI?",
    "What are the latest developments in AI funding?",
    "Explain the competitive landscape in AI",
    "What is Nvidia's role in the AI ecosystem?",
    "How are startups competing with big tech in AI?",
    "What are the key AI acquisitions recently?",
    "Tell me about AI regulatory challenges",
    "What is the future of generative AI?",
]

SEARCH_TYPES = ["vector", "graph", "hybrid"]


class AgenticRAGUser(HttpUser):
    """Simulated user for load testing the Agentic RAG API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Initialize user session."""
        self.session_id = f"test_session_{self.environment.runner.user_count}_{time.time()}"
        self.query_history = []
        logger.info(f"User session started: {self.session_id}")

    @task(3)
    def chat_simple(self):
        """Simple chat request without streaming."""
        query = random.choice(SAMPLE_QUERIES)
        
        with self.client.post(
            "/api/v1/chat",
            json={
                "message": query,
                "session_id": self.session_id,
                "stream": False,
                "include_sources": True,
                "max_tokens": 500,
            },
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.query_history.append(query)
                
                # Validate response structure
                if "response" in data and "confidence" in data:
                    response.success()
                    logger.debug(
                        f"Chat successful",
                        session_id=self.session_id,
                        confidence=data.get("confidence"),
                        response_time=response.elapsed.total_seconds(),
                    )
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def search_vector(self):
        """Vector search request."""
        query = random.choice(SAMPLE_QUERIES)
        
        with self.client.post(
            "/api/v1/search",
            json={
                "query": query,
                "search_type": "vector",
                "limit": 10,
                "threshold": 0.7,
            },
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                
                # Validate response
                if "results" in data and "search_time_ms" in data:
                    response.success()
                    logger.debug(
                        f"Vector search successful",
                        query=query[:50],
                        results_count=data.get("total_results"),
                        search_time_ms=data.get("search_time_ms"),
                    )
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def search_hybrid(self):
        """Hybrid search request."""
        query = random.choice(SAMPLE_QUERIES)
        
        with self.client.post(
            "/api/v1/search",
            json={
                "query": query,
                "search_type": "hybrid",
                "limit": 15,
                "threshold": 0.65,
            },
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                
                # Validate response
                if "results" in data and "search_time_ms" in data:
                    # Check performance SLO
                    if data.get("search_time_ms", 1000) < 500:
                        response.success()
                    else:
                        response.failure(f"Search too slow: {data.get('search_time_ms')}ms")
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def search_graph(self):
        """Graph search request."""
        query = random.choice(SAMPLE_QUERIES)
        
        with self.client.post(
            "/api/v1/search",
            json={
                "query": query,
                "search_type": "graph",
                "limit": 10,
                "threshold": 0.7,
            },
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                
                # Validate response
                if "results" in data:
                    response.success()
                    logger.debug(
                        f"Graph search successful",
                        query=query[:50],
                        results_count=data.get("total_results"),
                    )
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def chat_with_context(self):
        """Chat with previous context (follow-up questions)."""
        if not self.query_history:
            # No history yet, do a simple chat first
            self.chat_simple()
            return
        
        # Create a follow-up question
        previous_query = random.choice(self.query_history[-3:] if len(self.query_history) > 3 else self.query_history)
        follow_up = f"Tell me more about that. Specifically regarding: {previous_query}"
        
        with self.client.post(
            "/api/v1/chat",
            json={
                "message": follow_up,
                "session_id": self.session_id,
                "stream": False,
                "include_sources": False,
            },
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def get_status(self):
        """Check API status endpoint."""
        with self.client.get(
            "/api/v1/status",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "operational":
                    response.success()
                else:
                    response.failure(f"API not operational: {data.get('status')}")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def streaming_chat(self):
        """Test streaming chat endpoint."""
        query = random.choice(SAMPLE_QUERIES)
        
        with self.client.post(
            "/api/v1/chat/stream",
            json={
                "message": query,
                "session_id": self.session_id,
            },
            stream=True,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                # Read streaming response
                chunks_received = 0
                for line in response.iter_lines():
                    if line:
                        chunks_received += 1
                        if line.startswith(b"data: [DONE]"):
                            break
                
                if chunks_received > 0:
                    response.success()
                else:
                    response.failure("No streaming chunks received")
            else:
                response.failure(f"Status code: {response.status_code}")

    def on_stop(self):
        """Clean up user session."""
        logger.info(f"User session ended: {self.session_id}")


class AdminUser(HttpUser):
    """Admin user for testing administrative endpoints."""
    
    wait_time = between(10, 30)  # Less frequent admin operations
    
    @task(1)
    def check_metrics(self):
        """Check Prometheus metrics endpoint."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                # Validate it's Prometheus format
                if "http_requests_total" in response.text:
                    response.success()
                else:
                    response.failure("Invalid metrics format")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(1)
    def check_health(self):
        """Check health endpoints."""
        endpoints = ["/health", "/health/ready", "/health/live"]
        
        for endpoint in endpoints:
            with self.client.get(endpoint, catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Health check failed: {endpoint}")


# Event handlers for custom metrics and reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Handle test start event."""
    logger.info(
        "Load test starting",
        host=environment.host,
        users=environment.parsed_options.num_users if environment.parsed_options else "N/A",
    )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Handle test stop event."""
    logger.info(
        "Load test completed",
        total_requests=environment.stats.total.num_requests,
        failure_rate=environment.stats.total.fail_ratio,
        avg_response_time=environment.stats.total.avg_response_time,
    )


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track custom metrics for each request."""
    if exception:
        logger.warning(
            f"Request failed",
            request_type=request_type,
            name=name,
            exception=str(exception),
        )
    elif response_time > 1000:  # Log slow requests (>1s)
        logger.warning(
            f"Slow request detected",
            request_type=request_type,
            name=name,
            response_time_ms=response_time,
        )