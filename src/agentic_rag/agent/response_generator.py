"""
Response generation with citation management and confidence scoring.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Represents a citation for a piece of information."""

    document_title: str
    document_id: str
    chunk_id: str | None
    content: str
    confidence: float
    source_type: str  # 'vector', 'graph', 'document'


@dataclass
class GeneratedResponse:
    """A generated response with citations and metadata."""

    answer: str
    citations: list[Citation]
    confidence: float
    search_strategy_used: str
    follow_up_questions: list[str]
    metadata: dict[str, Any]


class ResponseGenerator:
    """
    Generates responses from search results with proper citations.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.min_confidence_threshold = 0.5

    async def generate_response(
        self, query: str, search_results: dict[str, Any], analyzed_query: Any
    ) -> GeneratedResponse:
        """
        Generate a comprehensive response from search results.
        """
        # Extract relevant content
        relevant_content = self._extract_relevant_content(search_results)

        # Generate citations
        citations = self._generate_citations(relevant_content)

        # Calculate overall confidence
        confidence = self._calculate_confidence(relevant_content, analyzed_query)

        # Synthesize answer
        answer = await self._synthesize_answer(query, relevant_content, citations, confidence)

        # Generate follow-up questions
        follow_ups = self._generate_follow_ups(query, relevant_content)

        return GeneratedResponse(
            answer=answer,
            citations=citations,
            confidence=confidence,
            search_strategy_used=search_results.get("search_type", "unknown"),
            follow_up_questions=follow_ups,
            metadata={
                "total_sources": len(citations),
                "content_pieces": len(relevant_content),
                "query_complexity": analyzed_query.complexity_score if analyzed_query else 0.5,
            },
        )

    def _extract_relevant_content(self, search_results: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and rank relevant content from search results."""
        content_pieces = []

        # Extract from vector results
        if "vector_results" in search_results:
            for result in search_results.get("vector_results", []):
                if isinstance(result, dict):
                    content_pieces.append(
                        {
                            "content": result.get("content", ""),
                            "score": result.get("score", 0.5),
                            "source_type": "vector",
                            "document_title": result.get("document_title", "Unknown"),
                            "document_id": result.get("document_id"),
                            "chunk_id": result.get("chunk_id"),
                        }
                    )

        # Extract from results list (alternative format)
        if "results" in search_results:
            for result in search_results.get("results", []):
                if isinstance(result, dict):
                    content_pieces.append(
                        {
                            "content": result.get("content", ""),
                            "score": result.get("score", 0.5),
                            "source_type": "vector",
                            "document_title": result.get("document_title", "Unknown"),
                            "document_id": result.get("document_id"),
                            "chunk_id": result.get("chunk_id"),
                        }
                    )

        # Extract from graph results
        if "graph_results" in search_results:
            graph_data = search_results["graph_results"]
            if isinstance(graph_data, dict):
                for fact in graph_data.get("facts", []):
                    content_pieces.append(
                        {
                            "content": fact.get("fact", ""),
                            "score": fact.get("confidence", 0.8),
                            "source_type": "graph",
                            "source_chunk": fact.get("source_chunk"),
                            "entities": fact.get("entities", []),
                        }
                    )

        # Extract from facts (alternative format)
        if "facts" in search_results:
            for fact in search_results.get("facts", []):
                content_pieces.append(
                    {
                        "content": fact.get("fact", "") if isinstance(fact, dict) else str(fact),
                        "score": fact.get("confidence", 0.8) if isinstance(fact, dict) else 0.8,
                        "source_type": "graph",
                        "source_chunk": (
                            fact.get("source_chunk") if isinstance(fact, dict) else None
                        ),
                        "entities": fact.get("entities", []) if isinstance(fact, dict) else [],
                    }
                )

        # Sort by relevance score
        content_pieces.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Filter by minimum confidence
        content_pieces = [
            c for c in content_pieces if c.get("score", 0) >= self.min_confidence_threshold
        ]

        return content_pieces[:20]  # Limit to top 20 pieces

    def _generate_citations(self, content_pieces: list[dict[str, Any]]) -> list[Citation]:
        """Generate citations for content pieces."""
        citations = []
        seen_chunks = set()  # Avoid duplicate citations

        for piece in content_pieces:
            chunk_id = piece.get("chunk_id") or piece.get("source_chunk")

            # Skip if already cited
            if chunk_id and chunk_id in seen_chunks:
                continue

            citation = Citation(
                document_title=piece.get("document_title", "Unknown Source"),
                document_id=piece.get("document_id", ""),
                chunk_id=chunk_id,
                content=piece.get("content", "")[:200],  # Truncate for citation
                confidence=piece.get("score", 0.5),
                source_type=piece.get("source_type", "unknown"),
            )

            citations.append(citation)
            if chunk_id:
                seen_chunks.add(chunk_id)

        return citations

    def _calculate_confidence(
        self, content_pieces: list[dict[str, Any]], analyzed_query: Any
    ) -> float:
        """Calculate overall confidence in the response."""
        if not content_pieces:
            return 0.0

        # Factors affecting confidence:
        # 1. Average relevance score
        avg_score = sum(c.get("score", 0) for c in content_pieces) / len(content_pieces)

        # 2. Number of supporting sources
        source_factor = min(len(content_pieces) / 10, 1.0)  # Max at 10 sources

        # 3. Query complexity (simpler queries should have higher confidence)
        complexity_factor = 1.0
        if analyzed_query and hasattr(analyzed_query, "complexity_score"):
            complexity_factor = 1.0 - (analyzed_query.complexity_score * 0.3)

        # 4. Source diversity (both vector and graph results)
        source_types = set(c.get("source_type", "unknown") for c in content_pieces)
        diversity_factor = 1.0 if len(source_types) > 1 else 0.8

        # Weighted combination
        confidence = (
            avg_score * 0.4 + source_factor * 0.2 + complexity_factor * 0.2 + diversity_factor * 0.2
        )

        return min(max(confidence, 0.0), 1.0)

    async def _synthesize_answer(
        self,
        query: str,
        content_pieces: list[dict[str, Any]],
        citations: list[Citation],
        confidence: float,
    ) -> str:
        """Synthesize a coherent answer from content pieces."""
        if not content_pieces:
            return "I couldn't find relevant information to answer your question."

        # For now, a simple implementation
        # In production, this would use LLM for synthesis

        # Group content by source type
        vector_content = [c for c in content_pieces if c.get("source_type") == "vector"]
        graph_content = [c for c in content_pieces if c.get("source_type") == "graph"]

        answer_parts = []

        # Add main answer from top results
        if vector_content:
            answer_parts.append(vector_content[0].get("content", ""))

        # Add facts from knowledge graph
        if graph_content:
            facts = [c.get("content", "") for c in graph_content[:3]]
            if facts:
                answer_parts.append("\n\nRelevant facts:\n- " + "\n- ".join(facts))

        # Add confidence indicator
        confidence_text = self._confidence_to_text(confidence)
        answer_parts.append(f"\n\n*Confidence: {confidence_text}*")

        # Add citations
        if citations:
            citation_text = "\n\nSources:\n"
            for i, cite in enumerate(citations[:5], 1):
                citation_text += f"{i}. {cite.document_title} "
                citation_text += f"(Confidence: {cite.confidence:.1%})\n"
            answer_parts.append(citation_text)

        return "\n".join(answer_parts)

    def _confidence_to_text(self, confidence: float) -> str:
        """Convert confidence score to human-readable text."""
        if confidence >= 0.9:
            return "Very High"
        if confidence >= 0.75:
            return "High"
        if confidence >= 0.6:
            return "Moderate"
        if confidence >= 0.4:
            return "Low"
        return "Very Low"

    def _generate_follow_ups(self, query: str, content_pieces: list[dict[str, Any]]) -> list[str]:
        """Generate relevant follow-up questions."""
        follow_ups = []

        # Extract entities mentioned in results
        entities = set()
        for piece in content_pieces:
            if "entities" in piece:
                entities.update(piece["entities"])

        # Generate entity-based follow-ups
        for entity in list(entities)[:3]:
            follow_ups.append(f"What else can you tell me about {entity}?")

        # Add general follow-ups
        follow_ups.extend(
            [
                "Would you like more details on any specific aspect?",
                "Should I search for related information?",
            ]
        )

        return follow_ups[:5]

    async def merge_results(
        self, vector_results: dict[str, Any], graph_results: dict[str, Any], analyzed_query: Any
    ) -> dict[str, Any]:
        """Merge results from multiple search strategies."""
        merged = {
            "type": "hybrid",
            "vector_results": (
                vector_results.get("results", []) if isinstance(vector_results, dict) else []
            ),
            "graph_results": graph_results,
            "merged_results": [],
        }

        # Score and rank all results together
        all_results = []

        # Add vector results
        for vr in merged["vector_results"]:
            if isinstance(vr, dict):
                all_results.append(
                    {
                        **vr,
                        "source": "vector",
                        "adjusted_score": vr.get("score", 0.5) * 0.6,  # Weight for vector
                    }
                )

        # Add graph facts as results
        if isinstance(graph_results, dict):
            for fact in graph_results.get("facts", []):
                all_results.append(
                    {
                        "content": fact.get("fact", ""),
                        "source": "graph",
                        "score": fact.get("confidence", 0.8),
                        "adjusted_score": fact.get("confidence", 0.8) * 0.4,  # Weight for graph
                        "entities": fact.get("entities", []),
                    }
                )

        # Sort by adjusted score
        all_results.sort(key=lambda x: x.get("adjusted_score", 0), reverse=True)

        merged["merged_results"] = all_results[:20]

        return merged

    async def format_streaming_response(
        self, chunk: str, chunk_type: str = "content", metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Format a chunk for streaming response."""
        response = {
            "type": chunk_type,
            "content": chunk,
            "timestamp": None,  # Would add timestamp in production
        }

        if metadata:
            response["metadata"] = metadata

        return response

    def extract_answer_sections(self, full_answer: str) -> dict[str, str]:
        """Extract different sections from a full answer."""
        sections = {
            "summary": "",
            "details": "",
            "facts": [],
            "citations": [],
            "confidence": "",
            "follow_ups": [],
        }

        # Simple parsing - would be more sophisticated in production
        lines = full_answer.split("\n")
        current_section = "summary"

        for line in lines:
            line = line.strip()

            if "Relevant facts:" in line:
                current_section = "facts"
            elif "Sources:" in line:
                current_section = "citations"
            elif "Confidence:" in line:
                sections["confidence"] = line.replace("*", "").replace("Confidence:", "").strip()
            elif line.startswith("- ") and current_section == "facts":
                sections["facts"].append(line[2:])
            elif line and current_section == "summary":
                sections["summary"] += line + " "
            elif line and current_section == "citations":
                sections["citations"].append(line)

        return sections
