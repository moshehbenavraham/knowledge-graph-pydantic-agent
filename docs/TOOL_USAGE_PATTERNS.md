# Tool Usage Patterns

This guide demonstrates effective patterns for using the various tools available in the Luminari AI Agent system.

## Table of Contents

- [Tool Overview](#tool-overview)
- [Single Tool Patterns](#single-tool-patterns)
- [Multi-Tool Workflows](#multi-tool-workflows)
- [Advanced Patterns](#advanced-patterns)
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

## Conclusion

Effective tool usage in the Luminari AI Agent system requires:

1. **Understanding each tool's strengths and limitations**
2. **Combining tools strategically for comprehensive analysis**
3. **Following proven patterns for common use cases**
4. **Iterating and refining based on results**
5. **Validating findings through multiple approaches**

By following these patterns and best practices, you can maximize the effectiveness of your interactions with the AI agent system and achieve more accurate, comprehensive, and actionable results.
