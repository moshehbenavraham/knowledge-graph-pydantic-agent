"""
Knowledge extraction for entities, relationships, and facts.

Extracts structured knowledge from text without storing content,
maintaining the zero duplication principle.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic_ai import Agent

from src.agentic_rag.config import get_config

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities that can be extracted."""

    COMPANY = "company"
    PERSON = "person"
    TECHNOLOGY = "technology"
    PRODUCT = "product"
    LOCATION = "location"
    EVENT = "event"
    ORGANIZATION = "organization"
    CONCEPT = "concept"


class RelationshipType(Enum):
    """Types of relationships between entities."""

    WORKS_AT = "works_at"
    FOUNDED = "founded"
    INVESTED_IN = "invested_in"
    ACQUIRED = "acquired"
    PARTNERS_WITH = "partners_with"
    COMPETES_WITH = "competes_with"
    OWNS = "owns"
    DEVELOPS = "develops"
    USES = "uses"
    LOCATED_IN = "located_in"
    PART_OF = "part_of"
    RELATED_TO = "related_to"


@dataclass
class Entity:
    """Represents an extracted entity (name and type only, no content)."""

    name: str
    type: EntityType
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate entity."""
        if not self.name or not self.name.strip():
            raise ValueError("Entity name cannot be empty")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")
        # Ensure no content is stored
        self.name = self.name.strip()[:100]  # Limit name length

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value if isinstance(self.type, EntityType) else self.type,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class Relationship:
    """Represents a relationship between entities."""

    source: str  # Source entity name
    target: str  # Target entity name
    type: RelationshipType
    confidence: float = 1.0
    temporal_marker: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate relationship."""
        if not self.source or not self.target:
            raise ValueError("Source and target entities are required")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type.value if isinstance(self.type, RelationshipType) else self.type,
            "confidence": self.confidence,
            "temporal_marker": self.temporal_marker,
            "metadata": self.metadata,
        }


