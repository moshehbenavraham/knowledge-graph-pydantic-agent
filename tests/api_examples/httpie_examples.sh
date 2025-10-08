#!/bin/bash
# HTTPie Examples for Agentic RAG API Testing

# Base URL configuration
BASE_URL="${API_URL:-http://localhost:8058}"

echo "=== HTTPie Examples for Agentic RAG API ==="
echo "Base URL: $BASE_URL"
echo ""

# Health and Status Checks
echo "1. Health Check:"
echo "http GET $BASE_URL/health"
echo ""

echo "2. API Status:"
echo "http GET $BASE_URL/api/v1/status"
echo ""

echo "3. Prometheus Metrics:"
echo "http GET $BASE_URL/metrics"
echo ""

# Chat Endpoints
echo "=== Chat Operations ==="
echo ""

echo "4. Simple Chat Message:"
echo 'http POST $BASE_URL/api/v1/chat message="Hello, how are you?" session_id="test-session"'
echo ""

echo "5. Chat with Tool Usage:"
echo 'http POST $BASE_URL/api/v1/chat message="Search for information about RAG systems" session_id="test-session" use_tools=true'
echo ""

echo "6. Streaming Chat:"
echo 'http --stream POST $BASE_URL/api/v1/chat/stream message="Explain vector databases" session_id="test-stream"'
echo ""

# Search Endpoints
echo "=== Search Operations ==="
echo ""

echo "7. Vector Search:"
echo 'http POST $BASE_URL/api/v1/search query="machine learning" search_type="vector" top_k=5'
echo ""

echo "8. Graph Search:"
echo 'http POST $BASE_URL/api/v1/search query="entity relationships" search_type="graph" max_depth=3'
echo ""

echo "9. Hybrid Search:"
echo 'http POST $BASE_URL/api/v1/search query="AI applications" search_type="hybrid" top_k=10'
echo ""

echo "10. Comprehensive Search:"
echo 'http POST $BASE_URL/api/v1/search/comprehensive query="deep learning transformers" include_metadata=true'
echo ""

# Memory Operations
echo "=== Memory Operations ==="
echo ""

echo "11. Store Memory:"
echo 'http POST $BASE_URL/api/v1/memory session_id="test-session" content="User prefers technical explanations"'
echo ""

echo "12. Retrieve Memory:"
echo 'http GET $BASE_URL/api/v1/memory/test-session'
echo ""

echo "13. Clear Memory:"
echo 'http DELETE $BASE_URL/api/v1/memory/test-session'
echo ""

# Document Operations
echo "=== Document Operations ==="
echo ""

echo "14. Upload Document:"
echo 'http --form POST $BASE_URL/api/v1/documents/upload file@document.pdf'
echo ""

echo "15. List Documents:"
echo 'http GET $BASE_URL/api/v1/documents'
echo ""

echo "16. Get Document by ID:"
echo 'http GET $BASE_URL/api/v1/documents/{document_id}'
echo ""

echo "17. Delete Document:"
echo 'http DELETE $BASE_URL/api/v1/documents/{document_id}'
echo ""

# Cache Operations
echo "=== Cache Operations ==="
echo ""

echo "18. Get Cache Stats:"
echo 'http GET $BASE_URL/api/v1/cache/stats'
echo ""

echo "19. Clear Cache:"
echo 'http POST $BASE_URL/api/v1/cache/clear'
echo ""

echo "20. Invalidate Cache Pattern:"
echo 'http POST $BASE_URL/api/v1/cache/invalidate pattern="search:*"'
echo ""

# Advanced Examples with Headers and Authentication
echo "=== Advanced Examples ==="
echo ""

echo "21. Authenticated Request:"
echo 'http POST $BASE_URL/api/v1/chat "Authorization: Bearer YOUR_API_KEY" message="Protected endpoint test"'
echo ""

echo "22. Custom Headers:"
echo 'http POST $BASE_URL/api/v1/chat "X-Request-ID: unique-id-123" "X-Client-Version: 1.0.0" message="Test with custom headers"'
echo ""

echo "23. JSON Response with Pretty Print:"
echo 'http --json --pretty=all POST $BASE_URL/api/v1/search query="test"'
echo ""

echo "24. Download Response to File:"
echo 'http --download POST $BASE_URL/api/v1/export/results query="all data" > results.json'
echo ""

echo "25. Timeout Configuration:"
echo 'http --timeout=30 POST $BASE_URL/api/v1/search/comprehensive query="complex search"'
echo ""

# Batch Operations
echo "=== Batch Operations ==="
echo ""

echo "26. Batch Search:"
cat << 'EOF'
http POST $BASE_URL/api/v1/batch/search queries:='[
  {"query": "machine learning", "search_type": "vector"},
  {"query": "neural networks", "search_type": "graph"},
  {"query": "deep learning", "search_type": "hybrid"}
]'
EOF
echo ""

echo "27. Batch Chat:"
cat << 'EOF'
http POST $BASE_URL/api/v1/batch/chat messages:='[
  {"message": "What is RAG?", "session_id": "session1"},
  {"message": "Explain vector search", "session_id": "session2"},
  {"message": "How do knowledge graphs work?", "session_id": "session3"}
]'
EOF
echo ""

# Performance Testing
echo "=== Performance Testing ==="
echo ""

echo "28. Load Test Endpoint:"
echo 'for i in {1..100}; do http --ignore-stdin POST $BASE_URL/api/v1/chat message="Test message $i" session_id="load-test-$i" & done'
echo ""

echo "29. Concurrent Requests:"
echo 'parallel -j 10 http POST $BASE_URL/api/v1/search query="test{}" ::: {1..10}'
echo ""

echo "30. Response Time Measurement:"
echo 'time http POST $BASE_URL/api/v1/search query="performance test"'
echo ""

# Debugging
echo "=== Debugging ==="
echo ""

echo "31. Verbose Output:"
echo 'http --verbose POST $BASE_URL/api/v1/chat message="Debug test"'
echo ""

echo "32. Show Headers Only:"
echo 'http --headers POST $BASE_URL/api/v1/chat message="Headers test"'
echo ""

echo "33. Follow Redirects:"
echo 'http --follow POST $BASE_URL/api/v1/chat message="Redirect test"'
echo ""

# Error Handling
echo "=== Error Handling Examples ==="
echo ""

echo "34. Handle 404:"
echo 'http GET $BASE_URL/api/v1/nonexistent || echo "Endpoint not found"'
echo ""

echo "35. Retry on Failure:"
echo 'for i in {1..3}; do http POST $BASE_URL/api/v1/chat message="Retry test" && break || sleep 2; done'
echo ""

echo "=== Usage Tips ==="
echo "- Use --json flag for JSON output"
echo "- Use --stream for streaming responses"
echo "- Use --session=NAME to maintain cookies"
echo "- Use @ to read from file: message=@request.json"
echo "- Use --print=HhBb to control output (H=request headers, h=response headers, B=request body, b=response body)"