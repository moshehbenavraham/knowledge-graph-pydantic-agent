# Deployment Guide

This guide covers deploying the Base Agent AI assistant in various environments.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Deployment](#local-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Production Considerations](#production-considerations)
- [Monitoring & Maintenance](#monitoring--maintenance)

## Prerequisites

### Required Services
- **Supabase Project**: Vector database for RAG (free tier available)
- **API Keys**:
  - Anthropic API key (for Claude models)
  - OpenAI API key (for embeddings)
  - Optional: Brave Search API key

### System Requirements
- Python 3.11+
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

## Local Deployment

### Quick Start

1. **Clone Repository**
```bash
git clone <repository-url>
cd base_agent
```

2. **Set Up Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Supabase**
- Create project at [supabase.com](https://supabase.com)
- Enable pgvector extension: Database → Extensions → Search "pgvector" → Enable
- Run SQL scripts in order:
  ```sql
  -- Run in SQL Editor
  sql/documents.sql
  sql/document_metadata.sql
  sql/document_rows.sql
  sql/execute_sql_rpc.sql
  ```

5. **Configure Environment**
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

# LLM Configuration (Choose one)
## Option 1: Anthropic Claude
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-api03-...
LLM_CHOICE=claude-sonnet-4-20250514

## Option 2: OpenAI GPT
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-...
LLM_CHOICE=gpt-5-mini

# Embeddings (Required)
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-proj-...
EMBEDDING_MODEL_CHOICE=text-embedding-3-small
```

6. **Run Application**
```bash
streamlit run src/ui/streamlit_app.py
# Or using make
make run-ui
```

Access at: **http://localhost:8501**

### Performance Optimization

For WSL2 users, copy project to WSL filesystem for 10x speed improvement:
```bash
cp -r /mnt/c/Projects/base_agent ~/base_agent
cd ~/base_agent
```

## Docker Deployment

### Standard Docker

1. **Build Image**
```bash
docker build -f docker/Dockerfile -t base-agent .
```

2. **Run Container**
```bash
docker run -d \
  --name base-agent \
  -p 8501:8501 \
  --env-file .env \
  base-agent
```

### Docker Compose (Recommended)

1. **Start Services**
```bash
docker-compose up -d
```

This starts:
- **App**: Port 8501 (Streamlit UI)
- **SearXNG**: Port 8080 (Web search)
- **Redis**: Port 6379 (Caching)

2. **Stop Services**
```bash
docker-compose down
```

### Using Makefile Commands
```bash
make docker-build   # Build images
make docker-run     # Start services
make docker-stop    # Stop services
```

## Cloud Deployment

### Option 1: Railway

1. **Install Railway CLI**
```bash
npm install -g @railway/cli
```

2. **Deploy**
```bash
railway login
railway init
railway up
```

3. **Add Environment Variables**
```bash
railway variables set SUPABASE_URL=your_url
railway variables set SUPABASE_SERVICE_KEY=your_key
railway variables set LLM_API_KEY=your_key
```

### Option 2: Render

1. **Create `render.yaml`**
```yaml
services:
  - type: web
    name: base-agent
    env: docker
    dockerfilePath: ./docker/Dockerfile
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: LLM_API_KEY
        sync: false
```

2. **Deploy via Render Dashboard**
- Connect GitHub repository
- Add environment variables
- Deploy

### Option 3: Google Cloud Run

1. **Build and Push Image**
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/base-agent
```

2. **Deploy to Cloud Run**
```bash
gcloud run deploy base-agent \
  --image gcr.io/PROJECT_ID/base-agent \
  --platform managed \
  --port 8501 \
  --set-env-vars "SUPABASE_URL=your_url,LLM_API_KEY=your_key"
```

### Option 4: AWS ECS

1. **Push to ECR**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI
docker tag base-agent:latest $ECR_URI/base-agent:latest
docker push $ECR_URI/base-agent:latest
```

2. **Create Task Definition**
```json
{
  "family": "base-agent",
  "containerDefinitions": [{
    "name": "base-agent",
    "image": "ECR_URI/base-agent:latest",
    "portMappings": [{
      "containerPort": 8501,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "SUPABASE_URL", "value": "your_url"},
      {"name": "LLM_API_KEY", "value": "your_key"}
    ]
  }]
}
```

## Production Considerations

### Security

1. **API Key Management**
   - Use secret management services (AWS Secrets Manager, Google Secret Manager)
   - Never commit `.env` files
   - Rotate keys regularly

2. **Network Security**
   - Use HTTPS/TLS certificates
   - Implement rate limiting
   - Set up firewall rules

3. **Authentication**
   - Add authentication layer (OAuth, JWT)
   - Implement user sessions
   - Set up role-based access

### Scaling

1. **Horizontal Scaling**
   - Use load balancer (nginx, ALB)
   - Deploy multiple instances
   - Implement session affinity

2. **Database Optimization**
   - Set up connection pooling
   - Implement caching (Redis)
   - Regular index maintenance

3. **Resource Limits**
```yaml
# docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Environment Variables

**Production Settings**:
```env
# Performance
MAX_CONCURRENT_REQUESTS=50
REQUEST_TIMEOUT=600
RATE_LIMIT_PER_MINUTE=100

# Logging
LOG_LEVEL=WARNING
LOG_FORMAT=json
ENABLE_STRUCTURED_LOGGING=true

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=8000
HEALTH_CHECK_INTERVAL=60

# Features
ENABLE_CODE_EXECUTION=false  # Disable in production
ENABLE_WEB_SEARCH=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true
ENABLE_RAG=true
```

## Monitoring & Maintenance

### Health Checks

1. **Endpoint**: `http://localhost:8501/_stcore/health`

2. **Custom Health Check**
```python
# src/utils/health.py
curl http://localhost:8000/health
```

### Logging

1. **View Logs**
```bash
# Docker
docker logs base-agent -f

# Systemd
journalctl -u base-agent -f

# PM2
pm2 logs base-agent
```

2. **Log Aggregation**
- Configure structured logging
- Use services like Datadog, New Relic, or ELK stack

### Metrics

1. **Prometheus Metrics**
```yaml
# Exposed at :8000/metrics
- luminari_request_count
- luminari_request_duration
- luminari_llm_tokens_total
- luminari_database_queries_total
```

2. **Grafana Dashboard**
- Import dashboard from `monitoring/grafana-dashboard.json`
- Configure Prometheus data source

### Backup & Recovery

1. **Database Backup**
```bash
# Supabase automatic backups
# Access via Dashboard → Settings → Backups
```

2. **Configuration Backup**
```bash
# Backup environment
cp .env .env.backup.$(date +%Y%m%d)

# Backup uploaded documents
tar -czf documents_backup.tar.gz data/
```

### Updates & Maintenance

1. **Update Dependencies**
```bash
pip install --upgrade -r requirements.txt
```

2. **Database Migrations**
```bash
# Check for new SQL scripts in sql/
# Run new migrations in order
```

3. **Zero-Downtime Deployment**
```bash
# Use blue-green deployment
docker-compose -f docker-compose.blue.yml up -d
# Test new version
# Switch traffic
docker-compose -f docker-compose.green.yml down
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Solution: Ensure running with `python -m streamlit run`

2. **Slow Performance (WSL2)**
   - Solution: Move to WSL native filesystem

3. **Memory Issues**
   - Solution: Disable unused features in `.env`
   - Increase Docker memory limits

4. **Connection Errors**
   - Verify API keys and URLs
   - Check firewall/proxy settings
   - Test with `curl` commands

### Debug Mode

Enable debug logging:
```env
DEBUG=true
LOG_LEVEL=DEBUG
DEVELOPMENT_MODE=true
```

### Support

- **Issues**: GitHub Issues
- **Documentation**: `/docs` directory
- **Community**: Discord/Slack channel

## Cost Optimization

### Estimated Monthly Costs

| Service | Free Tier | Paid Usage |
|---------|-----------|------------|
| Supabase | 500MB database | $25/month Pro |
| Anthropic Claude | N/A | ~$15/1M tokens |
| OpenAI Embeddings | N/A | ~$0.10/1M tokens |
| Hosting (Cloud Run) | 2M requests | ~$10-50/month |

### Cost Reduction Tips

1. Use Ollama for local LLMs (free)
2. Implement caching to reduce API calls
3. Use smaller models for non-critical tasks
4. Enable rate limiting
5. Monitor token usage

## Next Steps

1. Set up monitoring dashboard
2. Configure automated backups
3. Implement user authentication
4. Add custom domain with SSL
5. Set up CI/CD pipeline

---

For detailed configuration options, see [CONFIGURATION.md](./CONFIGURATION.md)
For troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
