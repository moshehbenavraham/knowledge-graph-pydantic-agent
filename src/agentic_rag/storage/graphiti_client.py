"""
Graphiti client wrapper for enhanced graph operations.
"""

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class GraphitiClient:
    """
    Enhanced wrapper for Graphiti operations.
    Provides entity extraction, episode management, and search capabilities.
    """

    def __init__(self, neo4j_store, llm_client=None):
        """
        Initialize Graphiti client.

        Args:
            neo4j_store: Neo4j store instance for graph operations
            llm_client: Optional LLM client for entity extraction
        """
        self.neo4j_store = neo4j_store
        self.llm_client = llm_client

    async def extract_and_store_knowledge(
        self, text: str, chunk_id: str, document_id: str
    ) -> dict[str, Any]:
        """
        Extract entities, relationships, and facts from text and store in graph.

        This is the main entry point for knowledge extraction.
        """
        # Extract entities
        entities = await self.extract_entities(text)
        entity_ids = await self.neo4j_store.add_entities(entities, chunk_id)

        # Extract relationships
        relationships = await self.extract_relationships(text, entity_ids)
        rel_count = await self.neo4j_store.add_relationships(relationships, chunk_id)

        # Extract temporal facts
        facts = await self.extract_facts(text)
        episode_ids = await self.neo4j_store.add_episodes(facts, entity_ids, chunk_id, document_id)

        # Update entity importance scores
        for entity_id in entity_ids:
            await self.neo4j_store.update_entity_importance(entity_id)

        return {
            "entities_extracted": len(entities),
            "entity_ids": entity_ids,
            "relationships_extracted": rel_count,
            "facts_extracted": len(facts),
            "episode_ids": episode_ids,
        }

    async def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract entities from text using LLM or NER.
        Returns only entity names and types, no content.
        """
        if not self.llm_client:
            # Fallback to simple NER or pattern matching
            return await self._extract_entities_simple(text)

        # Use LLM for extraction
        prompt = """
        Extract all entities from the following text.
        Return ONLY the entity name and type.
        Do NOT include descriptions or content.

        Entity types: company, person, technology, product, location, event

        Format each entity as:
        {{"name": "entity_name", "type": "entity_type"}}

        Text:
        {text}
        """

        try:
            response = await self.llm_client.extract(
                prompt.format(text=text[:2000])  # Limit text length
            )

            entities = []
            for item in response:
                if isinstance(item, dict) and "name" in item and "type" in item:
                    entities.append(
                        {
                            "name": item["name"][:100],  # Limit name length
                            "type": item["type"].lower(),
                        }
                    )

            return entities[:20]  # Limit number of entities per chunk

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return await self._extract_entities_simple(text)

    async def _extract_entities_simple(self, text: str) -> list[dict[str, Any]]:
        """Simple entity extraction using patterns."""
        import re

        entities = []

        # Extract company names (simple heuristic)
        company_pattern = (
            r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*(?:\s+(?:Inc|Corp|LLC|Ltd|Company|Co)\.?))\b"
        )
        for match in re.finditer(company_pattern, text):
            name = match.group(1).strip()
            if len(name) > 2 and name not in [e["name"] for e in entities]:
                entities.append({"name": name, "type": "company"})

        # Extract person names (simple heuristic)
        person_pattern = r"\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
        for match in re.finditer(person_pattern, text):
            name = match.group(1).strip()
            # Filter out common false positives
            if (
                len(name) > 5
                and name not in [e["name"] for e in entities]
                and not any(word in name for word in ["The", "This", "That", "These"])
            ):
                entities.append({"name": name, "type": "person"})

        return entities[:10]  # Limit to top 10 entities

    async def extract_relationships(self, text: str, entity_ids: list[str]) -> list[dict[str, Any]]:
        """
        Extract relationships between entities.
        """
        if len(entity_ids) < 2:
            return []

        relationships = []

        if self.llm_client:
            # Use LLM to identify relationships

            try:
                # For simplicity, create potential relationships between first few entities
                if len(entity_ids) > 1:
                    relationships.append(
                        {
                            "entity1_id": entity_ids[0],
                            "entity2_id": entity_ids[1],
                            "type": "RELATED_TO",
                            "subtype": "mentioned_together",
                            "confidence": 0.6,
                        }
                    )
            except Exception as e:
                logger.error(f"Relationship extraction failed: {e}")

        return relationships

    async def extract_facts(self, text: str, max_facts: int = 5) -> list[str]:
        """
        Extract key facts from text.
        Facts should be brief (max 500 chars) and self-contained.
        """
        facts = []

        if self.llm_client:
            prompt = """
            Extract {max_facts} key facts from this text.
            Each fact must be:
            - Self-contained and complete
            - Under 500 characters
            - A clear statement

            Text: {text}

            Return facts as a list of strings.
            """

            try:
                response = await self.llm_client.extract(
                    prompt.format(max_facts=max_facts, text=text[:2000])
                )

                for fact in response:
                    if isinstance(fact, str) and len(fact) <= 500:
                        facts.append(fact)
                    elif isinstance(fact, str):
                        facts.append(fact[:497] + "...")

            except Exception as e:
                logger.error(f"Fact extraction failed: {e}")
                facts = await self._extract_facts_simple(text)
        else:
            facts = await self._extract_facts_simple(text)

        return facts[:max_facts]

    async def _extract_facts_simple(self, text: str) -> list[str]:
        """Simple fact extraction using sentence splitting."""
        import re

        # Split into sentences
        sentences = re.split(r"[.!?]\s+", text)

        facts = []
        for sentence in sentences[:10]:  # Check first 10 sentences
            sentence = sentence.strip()
            # Filter for informative sentences
            if 20 < len(sentence) < 500 and any(
                word in sentence.lower()
                for word in [
                    "announced",
                    "launched",
                    "acquired",
                    "raised",
                    "partnered",
                    "developed",
                    "introduced",
                    "revealed",
                    "reported",
                ]
            ):
                facts.append(sentence)

        return facts[:5]

    async def search(
        self, query: str, search_type: str = "hybrid", limit: int = 10, return_dict: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """
        Search the knowledge graph.

        Args:
            query: Search query
            search_type: 'entities', 'episodes', 'relationships', or 'hybrid'
            limit: Maximum number of results
            return_dict: If True, return dict format; if False, return list of results

        Returns:
            List of result objects (default) or dict with categorized results
        """
        collected_results = []
        metadata = {
            "query": query,
            "search_type": search_type,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if search_type in ["entities", "hybrid"]:
            entities = await self.neo4j_store.search_entities(query, limit)
            for entity in entities:
                collected_results.append(
                    {
                        "type": "entity",
                        "content": entity.get("name", ""),
                        "entity_name": entity.get("name", ""),
                        **entity,
                    }
                )

        if search_type in ["episodes", "hybrid"]:
            episodes = await self.neo4j_store.search_episodes(query, limit=limit)
            for episode in episodes:
                collected_results.append(
                    {
                        "type": "episode",
                        "content": episode.get("content", episode.get("description", "")),
                        "fact": episode.get("content", episode.get("description", "")),
                        "timestamp": episode.get("timestamp"),
                        "confidence": episode.get("confidence", 0.8),
                        "source_chunk": episode.get("source_id", ""),
                        "entities": episode.get("entity_ids", []),
                        **episode,
                    }
                )

        if search_type == "relationships":
            # First find relevant entities
            entities = await self.neo4j_store.search_entities(query, limit=5)
            if entities:
                # Get relationships for top entity
                entity_id = entities[0]["id"]
                rel_data = await self.neo4j_store.get_entity_relationships(entity_id)
                collected_results.append(
                    {"type": "relationships", "entity_id": entity_id, **rel_data}
                )

        # Return in requested format
        if return_dict:
            # Legacy dict format
            results = metadata.copy()
            entities_list = [r for r in collected_results if r.get("type") == "entity"]
            episodes_list = [r for r in collected_results if r.get("type") == "episode"]
            rels_list = [r for r in collected_results if r.get("type") == "relationships"]

            if entities_list:
                results["entities"] = entities_list
            if episodes_list:
                results["episodes"] = episodes_list
            if rels_list:
                results["relationships"] = rels_list
            if search_type == "hybrid":
                results["relevance_score"] = self._calculate_relevance(results)
            return results
        # Return list for iteration
        return collected_results[:limit]

    def _calculate_relevance(self, results: dict[str, Any]) -> float:
        """Calculate overall relevance score for hybrid search results."""
        score = 0.0

        # Weight different result types
        if results.get("entities"):
            score += len(results["entities"]) * 0.3

        if results.get("episodes"):
            score += len(results["episodes"]) * 0.5

        if results.get("relationships"):
            score += 0.2

        return min(score, 1.0)

    async def get_entity_context(self, entity_id: str) -> dict[str, Any]:
        """
        Get comprehensive context for an entity.
        """
        # Get entity details and relationships
        rel_data = await self.neo4j_store.get_entity_relationships(entity_id, depth=2)

        # Get timeline of episodes
        timeline = await self.neo4j_store.get_entity_timeline(entity_id, limit=20)

        # Combine into context
        context = {
            "entity": rel_data["entity"] if rel_data else None,
            "relationships": rel_data["relationships"] if rel_data else [],
            "related_entities": rel_data["related_entities"] if rel_data else [],
            "timeline": timeline,
            "summary": await self._generate_entity_summary(rel_data, timeline),
        }

        return context

    async def _generate_entity_summary(
        self, rel_data: dict[str, Any], timeline: list[dict[str, Any]]
    ) -> str:
        """Generate a brief summary of an entity."""
        if not rel_data:
            return "No information available."

        entity = rel_data["entity"]
        summary_parts = []

        # Basic info
        summary_parts.append(
            f"{entity['name']} ({entity['type']}) has {entity.get('mention_count', 0)} mentions"
        )

        # Relationships
        if rel_data["relationships"]:
            summary_parts.append(f"Connected to {len(rel_data['related_entities'])} other entities")

        # Recent activity
        if timeline:
            summary_parts.append(f"Most recent activity: {timeline[0]['fact'][:100]}")

        return ". ".join(summary_parts)

    async def find_connections(self, entity1_name: str, entity2_name: str) -> list[dict[str, Any]]:
        """
        Find connections between two entities by name.
        """
        # Search for entities
        entities1 = await self.neo4j_store.search_entities(entity1_name, limit=1)
        entities2 = await self.neo4j_store.search_entities(entity2_name, limit=1)

        if not entities1 or not entities2:
            return []

        # Find paths
        paths = await self.neo4j_store.find_paths(
            entities1[0]["id"], entities2[0]["id"], max_depth=3
        )

        return paths

    async def get_temporal_context(
        self, start_date: datetime, end_date: datetime, entity_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Get temporal context (episodes) within a date range.
        """
        episodes = await self.neo4j_store.search_episodes(
            query="*",  # Match all
            entity_ids=entity_ids,
            time_range=(start_date, end_date),
            limit=100,
        )

        # Sort by timestamp (most recent first)
        episodes.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)

        return episodes

    async def build_knowledge_graph_summary(self) -> dict[str, Any]:
        """
        Build a summary of the entire knowledge graph.
        """
        stats = await self.neo4j_store.get_graph_statistics()

        summary = {
            "statistics": stats,
            "health": {
                "is_healthy": stats["entity_count"] > 0,
                "has_relationships": stats["relationship_count"] > 0,
                "has_episodes": stats["episode_count"] > 0,
                "graph_density": stats.get("graph_density", 0),
            },
            "recommendations": [],
        }

        # Add recommendations based on stats
        if stats["entity_count"] == 0:
            summary["recommendations"].append(
                "No entities found. Ingest documents to build the graph."
            )
        elif stats["relationship_count"] == 0:
            summary["recommendations"].append(
                "No relationships found. Consider improving entity extraction."
            )
        elif stats.get("graph_density", 0) < 0.01:
            summary["recommendations"].append(
                "Graph density is low. Consider extracting more relationships."
            )

        return summary
