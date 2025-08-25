# Usage Examples

This document provides comprehensive examples of how to use the Luminari AI Agent system effectively, including the advanced Agentic RAG capabilities with Phase 3 Agent Intelligence Layer.

## Table of Contents

- [Agentic RAG Examples (Phase 3)](#agentic-rag-examples-phase-3)
- [Basic Usage](#basic-usage)
- [Research Workflows](#research-workflows)
- [Document Analysis](#document-analysis)
- [Code Execution](#code-execution)
- [Data Analysis](#data-analysis)
- [Multi-Tool Workflows](#multi-tool-workflows)
- [Advanced Features](#advanced-features)

## Agentic RAG Examples (Phase 3)

The Phase 3 Agent Intelligence Layer provides advanced query understanding and intelligent search orchestration. Here are examples showcasing the 8 intent types and smart routing capabilities.

### Intent-Based Search Examples

#### 1. Factual Intent
**Query:** "What is the capital of France?"
**Intent Detected:** FACTUAL
**Strategy Selected:** Vector Search
**Response:** "The capital of France is Paris. [Confidence: 0.98] [Sources: geography_facts.pdf]"

#### 2. Relationship Intent  
**Query:** "How is Microsoft connected to OpenAI?"
**Intent Detected:** RELATIONSHIP
**Strategy Selected:** Graph Search
**Response:** 
```
Microsoft has several connections to OpenAI:

1. **Investment Partnership**: Microsoft invested $10 billion in OpenAI in 2023
2. **Technology Integration**: OpenAI's models are integrated into Microsoft products like Office 365
3. **Azure Partnership**: OpenAI runs its infrastructure on Microsoft Azure
4. **Strategic Alliance**: Long-term partnership for AI development

[Confidence: 0.92] [Sources: tech_partnerships.pdf, Graph: Microsoft→INVESTED_IN→OpenAI]
```

#### 3. Temporal Intent
**Query:** "When did the AI revolution begin and how has it evolved?"
**Intent Detected:** TEMPORAL  
**Strategy Selected:** Graph Search + Timeline
**Response:**
```
AI Revolution Timeline:

• 1956: Dartmouth Conference - Birth of AI as a field
• 1980s: Expert Systems boom
• 1997: Deep Blue defeats world chess champion
• 2012: AlexNet breakthrough in deep learning
• 2017: Transformer architecture introduced
• 2020: GPT-3 demonstrates large language model capabilities
• 2022: ChatGPT launches, bringing AI to mainstream
• 2023: GPT-4 and multimodal AI systems

[Confidence: 0.89] [Sources: ai_history.pdf, Timeline graph analysis]
```

#### 4. Comparison Intent
**Query:** "Compare Python and JavaScript for web development"
**Intent Detected:** COMPARISON
**Strategy Selected:** Hybrid Search
**Response:**
```
Python vs JavaScript for Web Development:

**Python:**
✓ Excellent for backend with Django/Flask
✓ Great data processing capabilities
✓ Clean, readable syntax
✗ Not native for frontend
✗ Slower execution than compiled languages

**JavaScript:**
✓ Full-stack capability (frontend + Node.js backend)
✓ Huge ecosystem and community
✓ Fast development cycle
✗ Type safety challenges (solved by TypeScript)
✗ Callback complexity

**Recommendation:** Use JavaScript for full-stack web apps, Python for data-heavy backend applications.

[Confidence: 0.85] [Sources: programming_guide.pdf, web_dev_best_practices.md]
```

#### 5. Exploratory Intent
**Query:** "What are the emerging trends in artificial intelligence?"
**Intent Detected:** EXPLORATORY
**Strategy Selected:** Comprehensive Search
**Response:**
```
Emerging AI Trends (2024):

🔬 **Technical Advances:**
- Multimodal AI (text, image, video, audio)
- Smaller, more efficient models (edge AI)
- Retrieval-Augmented Generation (RAG)
- Agent-based AI systems

🏢 **Industry Applications:**
- AI-powered drug discovery
- Autonomous vehicle improvements
- AI in cybersecurity
- Personalized education platforms

⚡ **Infrastructure:**
- Specialized AI chips (beyond GPUs)
- Federated learning systems
- AI model optimization techniques

[Confidence: 0.78] [Sources: Web search, ai_trends_2024.pdf, tech_reports/]
```

### Smart Search Tool Examples

#### Using `smart_search`
```python
# Automatically selects optimal strategy based on intent
query = "What companies has Microsoft acquired recently?"
result = await smart_search(query)

# Intent: FACTUAL + TEMPORAL
# Strategy Selected: Hybrid Search
# Combines vector search for "Microsoft acquisitions" with 
# graph search for recent acquisition relationships
```

#### Using `comprehensive_search`
```python
# For complex queries requiring multiple strategies
query = "Analyze the competitive landscape between cloud providers and their AI offerings"
result = await comprehensive_search(query)

# Executes:
# 1. Vector search for cloud provider information
# 2. Graph search for competitive relationships  
# 3. Timeline analysis for AI offering evolution
# 4. Entity relationship mapping
# 5. Intelligent result merging
```

#### Using `iterative_search`
```python
# For multi-hop reasoning queries
query = "Who are the key researchers behind transformer architecture and what companies do they work for now?"
result = await iterative_search(query)

# Step 1: Find transformer research papers
# Step 2: Extract researcher names
# Step 3: Find current company affiliations
# Step 4: Cross-reference and verify
```

### Advanced API Examples

#### Using the FastAPI Server
```bash
# Start the Agentic RAG API
python -m EXAMPLE_agentic-rag-knowledge-graph.agent.api

# Chat with intent analysis
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How are Tesla and SpaceX related to Elon Musk?",
    "session_id": "user123"
  }'

# Response includes:
# - Intent analysis results
# - Selected search strategy  
# - Confidence scores
# - Source citations
# - Follow-up questions
```

#### Direct Search API
```bash
# Vector search
curl "http://localhost:8000/search/vector?q=machine%20learning%20algorithms&limit=5"

# Graph search  
curl "http://localhost:8000/search/graph?q=Microsoft%20OpenAI%20relationship&limit=3"

# Hybrid search
curl "http://localhost:8000/search/hybrid?q=AI%20startup%20funding%20trends&limit=8"
```

#### Python SDK Usage
```python
from EXAMPLE_agentic_rag_knowledge_graph.agent import AgenticRAGAgent

# Initialize agent
agent = AgenticRAGAgent()

# Chat with full intelligence layer
response = await agent.chat(
    "What are the latest developments in quantum computing and who are the key players?"
)

print(f"Answer: {response.answer}")
print(f"Intent: {response.intent}")  
print(f"Strategy: {response.search_strategy}")
print(f"Confidence: {response.confidence}")
print(f"Sources: {response.sources}")
print(f"Follow-ups: {response.follow_up_questions}")
```

### Document Ingestion Examples

#### Batch Document Processing
```bash
# Ingest multiple documents with knowledge extraction
python -m EXAMPLE_agentic-rag-knowledge-graph.cli ingest \
  path/to/documents \
  --chunk-size 1000 \
  --extract-entities \
  --extract-relationships

# Output:
# Processed: 15 documents
# Created: 1,247 chunks  
# Extracted: 342 entities, 158 relationships, 89 temporal facts
# Storage: 18MB PostgreSQL, 85KB Neo4j (99.5% savings)
```

#### Real-time Processing
```python
# Stream processing for real-time updates
from EXAMPLE_agentic_rag_knowledge_graph.ingestion import IngestionPipeline

pipeline = IngestionPipeline()

# Process document with full knowledge extraction
result = await pipeline.ingest_document(
    content="Tesla announced a new AI chip for autonomous driving...",
    title="Tesla AI Chip Announcement",  
    source="tech_news_2024.pdf"
)

print(f"Entities: {result.entities_count}")
print(f"Facts: {result.facts_count}")  
print(f"Processing time: {result.processing_time}ms")
```

## Basic Usage

### Starting a Simple Conversation

```python
# Using the Streamlit UI
# 1. Start the application
streamlit run src/ui/streamlit_app.py

# 2. Navigate to http://localhost:8501
# 3. Type your question in the chat input
```

**Example Queries:**
- "What is machine learning?"
- "Explain the difference between Python and JavaScript"
- "How do I set up a virtual environment in Python?"

### Memory-Aware Conversations

The agent remembers your preferences and context across sessions:

```
User: I'm learning Python programming
Agent: Great! Python is an excellent language to start with...

[Later in the conversation]
User: Show me some examples
Agent: Here are some Python examples since you're learning Python...
```

## Research Workflows

### Academic Research

**Query:** "Find recent research papers on transformer architectures in NLP"

**What happens:**
1. Agent searches web for latest papers
2. Retrieves relevant documents from knowledge base
3. Synthesizes information from multiple sources
4. Provides citations and links

**Example Response:**
```
Based on recent research and documents in the knowledge base:

**Recent Developments:**
- Attention mechanisms have evolved beyond the original Transformer...
- New architectures like GPT-4 and Claude show improvements in...

**Key Papers:**
1. "Attention Is All You Need" - Foundational transformer paper
2. "BERT: Pre-training of Deep Bidirectional Transformers" - Bidirectional approach
3. Recent work on efficient transformers...

**Sources:**
- Web search: Latest arXiv papers from 2024
- Knowledge base: transformer_architectures.pdf, nlp_survey_2024.pdf
```

### Market Research

**Query:** "What are the current trends in AI startups and their funding?"

**Workflow:**
1. Web search for recent funding news
2. Query database for historical funding data
3. Analyze trends and provide insights

## Document Analysis

### Uploading and Analyzing Documents

1. **Upload Process:**
   ```bash
   # Place documents in the data directory
   cp your_document.pdf data/

   # Run RAG pipeline to process
   python -m src.rag_pipeline.pipeline --source local --interval 60
   ```

2. **Analysis Queries:**
   ```
   User: "Analyze the financial performance in the Q3 report"
   Agent: [Retrieves Q3_report.pdf] Based on the Q3 financial report...

   User: "What are the key risks mentioned in the document?"
   Agent: [Searches document content] The main risks identified include...
   ```

### Multi-Document Analysis

**Query:** "Compare the methodologies used in research_paper_1.pdf and research_paper_2.pdf"

**Process:**
1. Retrieves content from both documents
2. Identifies methodology sections
3. Compares approaches
4. Highlights similarities and differences

## Code Execution

### Data Analysis with Python

**Query:** "Analyze this dataset and create visualizations"

```python
# Agent executes:
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load sample data
data = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
    'sales': [1000, 1200, 1100, 1300, 1500],
    'costs': [800, 900, 850, 950, 1000]
})

# Calculate profit
data['profit'] = data['sales'] - data['costs']

# Create visualization
plt.figure(figsize=(10, 6))
plt.plot(data['month'], data['sales'], label='Sales', marker='o')
plt.plot(data['month'], data['costs'], label='Costs', marker='s')
plt.plot(data['month'], data['profit'], label='Profit', marker='^')
plt.legend()
plt.title('Monthly Financial Performance')
plt.show()

print("Summary Statistics:")
print(f"Average Sales: ${data['sales'].mean():.2f}")
print(f"Average Profit: ${data['profit'].mean():.2f}")
print(f"Profit Margin: {(data['profit'].mean()/data['sales'].mean()*100):.1f}%")
```

### Machine Learning Example

**Query:** "Build a simple linear regression model to predict house prices"

```python
# Agent executes:
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

# Generate sample data
np.random.seed(42)
n_samples = 1000

# Features: size, bedrooms, age
size = np.random.normal(2000, 500, n_samples)
bedrooms = np.random.poisson(3, n_samples)
age = np.random.uniform(0, 50, n_samples)

# Target: price (with some realistic relationships)
price = (size * 150 + bedrooms * 10000 - age * 1000 +
         np.random.normal(0, 20000, n_samples))

# Prepare data
X = np.column_stack([size, bedrooms, age])
y = price

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = LinearRegression()
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)

# Evaluate
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"Model Performance:")
print(f"R² Score: {r2:.3f}")
print(f"RMSE: ${np.sqrt(mse):,.2f}")
print(f"\nFeature Coefficients:")
print(f"Size ($/sqft): ${model.coef_[0]:.2f}")
print(f"Bedrooms: ${model.coef_[1]:,.2f}")
print(f"Age ($/year): ${model.coef_[2]:.2f}")
```

## Data Analysis

### SQL Queries for Business Intelligence

**Query:** "Show me the top 10 customers by revenue this year"

```sql
-- Agent executes:
SELECT
    customer_name,
    SUM(order_total) as total_revenue,
    COUNT(*) as order_count,
    AVG(order_total) as avg_order_value
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY customer_name
ORDER BY total_revenue DESC
LIMIT 10;
```

### Complex Analytics

**Query:** "Analyze customer churn patterns and identify at-risk customers"

```sql
-- Agent executes multiple queries:

-- 1. Calculate customer metrics
WITH customer_metrics AS (
    SELECT
        customer_id,
        COUNT(*) as total_orders,
        MAX(order_date) as last_order_date,
        AVG(order_total) as avg_order_value,
        EXTRACT(DAYS FROM CURRENT_DATE - MAX(order_date)) as days_since_last_order
    FROM orders
    GROUP BY customer_id
),

-- 2. Identify churn risk
churn_risk AS (
    SELECT *,
        CASE
            WHEN days_since_last_order > 90 THEN 'High Risk'
            WHEN days_since_last_order > 60 THEN 'Medium Risk'
            WHEN days_since_last_order > 30 THEN 'Low Risk'
            ELSE 'Active'
        END as churn_risk_level
    FROM customer_metrics
)

-- 3. Summary by risk level
SELECT
    churn_risk_level,
    COUNT(*) as customer_count,
    AVG(avg_order_value) as avg_customer_value,
    AVG(days_since_last_order) as avg_days_inactive
FROM churn_risk
GROUP BY churn_risk_level
ORDER BY
    CASE churn_risk_level
        WHEN 'High Risk' THEN 1
        WHEN 'Medium Risk' THEN 2
        WHEN 'Low Risk' THEN 3
        WHEN 'Active' THEN 4
    END;
```

## Multi-Tool Workflows

### Comprehensive Research Project

**Query:** "Research the impact of AI on job markets, analyze relevant data, and create a presentation"

**Workflow:**
1. **Web Search:** Latest news and studies on AI job impact
2. **Document Retrieval:** Academic papers from knowledge base
3. **Data Analysis:** Employment statistics and trends
4. **Code Execution:** Create visualizations and charts
5. **Synthesis:** Combine all information into coherent analysis

**Example Process:**
```
1. Web Search Results:
   - "AI could displace 40% of jobs in next decade" - Recent study
   - "New AI roles emerging faster than traditional jobs lost" - Industry report

2. Document Analysis:
   - Retrieved: ai_employment_study_2024.pdf, future_of_work_report.pdf
   - Key findings: Automation affects routine tasks most

3. Data Analysis:
   [SQL queries for employment data]
   [Python code for trend analysis and visualization]

4. Final Synthesis:
   Based on current research and data analysis, AI's impact on employment shows...
```

### Investment Research

**Query:** "Analyze Tesla's financial performance and compare with competitors"

**Multi-step Process:**
1. **Web Search:** Recent Tesla news and stock performance
2. **Database Query:** Historical financial data
3. **Document Analysis:** Annual reports and SEC filings
4. **Code Execution:** Financial ratio calculations and comparisons
5. **Visualization:** Charts and graphs for presentation

## Advanced Features

### Image Analysis

**Query:** "Analyze the chart in quarterly_report.png and extract key metrics"

**Process:**
1. Agent retrieves image from knowledge base
2. Uses vision model to analyze chart
3. Extracts numerical data and trends
4. Provides structured summary

### Memory-Driven Personalization

**Long-term Context:**
```
Session 1: User asks about Python web frameworks
Session 2: User asks about database integration
Session 3: User asks "How do I deploy my application?"

Agent Response: "Since you've been working with Python web frameworks and database integration, here are deployment options that work well with your stack..."
```

### Custom Workflows

**Query:** "Create a daily market analysis report"

**Automated Workflow:**
1. Fetch latest market data
2. Analyze key indicators
3. Compare with historical trends
4. Generate formatted report
5. Highlight significant changes

## Best Practices

### Effective Query Formulation

**Good Queries:**
- "Compare the performance of different machine learning algorithms for text classification"
- "Analyze the financial trends in our Q3 data and identify areas for cost reduction"
- "Find recent research on sustainable energy solutions and summarize key innovations"

**Less Effective Queries:**
- "Tell me about AI" (too broad)
- "Fix this" (lacks context)
- "What should I do?" (unclear objective)

### Leveraging Memory

- **Be specific about your role/context:** "I'm a data scientist working on customer segmentation"
- **Mention your preferences:** "I prefer Python over R for analysis"
- **Reference previous conversations:** "Building on our earlier discussion about neural networks..."

### Optimizing Performance

- **Use specific document references:** "According to the methodology in research_paper_1.pdf..."
- **Break complex requests into steps:** "First analyze the data, then create visualizations"
- **Provide context for code execution:** "Using the sales data from last quarter..."
