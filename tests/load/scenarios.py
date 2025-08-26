"""Advanced load testing scenarios for stress testing and performance validation."""

import random
import time
from typing import List

from locust import HttpUser, TaskSet, task, between, constant, constant_pacing
from locust import events
import structlog

logger = structlog.get_logger()


class StressTestScenario(TaskSet):
    """Stress testing scenario with aggressive load patterns."""

    @task(5)
    def rapid_fire_search(self):
        """Rapid consecutive searches to test rate limiting."""
        queries = [
            "AI funding trends",
            "Machine learning startups",
            "Tech acquisitions 2024",
            "OpenAI competitors",
            "Cloud computing costs",
        ]
        
        for query in random.sample(queries, 3):
            self.client.post(
                "/api/v1/search",
                json={
                    "query": query,
                    "search_type": "vector",
                    "limit": 5,
                },
                name="/api/v1/search [rapid]",
            )
            time.sleep(0.1)  # 100ms between requests

    @task(3)
    def large_payload_chat(self):
        """Test with large message payloads."""
        # Generate a large message (simulate complex multi-part question)
        base_query = "Analyze the following aspects of AI development: "
        aspects = [
            "technological advancement",
            "economic impact",
            "regulatory challenges",
            "ethical considerations",
            "market dynamics",
            "competitive landscape",
            "investment trends",
            "talent acquisition",
        ]
        large_message = base_query + ", ".join(
            [f"{i+1}) {aspect} with detailed examples" for i, aspect in enumerate(aspects)]
        )
        
        self.client.post(
            "/api/v1/chat",
            json={
                "message": large_message,
                "max_tokens": 2000,
                "include_sources": True,
            },
            name="/api/v1/chat [large_payload]",
        )

    @task(2)
    def concurrent_searches(self):
        """Simulate concurrent search requests."""
        search_types = ["vector", "graph", "hybrid"]
        
        # Fire multiple searches in parallel
        for search_type in search_types:
            self.client.post(
                "/api/v1/search",
                json={
                    "query": "AI market analysis",
                    "search_type": search_type,
                    "limit": 20,
                },
                name=f"/api/v1/search [{search_type}_concurrent]",
            )

    @task(1)
    def cache_buster(self):
        """Test cache invalidation with unique queries."""
        unique_query = f"Random query {random.randint(1000, 9999)} at {time.time()}"
        
        self.client.post(
            "/api/v1/search",
            json={
                "query": unique_query,
                "search_type": "hybrid",
                "limit": 10,
            },
            name="/api/v1/search [cache_buster]",
        )


class SpikeTestScenario(TaskSet):
    """Spike testing scenario to test sudden load increases."""

    def on_start(self):
        """Initialize spike test."""
        self.spike_active = False
        self.normal_load_count = 0

    @task(10)
    def normal_load(self):
        """Normal load pattern."""
        self.normal_load_count += 1
        
        # Trigger spike every 20 normal requests
        if self.normal_load_count % 20 == 0:
            self.spike_active = True
        
        self.client.post(
            "/api/v1/chat",
            json={
                "message": "What is artificial intelligence?",
                "stream": False,
            },
            name="/api/v1/chat [normal]",
        )

    @task(1)
    def spike_load(self):
        """Spike load pattern."""
        if not self.spike_active:
            return
        
        # Generate 10 rapid requests
        for i in range(10):
            self.client.post(
                "/api/v1/search",
                json={
                    "query": f"Spike test query {i}",
                    "search_type": "vector",
                    "limit": 5,
                },
                name="/api/v1/search [spike]",
            )
        
        self.spike_active = False