@dataclass
class Fact:
    """Represents a temporal fact (brief statement, not full content)."""

    text: str  # Brief fact, max 500 chars
    timestamp: datetime | None = None
    entities: list[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and truncate fact."""
        if not self.text:
            raise ValueError("Fact text cannot be empty")
        # Enforce 500 character limit
        self.text = self.text.strip()[:500]
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "entities": self.entities,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class KnowledgeExtractor:
    """
    Extract structured knowledge from text without storing content.

    Extracts entities (names only), relationships, and brief facts
    while maintaining the zero content duplication principle.
    """

    # Relationship patterns for pattern matching
    RELATIONSHIP_PATTERNS = {
        RelationshipType.WORKS_AT: [
            r"(\w+(?:\s+\w+)*)\s+(?:works?\s+at|employed\s+by|joined)\s+(\w+(?:\s+\w+)*)",
            r"(\w+(?:\s+\w+)*),?\s+(?:CEO|CTO|founder|president|director)\s+(?:of|at)\s+(\w+(?:\s+\w+)*)",
        ],
        RelationshipType.FOUNDED: [
            r"(\w+(?:\s+\w+)*)\s+founded\s+(\w+(?:\s+\w+)*)",
            r"(\w+(?:\s+\w+)*)\s+(?:created|established|started)\s+(\w+(?:\s+\w+)*)",
        ],
        RelationshipType.INVESTED_IN: [
            r"(\w+(?:\s+\w+)*)\s+invested\s+(?:in|\$[\d.]+[MBK]?\s+in)\s+(\w+(?:\s+\w+)*)",
            r"(\w+(?:\s+\w+)*)\s+(?:funded|backed)\s+(\w+(?:\s+\w+)*)",
        ],
        RelationshipType.ACQUIRED: [
            r"(\w+(?:\s+\w+)*)\s+(?:acquired|bought|purchased)\s+(\w+(?:\s+\w+)*)",
            r"(\w+(?:\s+\w+)*)\s+acquisition\s+of\s+(\w+(?:\s+\w+)*)",
        ],
    }

    def __init__(self):
        """Initialize knowledge extractor."""
        self.config = get_config()
        self._llm_agent = None

    @property
    def llm_agent(self) -> Agent:
        """Lazy load LLM agent."""
        if self._llm_agent is None:
            self._llm_agent = Agent(
                model=f"{self.config.llm.provider}:{self.config.llm.extraction_model}",
                api_key=self.config.llm.api_key,
            )
        return self._llm_agent

    async def extract(self, text: str, chunk_id: str | None = None) -> dict[str, Any]:
        """
        Extract all knowledge from text.

        Args:
            text: Text to extract from
            chunk_id: Optional chunk identifier

        Returns:
            Dictionary with entities, relationships, and facts
        """
        # Run extractions in parallel
        tasks = [
            self.extract_entities(text),
            self.extract_facts(text),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        entities = results[0] if not isinstance(results[0], Exception) else []
        facts = results[1] if not isinstance(results[1], Exception) else []

        # Extract relationships after entities (needs entity list)
        relationships = await self.extract_relationships(text, entities)

        return {
            "entities": entities,
            "relationships": relationships,
            "facts": facts,
            "chunk_id": chunk_id,
        }

    async def extract_entities(self, text: str) -> list[Entity]:
        """
        Extract entity names and types only (no content).

        Args:
            text: Text to extract entities from

        Returns:
            List of entities
        """
        try:
            # First try pattern-based extraction for common patterns
            pattern_entities = self._extract_entities_by_pattern(text)

            # Then use LLM for comprehensive extraction
            prompt = """
            Extract entities from this text.
            Return ONLY the entity name and type.
            Do NOT include descriptions or content.

            Valid types: company, person, technology, product, location, event, organization

            Format each entity as:
            {"name": "...", "type": "...", "confidence": 0.0-1.0}

            Return as JSON array. Maximum 10 entities.

            Text: {text}
            """

            response = await self.llm_agent.run(
                prompt.format(text=text[:2000])
            )  # Limit text length

            # Parse response
            entities = []
            try:
                import json

                entity_data = json.loads(response.data)
                if not isinstance(entity_data, list):
                    entity_data = [entity_data]

                for item in entity_data[:10]:  # Limit to 10 entities
                    if isinstance(item, dict) and "name" in item and "type" in item:
                        try:
                            entity_type = EntityType(item["type"].lower())
                        except ValueError:
                            entity_type = EntityType.CONCEPT

                        entities.append(
                            Entity(
                                name=item["name"][:100],  # Limit name length
                                type=entity_type,
                                confidence=item.get("confidence", 0.8),
                            )
                        )
            except json.JSONDecodeError:
                logger.warning("Failed to parse entity extraction response")

            # Merge with pattern-based entities
            entity_names = {e.name.lower() for e in entities}
            for pe in pattern_entities:
                if pe.name.lower() not in entity_names:
                    entities.append(pe)

            return entities[: self.config.ingestion.max_entities_per_chunk]

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def _extract_entities_by_pattern(self, text: str) -> list[Entity]:
        """
        Extract entities using regex patterns.

        Args:
            text: Text to extract from

        Returns:
            List of entities
        """
        entities = []

        # Company patterns
        company_pattern = (
            r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:Inc|Corp|LLC|Ltd|Company|Corporation)\b"
        )
        for match in re.finditer(company_pattern, text):
            entities.append(Entity(name=match.group(1), type=EntityType.COMPANY, confidence=0.9))

        # Technology patterns
        tech_pattern = r"\b(GPT-\d+|DALL-E|LaMDA|PaLM|Claude|Gemini|LLaMA)\b"
        for match in re.finditer(tech_pattern, text, re.IGNORECASE):
            entities.append(
                Entity(name=match.group(1), type=EntityType.TECHNOLOGY, confidence=0.95)
            )

        return entities

    async def extract_relationships(self, text: str, entities: list[Entity]) -> list[Relationship]:
        """
        Extract relationships between entities.

        Args:
            text: Text to extract from
            entities: List of entities found in text

        Returns:
            List of relationships
        """
        if len(entities) < 2:
            return []

        relationships = []

        # Pattern-based extraction
        for rel_type, patterns in self.RELATIONSHIP_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    source = match.group(1)
                    target = match.group(2)

                    # Verify entities exist
                    source_entity = self._find_entity(source, entities)
                    target_entity = self._find_entity(target, entities)

                    if source_entity and target_entity:
                        relationships.append(
                            Relationship(
                                source=source_entity.name,
                                target=target_entity.name,
                                type=rel_type,
                                confidence=0.8,
                            )
                        )

        # LLM-based extraction for complex relationships
        if len(entities) > 1:
            entity_names = [e.name for e in entities]
            prompt = f"""
            Identify relationships between these entities: {', '.join(entity_names[:10])}

            Valid relationship types: works_at, founded, invested_in, acquired, partners_with, competes_with

            Return as JSON array:
            [{{"source": "...", "target": "...", "type": "...", "confidence": 0.0-1.0}}]

            Text: {text[:1500]}
            """

            try:
                response = await self.llm_agent.run(prompt)
                import json

                rel_data = json.loads(response.data)

                for item in rel_data[:10]:  # Limit relationships
                    if self._validate_relationship(item, entity_names):
                        try:
                            rel_type = RelationshipType(item["type"])
                        except ValueError:
                            rel_type = RelationshipType.RELATED_TO

                        relationships.append(
                            Relationship(
                                source=item["source"],
                                target=item["target"],
                                type=rel_type,
                                confidence=item.get("confidence", 0.7),
                            )
                        )
            except Exception as e:
                logger.warning(f"LLM relationship extraction failed: {e}")

        return self._deduplicate_relationships(relationships)

    async def extract_facts(self, text: str, max_length: int = 500) -> list[Fact]:
        """
        Extract brief temporal facts (not full content).

        Args:
            text: Text to extract facts from
            max_length: Maximum length of each fact

        Returns:
            List of facts
        """
        try:
            prompt = f"""
            Extract 3-5 key facts from this text.
            Each fact must be:
            - Self-contained and complete
            - Under {max_length} characters
            - A brief statement, not a content excerpt
            - Include temporal markers when available (dates, timeframes)

            Good example: "Microsoft invested $10B in OpenAI in January 2023"
            Bad example: Long paragraph or content excerpt

            Return as JSON array:
            [{{"text": "...", "confidence": 0.0-1.0}}]

            Text: {text[:2000]}
            """

            response = await self.llm_agent.run(prompt)

            facts = []
            try:
                import json

                fact_data = json.loads(response.data)

                for item in fact_data[:5]:  # Max 5 facts
                    if isinstance(item, dict) and "text" in item:
                        fact_text = item["text"].strip()[:max_length]

                        # Extract temporal markers
                        timestamp = self._extract_timestamp(fact_text)

                        facts.append(
                            Fact(
                                text=fact_text,
                                timestamp=timestamp,
                                confidence=item.get("confidence", 0.8),
                            )
                        )
            except json.JSONDecodeError:
                logger.warning("Failed to parse fact extraction response")

            return facts

        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
            return []

    def _find_entity(self, name: str, entities: list[Entity]) -> Entity | None:
        """
        Find entity by name (case-insensitive).

        Args:
            name: Entity name to find
            entities: List of entities

        Returns:
            Found entity or None
        """
        name_lower = name.lower().strip()
        for entity in entities:
            if entity.name.lower() == name_lower or name_lower in entity.name.lower():
                return entity
        return None

    def _validate_relationship(self, rel_dict: dict, entity_names: list[str]) -> bool:
        """
        Validate relationship data.

        Args:
            rel_dict: Relationship dictionary
            entity_names: Valid entity names

        Returns:
            True if valid
        """
        if not isinstance(rel_dict, dict):
            return False

        required = ["source", "target", "type"]
        if not all(k in rel_dict for k in required):
            return False

        # Check if entities exist
        source_valid = any(rel_dict["source"] in name for name in entity_names)
        target_valid = any(rel_dict["target"] in name for name in entity_names)

        return source_valid and target_valid

    def _deduplicate_relationships(self, relationships: list[Relationship]) -> list[Relationship]:
        """
        Remove duplicate relationships.

        Args:
            relationships: List of relationships

        Returns:
            Deduplicated list
        """
        seen = set()
        unique = []

        for rel in relationships:
            key = (
                rel.source,
                rel.target,
                rel.type.value if isinstance(rel.type, RelationshipType) else rel.type,
            )
            if key not in seen:
                seen.add(key)
                unique.append(rel)

        return unique

    def _extract_timestamp(self, text: str) -> datetime | None:
        """
        Extract timestamp from text.

        Args:
            text: Text containing potential date

        Returns:
            Datetime or None
        """
        # Simple date patterns
        patterns = [
            r"(\d{4})-(\d{1,2})-(\d{1,2})",  # YYYY-MM-DD
            r"(\d{1,2})/(\d{1,2})/(\d{4})",  # MM/DD/YYYY
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    # Simple parsing - would need more robust solution in production
                    return datetime.now()  # Placeholder
                except (ValueError, TypeError):
                    pass

        return None
