"""
Dashboard utilities for GraphRAG analytics and visualization.

Provides Cypher query generation, data formatting for visualizations,
time-series aggregation, and export functions.
"""

import csv
import json
from datetime import timedelta
from typing import Any

import pandas as pd
from pyvis.network import Network


def generate_entity_cypher(filters: dict[str, Any] | None = None, limit: int = 50) -> str:
    """
    Generate Cypher query for entity retrieval with optional filters.

    Args:
        filters: Optional filters (entity_types, min_relationships, search_term)
        limit: Maximum number of entities to return

    Returns:
        Cypher query string
    """
    filters = filters or {}
    entity_types = filters.get("entity_types", [])
    min_relationships = filters.get("min_relationships", 0)
    search_term = filters.get("search_term", "")

    query = "MATCH (e:Entity)\n"

    # Add type filter
    if entity_types:
        types_str = ", ".join(f"'{t}'" for t in entity_types)
        query += f"WHERE e.type IN [{types_str}]\n"

    # Add search filter
    if search_term:
        search_condition = f"toLower(e.name) CONTAINS toLower('{search_term}')"
        if "WHERE" in query:
            query += f"AND {search_condition}\n"
        else:
            query += f"WHERE {search_condition}\n"

    # Count relationships
    query += """
WITH e, COUNT { (e)-[]->(other) } + COUNT { (e)<-[]-(other) } as rel_count
"""

    # Add minimum relationships filter
    if min_relationships > 0:
        query += f"WHERE rel_count >= {min_relationships}\n"

    # Return with limit
    query += f"""
RETURN e.id as id,
       e.name as name,
       e.type as type,
       rel_count as relationship_count,
       e.canonical_name as summary
ORDER BY rel_count DESC
LIMIT {limit}
"""

    return query


def generate_relationship_cypher(entity_ids: list[str] | None = None, limit: int = 100) -> str:
    """
    Generate Cypher query for relationship retrieval.

    Args:
        entity_ids: Optional list of entity IDs to filter relationships
        limit: Maximum number of relationships to return

    Returns:
        Cypher query string
    """
    if entity_ids:
        ids_str = ", ".join(f"'{entity_id}'" for entity_id in entity_ids)
        query = f"""
MATCH (source:Entity)-[r]->(target:Entity)
WHERE source.id IN [{ids_str}] OR target.id IN [{ids_str}]
RETURN source.id as source_id,
       target.id as target_id,
       type(r) as relationship_type,
       properties(r) as summary
LIMIT {limit}
"""
    else:
        query = f"""
MATCH (source:Entity)-[r]->(target:Entity)
RETURN source.id as source_id,
       target.id as target_id,
       type(r) as relationship_type,
       properties(r) as summary
LIMIT {limit}
"""

    return query


def generate_top_entities_cypher(limit: int = 20) -> str:
    """
    Generate Cypher query for top connected entities.

    Args:
        limit: Maximum number of entities to return

    Returns:
        Cypher query string
    """
    return f"""
MATCH (e:Entity)
WITH e,
     COUNT {{ (e)-[]->(other) }} + COUNT {{ (e)<-[]-(other) }} as relationship_count
RETURN e.id as id,
       e.name as name,
       e.type as type,
       relationship_count,
       size(e.chunk_refs) as chunk_count,
       e.first_seen as created_at
ORDER BY relationship_count DESC
LIMIT {limit}
"""


def generate_entity_timeline_cypher(entity_id: str) -> str:
    """
    Generate Cypher query for entity temporal timeline.

    Returns related entities and their relationships as timeline events.
    Note: Does not query for Fact nodes since they may not exist in all schemas.

    Args:
        entity_id: Entity ID

    Returns:
        Cypher query string
    """
    return f"""
MATCH (e:Entity {{id: '{entity_id}'}})-[r]-(f:Entity)
WHERE type(r) IN ['RELATED_TO', 'MENTIONS', 'HAS_RELATIONSHIP']
WITH e, f, r,
     coalesce(f.name, f.canonical_name, 'Related entity') as description,
     coalesce(f.first_seen, r.created_at) as valid_from,
     null as valid_to,
     coalesce(f.first_seen, r.created_at) as created_at
RETURN description, valid_from, valid_to, created_at
ORDER BY created_at DESC
LIMIT 50
"""