class EnduranceTestScenario(TaskSet):
    """Long-running endurance test to detect memory leaks and degradation."""

    def on_start(self):
        """Initialize endurance test."""
        self.request_count = 0
        self.session_id = f"endurance_{time.time()}"

    @task(5)
    def steady_chat(self):
        """Steady chat requests over extended period."""
        self.request_count += 1
        
        # Vary the query complexity over time
        if self.request_count % 100 == 0:
            message = "Complex: " + " AND ".join([f"topic_{i}" for i in range(10)])
        else:
            message = "Simple query about AI"
        
        response = self.client.post(
            "/api/v1/chat",
            json={
                "message": message,
                "session_id": self.session_id,
            },
            name="/api/v1/chat [endurance]",
        )
        
        # Log every 100th request for monitoring
        if self.request_count % 100 == 0:
            logger.info(
                f"Endurance test progress",
                requests_completed=self.request_count,
                session_id=self.session_id,
            )

    @task(3)
    def steady_search(self):
        """Steady search requests."""
        search_types = ["vector", "graph", "hybrid"]
        search_type = search_types[self.request_count % 3]
        
        self.client.post(
            "/api/v1/search",
            json={
                "query": "Consistent search query",
                "search_type": search_type,
                "limit": 10,
            },
            name=f"/api/v1/search [{search_type}_endurance]",
        )

    @task(1)
    def memory_check(self):
        """Periodically check system status."""
        response = self.client.get("/api/v1/status")
        
        if response.status_code == 200:
            data = response.json()
            if self.request_count % 50 == 0:
                logger.info(
                    "System status check",
                    active_connections=data.get("metrics", {}).get("active_connections"),
                    cache_healthy=data.get("cache", {}).get("healthy"),
                )


class RealisticUserScenario(TaskSet):
    """Realistic user behavior patterns."""

    def on_start(self):
        """Initialize realistic user session."""
        self.session_id = f"user_{random.randint(1000, 9999)}"
        self.conversation_depth = 0
        self.topics = [
            "artificial intelligence",
            "machine learning",
            "data science",
            "cloud computing",
            "cybersecurity",
        ]
        self.current_topic = random.choice(self.topics)

    @task(10)
    def browse_and_search(self):
        """User browsing and searching pattern."""
        # Initial search
        self.client.post(
            "/api/v1/search",
            json={
                "query": self.current_topic,
                "search_type": "hybrid",
                "limit": 10,
            },
            name="/api/v1/search [browse]",
        )
        
        # Simulate reading time
        time.sleep(random.uniform(2, 5))

    @task(5)
    def ask_question(self):
        """User asks a question about current topic."""
        questions = [
            f"What is {self.current_topic}?",
            f"How does {self.current_topic} work?",
            f"What are the applications of {self.current_topic}?",
            f"What are the challenges in {self.current_topic}?",
        ]
        
        self.client.post(
            "/api/v1/chat",
            json={
                "message": random.choice(questions),
                "session_id": self.session_id,
                "include_sources": True,
            },
            name="/api/v1/chat [question]",
        )
        
        self.conversation_depth += 1
        
        # Simulate reading response
        time.sleep(random.uniform(3, 8))

    @task(3)
    def follow_up_question(self):
        """Ask follow-up question if in conversation."""
        if self.conversation_depth > 0:
            follow_ups = [
                "Can you explain that in more detail?",
                "What are some examples?",
                "How does this compare to alternatives?",
                "What are the recent developments?",
            ]
            
            self.client.post(
                "/api/v1/chat",
                json={
                    "message": random.choice(follow_ups),
                    "session_id": self.session_id,
                },
                name="/api/v1/chat [follow_up]",
            )
            
            # Simulate reading
            time.sleep(random.uniform(2, 6))

    @task(2)
    def change_topic(self):
        """Switch to a different topic."""
        self.current_topic = random.choice(self.topics)
        self.conversation_depth = 0
        logger.debug(f"User switched topic to: {self.current_topic}")


# User classes with different scenarios
class StressTestUser(HttpUser):
    """User for stress testing."""
    tasks = [StressTestScenario]
    wait_time = constant(0.5)  # Aggressive timing


class SpikeTestUser(HttpUser):
    """User for spike testing."""
    tasks = [SpikeTestScenario]
    wait_time = between(1, 2)


class EnduranceTestUser(HttpUser):
    """User for endurance testing."""
    tasks = [EnduranceTestScenario]
    wait_time = constant_pacing(2)  # Consistent pacing


class RealisticUser(HttpUser):
    """User with realistic behavior."""
    tasks = [RealisticUserScenario]
    wait_time = between(1, 10)  # Variable human-like timing