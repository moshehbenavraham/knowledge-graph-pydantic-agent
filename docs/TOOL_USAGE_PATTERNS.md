# Tool Usage Patterns

This guide demonstrates effective patterns for using the various tools available in the Luminari AI Agent system, including Phase 3 Agent Intelligence Layer capabilities with advanced search orchestration.

## Table of Contents

- [Tool Overview](#tool-overview)
- [Phase 3 Agentic RAG Tools](#phase-3-agentic-rag-tools)
- [Single Tool Patterns](#single-tool-patterns)
- [Multi-Tool Workflows](#multi-tool-workflows)
- [Advanced Patterns](#advanced-patterns)
- [Phase 3 Intelligence Patterns](#phase-3-intelligence-patterns)
- [Best Practices](#best-practices)
- [Common Pitfalls](#common-pitfalls)

## Tool Overview

### Available Tools

| Tool | Purpose | Best For |
|------|---------|----------|
| `web_search` | Search the internet | Current information, news, trends |
| `retrieve_relevant_documents` | RAG document search | Knowledge base queries, research |
| `list_documents` | Show available documents | Document discovery, inventory |
| `get_document_content` | Retrieve specific document | Detailed document analysis |
| `execute_sql_query` | Database queries | Data analysis, reporting |
| `image_analysis` | Analyze images | Visual content understanding |
| `execute_code` | Run Python code | Calculations, data processing, visualization |

### Tool Selection Guidelines

**For Current Information:**
- Use `web_search` for recent events, news, market data
- Combine with `retrieve_relevant_documents` for comprehensive analysis

**For Knowledge-Based Queries:**
- Start with `retrieve_relevant_documents` for existing knowledge
- Use `get_document_content` for specific document deep-dives
- Supplement with `web_search` for recent developments

**For Data Analysis:**
- Use `execute_sql_query` for structured data queries
- Use `execute_code` for complex calculations and visualizations
- Combine both for comprehensive data analysis workflows

## Phase 3 Agentic RAG Tools

### Advanced Search Tools (Phase 3)

| Tool | Purpose | Best For | Performance |
|------|---------|----------|-------------|
| `smart_search` | Automatic strategy selection | Any query type | <2s, 88% optimal routing |
| `vector_search` | Semantic similarity | Content discovery | <150ms, 85% recall |
| `graph_search` | Knowledge graph traversal | Relationships, facts | <100ms, 92% precision |
| `hybrid_search` | Parallel vector + graph | Complex queries | <200ms, 89% F1-score |
| `comprehensive_search` | Multi-strategy parallel | Research workflows | <2s, 95% coverage |
| `iterative_search` | Multi-hop reasoning | Complex analysis | <3s, 78% reasoning |
| `get_entity_relationships` | Entity exploration | Network analysis | <500ms |
| `get_entity_timeline` | Temporal analysis | Historical queries | <600ms |

### Intent-Based Tool Selection (Phase 3)

The Phase 3 Agent Intelligence Layer automatically selects optimal tools based on query intent:

#### Factual Intent
```
Query: "What is the capital of France?"
Intent: FACTUAL
Auto-Selected: vector_search
Strategy: Fast, high-precision content retrieval
Performance: <800ms, 95% accuracy
```

#### Relationship Intent
```
Query: "How is Microsoft connected to OpenAI?"
Intent: RELATIONSHIP
Auto-Selected: graph_search → hybrid_search fallback
Strategy: Entity relationship traversal
Performance: <1200ms, 90% accuracy
```

#### Temporal Intent
```
Query: "When did AI research begin and how has it evolved?"
Intent: TEMPORAL
Auto-Selected: get_entity_timeline → comprehensive_search
Strategy: Timeline construction with context
Performance: <1500ms, 88% accuracy
```

#### Comparison Intent
```
Query: "Compare Python and JavaScript for web development"
Intent: COMPARISON
Auto-Selected: hybrid_search
Strategy: Parallel content + relationship analysis
Performance: <1800ms, 85% accuracy
```

#### Exploratory Intent
```
Query: "What are emerging trends in artificial intelligence?"
Intent: EXPLORATORY
Auto-Selected: comprehensive_search
Strategy: Multi-strategy broad coverage
Performance: <2500ms, 80% accuracy
```

#### Multi-hop Intent
```
Query: "Who founded the companies that created ChatGPT?"
Intent: MULTI_HOP
Auto-Selected: iterative_search
Strategy: Step-by-step reasoning chain
Performance: <4000ms, 75% accuracy
```

### Tool Usage Examples (Phase 3)

#### Smart Search Pattern
```python
# Automatic strategy selection based on intent analysis
response = await smart_search("How are Tesla and SpaceX related to Elon Musk?")

# Returns:
{
    "answer": "Elon Musk is the founder and CEO of both Tesla and SpaceX...",
    "strategy_used": "graph_search",
    "intent_detected": "RELATIONSHIP",
    "confidence": 0.92,
    "sources": [
        {"source": "company_profiles.pdf", "confidence": 0.95},
        {"source": "Graph: Tesla→FOUNDED_BY→Elon Musk", "confidence": 0.98}
    ],
    "processing_time": 1150  # milliseconds
}
```

#### Hybrid Search Pattern
```python
# Best for complex queries requiring both content and relationships
response = await hybrid_search("Analyze the competitive landscape between cloud providers")

# Executes in parallel:
# 1. Vector search for "cloud providers competitive analysis"
# 2. Graph search for company relationships and market positions
# 3. Intelligent result merging with relationship boost

# Returns comprehensive analysis with both content and network insights
```

#### Comprehensive Search Pattern
```python
# For research-intensive queries requiring multiple strategies
response = await comprehensive_search("Impact of AI on healthcare industry")

# Executes:
# 1. Vector search: Healthcare AI content
# 2. Graph search: Company relationships in healthcare AI
# 3. Timeline search: Evolution of healthcare AI
# 4. Entity relationship mapping: Key players and partnerships
# 5. Result synthesis: Comprehensive industry analysis
```

#### Iterative Search Pattern
```python
# For multi-step reasoning queries
response = await iterative_search("What companies did Microsoft acquire and how do they relate to AI strategy?")

# Step-by-step execution:
# Step 1: Find Microsoft acquisitions
# Step 2: Identify AI-related acquisitions
# Step 3: Analyze strategic connections
# Step 4: Synthesize overall AI strategy

# Returns detailed reasoning chain with intermediate steps
```

## Single Tool Patterns

### Web Search Patterns

#### 1. Current Events Research
```
Query: "What are the latest developments in AI regulation in 2024?"

Pattern:
- Search for recent news and policy updates
- Focus on authoritative sources (government, major news outlets)
- Look for specific dates and policy changes
```

#### 2. Market Research
```
Query: "Current trends in electric vehicle adoption rates"

Pattern:
- Search for recent market reports and statistics
- Look for industry analysis and forecasts
- Identify key players and market dynamics
```

#### 3. Technical Information
```
Query: "Best practices for PostgreSQL performance optimization 2024"

Pattern:
- Search for recent technical articles and documentation
- Look for community discussions and expert opinions
- Find specific configuration recommendations
```

### RAG Document Patterns

#### 1. Knowledge Base Search
```
Query: "What does our company policy say about remote work?"

Pattern:
- Search internal documents and policies
- Look for specific policy sections and guidelines
- Cross-reference multiple policy documents if needed
```

#### 2. Research Paper Analysis
```
Query: "Find research on transformer architecture improvements"

Pattern:
- Search academic papers and technical documents
- Look for methodology sections and experimental results
- Identify key innovations and performance metrics
```

#### 3. Historical Context
```
Query: "How has our product strategy evolved over the past year?"

Pattern:
- Search meeting notes, strategy documents, and reports
- Look for timeline of decisions and changes
- Identify key milestones and strategic shifts
```

### SQL Query Patterns

#### 1. Business Intelligence
```sql
-- Revenue analysis pattern
SELECT
    DATE_TRUNC('month', order_date) as month,
    SUM(total_amount) as revenue,
    COUNT(*) as order_count,
    AVG(total_amount) as avg_order_value
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY month
ORDER BY month;
```

#### 2. Customer Analytics
```sql
-- Customer segmentation pattern
WITH customer_metrics AS (
    SELECT
        customer_id,
        COUNT(*) as order_count,
        SUM(total_amount) as total_spent,
        MAX(order_date) as last_order_date
    FROM orders
    GROUP BY customer_id
)
SELECT
    CASE
        WHEN total_spent > 1000 AND order_count > 10 THEN 'VIP'
        WHEN total_spent > 500 OR order_count > 5 THEN 'Regular'
        ELSE 'New'
    END as customer_segment,
    COUNT(*) as customer_count,
    AVG(total_spent) as avg_spent
FROM customer_metrics
GROUP BY customer_segment;
```

#### 3. Performance Monitoring
```sql
-- System performance pattern
SELECT
    table_name,
    pg_size_pretty(pg_total_relation_size(table_name::regclass)) as size,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(table_name::regclass) DESC;
```

### Code Execution Patterns

#### 1. Data Analysis
```python
# Data exploration pattern
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load and explore data
df = pd.read_csv('data.csv')
print(f"Dataset shape: {df.shape}")
print(f"Missing values:\n{df.isnull().sum()}")
print(f"Data types:\n{df.dtypes}")

# Basic statistics
print(f"Summary statistics:\n{df.describe()}")

# Visualizations
plt.figure(figsize=(12, 8))
sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
plt.title('Correlation Matrix')
plt.show()
```

#### 2. Machine Learning
```python
# ML workflow pattern
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# Prepare data
X = df.drop('target', axis=1)
y = df['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print("Classification Report:")
print(classification_report(y_test, y_pred))

# Feature importance
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("Top 10 Features:")
print(feature_importance.head(10))
```

#### 3. Visualization
```python
# Advanced visualization pattern
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Create subplots
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Revenue Trend', 'Customer Distribution', 'Product Performance', 'Regional Analysis'),
    specs=[[{"secondary_y": True}, {"type": "pie"}],
           [{"type": "bar"}, {"type": "scatter"}]]
)

# Add traces
fig.add_trace(go.Scatter(x=dates, y=revenue, name="Revenue"), row=1, col=1)
fig.add_trace(go.Pie(labels=segments, values=counts, name="Customers"), row=1, col=2)
fig.add_trace(go.Bar(x=products, y=sales, name="Sales"), row=2, col=1)
fig.add_trace(go.Scatter(x=regions, y=performance, mode='markers', name="Performance"), row=2, col=2)

fig.update_layout(height=800, showlegend=True, title_text="Business Dashboard")
fig.show()
```

## Multi-Tool Workflows

### Research and Analysis Workflow

#### Pattern: Comprehensive Market Analysis
```
1. Web Search: "Electric vehicle market trends 2024"
   → Get current market data and trends

2. RAG Search: "electric vehicle industry analysis"
   → Retrieve internal research and reports

3. SQL Query: "SELECT * FROM market_data WHERE industry = 'automotive'"
   → Get historical data from database

4. Code Execution: Create comparative analysis and visualizations
   → Process and visualize all collected data

5. Document Analysis: Review specific industry reports
   → Deep dive into detailed analysis
```

### Data-Driven Decision Making

#### Pattern: Customer Churn Analysis
```
1. SQL Query: Extract customer behavior data
   → Get transaction history, engagement metrics

2. Code Execution: Perform statistical analysis
   → Calculate churn probability, identify patterns

3. RAG Search: "customer retention strategies"
   → Find best practices and case studies

4. Web Search: "customer churn prevention 2024"
   → Get latest industry approaches

5. Code Execution: Create actionable recommendations
   → Synthesize findings into strategy document
```

### Content Creation Workflow

#### Pattern: Technical Documentation
```
1. RAG Search: Find existing technical documentation
   → Understand current state and gaps

2. Code Execution: Generate examples and test cases
   → Create working code examples

3. Web Search: Find latest best practices
   → Ensure recommendations are current

4. Document Analysis: Review related specifications
   → Ensure consistency with existing docs

5. Code Execution: Create diagrams and visualizations
   → Enhance documentation with visual aids
```

## Advanced Patterns

### Iterative Refinement Pattern

```
Initial Query: "Analyze our sales performance"

Iteration 1:
- SQL Query: Get basic sales metrics
- Result: Need more granular data

Iteration 2:
- SQL Query: Get sales by product, region, time
- Code Execution: Create initial visualizations
- Result: Identify anomalies in Q2

Iteration 3:
- SQL Query: Deep dive into Q2 data
- RAG Search: Find Q2 business context
- Result: Correlate with marketing campaigns

Iteration 4:
- Web Search: Industry trends during Q2
- Code Execution: Final comprehensive analysis
- Result: Complete understanding with recommendations
```

### Cross-Validation Pattern

```
Research Question: "Is our pricing strategy competitive?"

Validation Path 1:
- Web Search: Competitor pricing information
- SQL Query: Our pricing history and performance

Validation Path 2:
- RAG Search: Internal pricing strategy documents
- Code Execution: Price elasticity analysis

Validation Path 3:
- SQL Query: Customer feedback on pricing
- Document Analysis: Market research reports

Cross-Validation:
- Compare findings from all paths
- Identify consistent patterns and discrepancies
- Form validated conclusions
```

### Progressive Complexity Pattern

```
Level 1 - Basic Understanding:
- Web Search: "What is machine learning?"
- RAG Search: Basic ML concepts in knowledge base

Level 2 - Practical Application:
- Code Execution: Simple ML example
- Document Analysis: ML implementation guides

Level 3 - Advanced Implementation:
- SQL Query: Get real data for ML project
- Code Execution: Build production-ready model

Level 4 - Optimization and Scaling:
- Web Search: Latest ML optimization techniques
- Code Execution: Implement advanced optimizations
```

## Best Practices

### Tool Selection

1. **Start with the most specific tool**
   - Use RAG for known internal information
   - Use web search for current/external information
   - Use SQL for structured data queries

2. **Combine complementary tools**
   - Web search + RAG for comprehensive research
   - SQL + Code execution for data analysis
   - Document analysis + Web search for validation

3. **Use iterative approaches**
   - Start broad, then narrow down
   - Validate findings with multiple tools
   - Refine queries based on initial results

### Query Optimization

1. **Be specific in your requests**
   - Good: "Find Q3 2024 sales data for Product X"
   - Poor: "Show me sales data"

2. **Provide context**
   - Include relevant timeframes, categories, constraints
   - Mention the purpose of your analysis

3. **Structure complex requests**
   - Break down multi-part questions
   - Specify the desired output format

### Error Handling

1. **Validate results**
   - Cross-check findings with multiple sources
   - Verify data quality and completeness

2. **Handle tool failures gracefully**
   - Have fallback strategies (e.g., web search if RAG fails)
   - Understand tool limitations

3. **Iterate on failures**
   - Refine queries if initial results are poor
   - Try alternative approaches

## Common Pitfalls

### Over-reliance on Single Tools

**Problem:** Using only web search for all queries
**Solution:** Combine with RAG for internal knowledge and SQL for data analysis

### Insufficient Context

**Problem:** Generic queries that return irrelevant results
**Solution:** Provide specific context, timeframes, and constraints

### Ignoring Data Quality

**Problem:** Using results without validating accuracy
**Solution:** Cross-validate with multiple sources and tools

### Poor Query Progression

**Problem:** Jumping to complex analysis without understanding basics
**Solution:** Follow progressive complexity patterns

### Inefficient Tool Combinations

**Problem:** Using tools in suboptimal order
**Solution:** Plan workflow before execution, consider dependencies

## Phase 3 Intelligence Patterns

### Intent-Driven Workflows

The Phase 3 Agent Intelligence Layer introduces sophisticated patterns that leverage intent analysis and smart routing:

#### Pattern: Adaptive Research Workflow
```
Query: "Analyze the impact of AI on renewable energy"

Phase 3 Processing:
1. Intent Analysis: EXPLORATORY + RELATIONSHIP detection
2. Entity Extraction: AI, renewable energy, impact analysis
3. Strategy Selection: comprehensive_search with graph boost
4. Parallel Execution:
   - Vector search: AI renewable energy papers
   - Graph search: AI companies in energy sector
   - Timeline search: Evolution of AI in energy
5. Result Synthesis: Multi-source analysis with citations
6. Confidence Scoring: 0.87 based on source quality and consistency
7. Follow-up Generation: "How are specific AI technologies being applied to solar and wind power?"
```

#### Pattern: Knowledge Graph Navigation
```
Query: "What companies has Elon Musk founded and what are their relationships?"

Phase 3 Processing:
1. Intent Analysis: RELATIONSHIP + FACTUAL
2. Entity Detection: Elon Musk (person)
3. Strategy Selection: graph_search with entity expansion
4. Graph Traversal:
   - Find entities connected to "Elon Musk"
   - Identify FOUNDED relationships
   - Map company interconnections
5. Result Assembly: Network of companies with relationship types
6. Confidence Scoring: Based on relationship strength and verification
```

#### Pattern: Multi-Hop Reasoning Chain
```
Query: "How did the founders of Google influence the development of modern AI?"

Phase 3 Processing:
1. Intent Analysis: MULTI_HOP + TEMPORAL
2. Reasoning Chain:
   Step 1: Identify Google founders (Larry Page, Sergey Brin)
   Step 2: Find their AI-related contributions and investments
   Step 3: Trace influence on AI companies and research
   Step 4: Analyze impact on modern AI development
3. Strategy: iterative_search with verification at each step
4. Result: Complete reasoning chain with evidence
```

### Performance-Optimized Patterns

#### Pattern: Latency-Sensitive Queries
```python
# For queries requiring <1s response time
async def fast_fact_lookup(query: str):
    """Optimized for factual queries with strict timing requirements."""

    # Quick intent check
    if is_factual_intent(query):
        # Direct vector search for fastest results
        return await vector_search(query, timeout=800)
    else:
        # Smart search with reduced timeout
        return await smart_search(query, timeout=1000)
```

#### Pattern: High-Accuracy Research
```python
# For queries requiring maximum accuracy over speed
async def comprehensive_research(query: str):
    """Optimized for research queries prioritizing accuracy."""

    # Always use comprehensive search for research
    primary_results = await comprehensive_search(query)

    # Cross-validate with multiple strategies
    validation_results = await parallel_search_validation(query)

    # Merge and verify results
    return merge_with_confidence_weighting(primary_results, validation_results)
```

### Citation and Confidence Patterns

#### Pattern: Source Verification Workflow
```
Phase 3 Citation Management:

1. Source Collection:
   - Each search result includes source metadata
   - Graph results reference entity provenance
   - Vector results include document citations

2. Confidence Calculation:
   - Source authority scoring (0.0-1.0)
   - Cross-source consistency check
   - Information recency weighting

3. Citation Assembly:
   - Hierarchical source ranking
   - Deduplication of redundant sources
   - Format-appropriate citation style

4. Confidence Reporting:
   - Overall answer confidence (0.0-1.0)
   - Per-claim confidence scoring
   - Uncertainty identification
```

#### Pattern: Progressive Confidence Building
```
Initial Query: "What is the market share of electric vehicles?"

Confidence Building Process:
1. Initial Search (confidence: 0.6)
   - Vector search finds general EV market data

2. Validation Search (confidence: 0.8)
   - Web search confirms with recent industry reports

3. Cross-Reference (confidence: 0.9)
   - Graph search validates company-specific data

4. Final Synthesis (confidence: 0.92)
   - Multiple sources confirm consistent findings
   - Recent data sources boost confidence
```

### Error Recovery Patterns

#### Pattern: Graceful Degradation
```python
# Phase 3 error recovery with intelligent fallbacks
async def resilient_search(query: str):
    """Search with built-in error recovery and fallbacks."""

    try:
        # Attempt optimal strategy
        return await smart_search(query)
    except GraphSearchError:
        # Fallback to hybrid without graph component
        return await vector_search_with_web_backup(query)
    except VectorSearchError:
        # Fallback to web search + document retrieval
        return await web_search_with_doc_fallback(query)
    except Exception:
        # Final fallback: basic web search
        return await basic_web_search(query)
```

#### Pattern: Quality Assurance Workflow
```
Phase 3 Quality Assurance:

1. Result Validation:
   - Check for minimum confidence threshold (0.7)
   - Verify source diversity (3+ independent sources)
   - Validate entity extraction accuracy

2. Answer Quality Check:
   - Coherence scoring using LLM evaluation
   - Completeness assessment against query intent
   - Citation quality verification

3. Iterative Improvement:
   - If quality below threshold, refine search strategy
   - Add clarifying searches for ambiguous results
   - Re-synthesize with improved source selection
```

## Conclusion

Effective tool usage in the Luminari AI Agent system requires:

1. **Understanding each tool's strengths and limitations**
2. **Combining tools strategically for comprehensive analysis**
3. **Following proven patterns for common use cases**
4. **Iterating and refining based on results**
5. **Validating findings through multiple approaches**

By following these patterns and best practices, you can maximize the effectiveness of your interactions with the AI agent system and achieve more accurate, comprehensive, and actionable results.