def format_graph_for_plotly(
    entities: list[dict[str, Any]], relationships: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Format graph data for plotly network visualization.

    Args:
        entities: List of entity dictionaries with id, name, type
        relationships: List of relationship dictionaries with source_id, target_id, type

    Returns:
        Dictionary with formatted nodes and edges for plotly
    """
    # Create node mapping
    node_map = {entity["id"]: i for i, entity in enumerate(entities)}

    # Format nodes
    nodes = []
    for entity in entities:
        nodes.append(
            {
                "id": entity["id"],
                "name": entity["name"],
                "type": entity.get("type", "Unknown"),
                "relationship_count": entity.get("relationship_count", 0),
            }
        )

    # Format edges
    edges = []
    for rel in relationships:
        source_id = rel["source_id"]
        target_id = rel["target_id"]

        # Only include edge if both nodes exist
        if source_id in node_map and target_id in node_map:
            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "type": rel.get("relationship_type", "RELATED_TO"),
                    "summary": rel.get("summary", ""),
                }
            )

    return {"nodes": nodes, "edges": edges}


def aggregate_time_series(stats: list[dict[str, Any]], time_window: str = "7d") -> pd.DataFrame:
    """
    Aggregate metrics over time window.

    Args:
        stats: List of statistics with timestamps
        time_window: Time window (24h, 7d, 30d)

    Returns:
        DataFrame with aggregated time series data
    """
    if not stats:
        # Return empty DataFrame with expected structure
        return pd.DataFrame(columns=["timestamp", "search_count", "avg_latency_ms"])

    # Convert to DataFrame
    df = pd.DataFrame(stats)

    # Ensure timestamp column exists and is datetime
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.Timestamp.now()
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Filter by time window
    now = pd.Timestamp.now()
    if time_window == "24h":
        cutoff = now - timedelta(hours=24)
    elif time_window == "7d":
        cutoff = now - timedelta(days=7)
    elif time_window == "30d":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = now - timedelta(days=7)  # default to 7d

    df = df[df["timestamp"] >= cutoff]

    # Aggregate by hour for 24h, by day for longer periods
    if time_window == "24h":
        df["period"] = df["timestamp"].dt.floor("H")
    else:
        df["period"] = df["timestamp"].dt.floor("D")

    # Group and aggregate
    aggregated = (
        df.groupby("period")
        .agg(
            {
                "search_count": "sum" if "search_count" in df.columns else "count",
                "avg_latency_ms": "mean",
            }
        )
        .reset_index()
    )

    aggregated.rename(columns={"period": "timestamp"}, inplace=True)

    return aggregated


def export_metrics_to_csv(metrics: dict[str, Any], filename: str) -> None:
    """
    Export dashboard metrics to CSV file.

    Args:
        metrics: Dictionary of metrics to export
        filename: Output CSV filename
    """
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow(["Metric", "Value"])

        # Write metrics
        for key, value in metrics.items():
            if isinstance(value, (dict, list)):
                # For complex types, convert to JSON string
                writer.writerow([key, json.dumps(value)])
            else:
                writer.writerow([key, value])


def export_metrics_to_json(metrics: dict[str, Any], filename: str) -> None:
    """
    Export dashboard metrics to JSON file.

    Args:
        metrics: Dictionary of metrics to export
        filename: Output JSON filename
    """
    with open(filename, "w") as jsonfile:
        json.dump(metrics, jsonfile, indent=2, default=str)


def format_entity_for_display(entity: dict[str, Any]) -> dict[str, Any]:
    """
    Format entity data for display in UI.

    Args:
        entity: Raw entity dictionary

    Returns:
        Formatted entity dictionary
    """
    return {
        "name": entity.get("name", "Unknown"),
        "type": entity.get("type", "Unknown"),
        "relationship_count": entity.get("relationship_count", 0),
        "chunk_count": entity.get("chunk_count", 0),
        "confidence": entity.get("confidence", 0.0),
    }


def calculate_graph_statistics(
    entities: list[dict[str, Any]], relationships: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Calculate basic graph statistics.

    Args:
        entities: List of entities
        relationships: List of relationships

    Returns:
        Dictionary with graph statistics
    """
    entity_types = {}
    for entity in entities:
        entity_type = entity.get("type", "Unknown")
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

    relationship_types = {}
    for rel in relationships:
        rel_type = rel.get("relationship_type", "RELATED_TO")
        relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1

    return {
        "total_entities": len(entities),
        "total_relationships": len(relationships),
        "entity_types": entity_types,
        "relationship_types": relationship_types,
        "avg_relationships_per_entity": (len(relationships) / len(entities) if entities else 0),
    }


def create_pyvis_graph(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    height: str = "700px",
    width: str = "100%",
    layout: str = "force_directed",
) -> Network:
    """
    Create an interactive pyvis network graph from entities and relationships.

    This creates a Neo4j-style interactive graph where nodes can be dragged,
    the graph can be panned and zoomed, and physics simulations create natural layouts.

    Args:
        entities: List of entity dictionaries with id, name, type, relationship_count
        relationships: List of relationship dictionaries with source_id, target_id, type
        height: Height of the visualization (CSS format, e.g., "700px")
        width: Width of the visualization (CSS format, e.g., "100%")
        layout: Layout algorithm - "force_directed", "hierarchical", or "circular"

    Returns:
        Network: Configured pyvis Network object ready for rendering
    """
    # Define Neo4j-inspired color palette (lowercase keys to match DB)
    entity_type_colors = {
        "person": "#4C8EDA",  # Blue
        "company": "#FF6B6B",  # Coral Red
        "organization": "#57C7E3",  # Cyan
        "location": "#FFC454",  # Yellow
        "event": "#F16667",  # Red
        "technology": "#8DCC93",  # Green
        "product": "#A78BFA",  # Purple
        "concept": "#D9A5B3",  # Pink
    }
    default_color = "#A5ABB6"  # Gray for unknown types

    # Initialize pyvis network with optimized settings
    net = Network(
        height=height,
        width=width,
        bgcolor="#F8F9FA",
        font_color="#2C3E50",
        notebook=False,  # Not in Jupyter
        cdn_resources="remote",  # Use CDN for libraries
    )

    # Configure physics for natural, Neo4j-like behavior
    if layout == "force_directed":
        net.set_options(
            """
        {
            "physics": {
                "enabled": true,
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 200,
                    "springConstant": 0.08,
                    "damping": 0.4,
                    "avoidOverlap": 0.5
                },
                "maxVelocity": 50,
                "minVelocity": 0.1,
                "solver": "forceAtlas2Based",
                "timestep": 0.35,
                "stabilization": {
                    "enabled": true,
                    "iterations": 100,
                    "updateInterval": 25
                }
            },
            "interaction": {
                "dragNodes": true,
                "dragView": true,
                "zoomView": true,
                "hover": true,
                "navigationButtons": true,
                "keyboard": {
                    "enabled": true
                }
            },
            "nodes": {
                "borderWidth": 2,
                "borderWidthSelected": 4,
                "font": {
                    "size": 14,
                    "face": "arial"
                }
            },
            "edges": {
                "color": {
                    "color": "rgba(125, 125, 125, 0.3)",
                    "highlight": "rgba(125, 125, 125, 0.7)",
                    "hover": "rgba(125, 125, 125, 0.5)"
                },
                "smooth": {
                    "enabled": true,
                    "type": "continuous"
                }
            }
        }
        """
        )
    elif layout == "hierarchical":
        net.set_options(
            """
        {
            "layout": {
                "hierarchical": {
                    "enabled": true,
                    "direction": "UD",
                    "sortMethod": "directed"
                }
            },
            "physics": {
                "enabled": false
            },
            "interaction": {
                "dragNodes": true,
                "dragView": true,
                "zoomView": true,
                "hover": true,
                "navigationButtons": true
            }
        }
        """
        )
    else:  # circular or default
        net.toggle_physics(enabled=True)

    # Add nodes with proper styling and track added node IDs
    added_node_ids = set()
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue

        name = entity.get("name", "Unknown")
        entity_type = str(entity.get("type", "unknown")).lower()
        relationship_count = entity.get("relationship_count", 0)

        # Get color based on entity type
        color = entity_type_colors.get(entity_type, default_color)

        # Scale node size based on connection count (15-50px range)
        size = max(15, min(50, 15 + relationship_count * 2))

        # Create rich hover tooltip (using newlines instead of HTML for pyvis)
        title = f"{name}\nType: {entity_type.capitalize()}\nConnections: {relationship_count}\nDrag to reposition"

        # Add node to network
        net.add_node(
            entity_id,
            label=name[:20],  # Truncate long names
            title=title,
            color=color,
            size=size,
            borderWidth=2,
            borderWidthSelected=4,
            font={"size": 12, "color": "#2C3E50"},
        )
        added_node_ids.add(entity_id)

    # Add edges (relationships) - only for nodes that were actually added
    edges_added = 0
    edges_skipped = 0
    for rel in relationships:
        source_id = rel.get("source_id")
        target_id = rel.get("target_id")
        rel_type = rel.get("relationship_type", "RELATED_TO")

        # Only add edge if both nodes exist in the graph
        if source_id and target_id and source_id in added_node_ids and target_id in added_node_ids:
            # Create hover tooltip for edge
            edge_title = f"Relationship: {rel_type}"

            net.add_edge(
                source_id,
                target_id,
                title=edge_title,
                color="rgba(125, 125, 125, 0.3)",
                width=1.5,
            )
            edges_added += 1
        else:
            edges_skipped += 1

    # Log statistics for debugging
    if edges_skipped > 0:
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"Graph created: {len(added_node_ids)} nodes, {edges_added} edges added, "
            f"{edges_skipped} edges skipped (missing nodes)"
        )

    return net
