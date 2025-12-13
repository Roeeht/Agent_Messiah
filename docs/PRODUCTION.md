# Production Deployment Guide

## Overview

Agent Messiah is now production-ready with:

- ✅ PostgreSQL database persistence
- ✅ Redis session management
- ✅ Structured JSON logging
- ✅ Health checks and monitoring
- ✅ Prometheus metrics
- ✅ Security features (API auth, webhook validation)
- ✅ Async job processing with Celery
- ✅ Docker containerization
- ✅ OpenAI GPT-4o-mini integration
- ✅ Twilio voice integration

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Twilio    │────▶│  FastAPI App │────▶│  PostgreSQL │
│   (Voice)   │     │              │     │  (Database) │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │  (Sessions) │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Celery    │
                    │  (Workers)  │
                    └─────────────┘
```

## Quick Start (Docker)

### 1. Prerequisites

- Docker and Docker Compose installed
- OpenAI API key
- Twilio account with phone number
- ngrok (for local development) or public domain

### 2. Setup

```bash
# Clone and navigate to project
cd Agent_Messiah

# Copy and configure environment
cp .env.docker.example .env.docker
# Edit .env.docker with your credentials

# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f app

# Run migrations
docker-compose exec app alembic upgrade head
```

### 3. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Readiness check (with dependencies)
curl http://localhost:8000/health/ready

# System info
curl http://localhost:8000/health/info

# Metrics
curl http://localhost:8000/metrics
```

## Manual Deployment

### 1. System Requirements

- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- 512MB RAM minimum, 2GB recommended
- Linux/macOS/Windows (with WSL)

### 2. Database Setup

#### PostgreSQL Installation (Ubuntu/Debian)

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE agent_messiah;
CREATE USER agent_messiah WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE agent_messiah TO agent_messiah;
\q
```

#### PostgreSQL Installation (macOS)

```bash
# Install via Homebrew
brew install postgresql@16
brew services start postgresql@16

# Create database
createdb agent_messiah
```

### 3. Redis Setup

#### Redis Installation (Ubuntu/Debian)

```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### Redis Installation (macOS)

```bash
brew install redis
brew services start redis
```

### 4. Application Setup

```bash
# Clone repository
git clone <your-repo>
cd Agent_Messiah

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your actual configuration

# Run database migrations
alembic upgrade head

# Start application
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start Celery worker (in separate terminal)
celery -A app.celery_tasks worker --loglevel=info
```

## Configuration

### Environment Variables

#### Required

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...  # Your OpenAI API key
AGENT_MODE=llm              # Use LLM-based conversations

# Twilio
TWILIO_ACCOUNT_SID=AC...    # Your Twilio Account SID
TWILIO_AUTH_TOKEN=...       # Your Twilio Auth Token
TWILIO_CALLER_ID=+1...      # Your Twilio phone number

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/agent_messiah

# Base URL (for Twilio webhooks)
BASE_URL=https://your-domain.com
```

#### Optional

```bash
# OpenAI
OPENAI_MODEL=gpt-4o-mini    # Model to use (default: gpt-4o-mini)

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_TTL=1800      # Session TTL in seconds (default: 30 min)

# Logging
DEBUG=False                 # Debug mode (default: False)
LOG_LEVEL=INFO             # Log level (DEBUG, INFO, WARNING, ERROR)

# Security
API_KEY=your_secret_key    # API key for protected endpoints
WEBHOOK_SECRET=...         # Webhook validation secret

# Language / voice
CALLER_LANGUAGE=he-IL
INTERNAL_LANGUAGE=en
ENABLE_TRANSLATION=True
TWILIO_TTS_VOICE=Google.he-IL-Standard-A
```

## Production Checklist

### Before Deployment

- [ ] Change default passwords
- [ ] Set strong `API_KEY` and `WEBHOOK_SECRET`
- [ ] Configure PostgreSQL with production settings
- [ ] Enable Redis persistence
- [ ] Set `DEBUG=False`
- [ ] Configure proper `BASE_URL` (public domain)
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up backup strategy for database
- [ ] Configure log rotation
- [ ] Set up monitoring and alerts

### Security Best Practices

1. **API Authentication**: Set `API_KEY` for protected endpoints
2. **Webhook Validation**: Configure `WEBHOOK_SECRET` and validate Twilio signatures
3. **HTTPS Only**: Use SSL/TLS certificates (Let's Encrypt recommended)
4. **Database Security**: Use strong passwords, enable SSL connections
5. **Redis Security**: Configure password, bind to localhost only
6. **Environment Variables**: Never commit .env files to version control
7. **Regular Updates**: Keep dependencies updated

## Monitoring & Observability

### Health Checks

```bash
# Liveness probe (basic health)
GET /health

# Readiness probe (with dependencies)
GET /health/ready

# System information
GET /health/info
```

### Prometheus Metrics

Available at `/metrics`:

- `api_requests_total`: Total API requests by method, endpoint, status
- `api_request_duration_seconds`: Request duration histogram
- `calls_initiated_total`: Total outbound calls initiated
- `meetings_booked_total`: Total meetings booked

### Logging

Structured JSON logs (production) or pretty-printed (development):

```json
{
  "event": "call_session_created",
  "timestamp": "2024-12-12T10:30:00Z",
  "level": "info",
  "call_sid": "CA123...",
  "lead_id": 42
}
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml - scale workers
docker-compose up --scale celery_worker=3
```

### Database Connection Pooling

Already configured in `app/database.py`:

- Pool size: 10
- Max overflow: 20

### Redis Clustering

For high availability, use Redis Cluster or Sentinel.

### Load Balancing

Use Nginx or AWS ALB to distribute traffic across multiple app instances.

## Backup & Recovery

### Database Backups

```bash
# Backup
pg_dump -U agent_messiah agent_messiah > backup_$(date +%Y%m%d).sql

# Restore
psql -U agent_messiah agent_messiah < backup_20241212.sql
```

### Automated Backups (cron)

```bash
# Add to crontab
0 2 * * * pg_dump -U agent_messiah agent_messiah > /backups/agent_$(date +\%Y\%m\%d).sql
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U agent_messiah -h localhost -d agent_messiah
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

### Celery Not Processing Tasks

```bash
# Check Celery worker logs
celery -A app.celery_tasks worker --loglevel=debug

# Verify Redis connection
redis-cli -u redis://localhost:6379/0 ping
```

### Twilio Webhook Issues

1. Check `BASE_URL` is correct and publicly accessible
2. Verify ngrok is running (local dev)
3. Check Twilio webhook logs in console
4. Verify `TWILIO_AUTH_TOKEN` is correct for signature validation

## Cost Optimization

### OpenAI

- Using `gpt-4o-mini`: ~$0.0015 per conversation
- Average conversation: 10-20 turns
- Monthly cost (1000 calls): ~$15-30

### Twilio

- Outbound calls: ~$0.013/minute
- Phone number: $1/month
- Monthly cost (1000 calls, avg 2 min): ~$27

### Infrastructure

- VPS (2GB RAM): $10-20/month
- Or use free tier: Render.com, Railway.app

## Support & Monitoring

### Log Analysis

```bash
# View recent errors
docker-compose logs app | grep ERROR

# Monitor in real-time
docker-compose logs -f app celery_worker
```

### Performance Monitoring

- Use Prometheus + Grafana for metrics visualization
- Set up alerts for high error rates
- Monitor response times and call success rates

## Next Steps

1. **CI/CD Pipeline**: Set up GitHub Actions or GitLab CI
2. **Monitoring**: Deploy Prometheus + Grafana
3. **Alerting**: Configure alerts for errors and downtime
4. **Rate Limiting**: Add request rate limiting
5. **Caching**: Add caching for frequent queries
6. **Testing**: Expand test coverage
7. **Documentation**: API documentation with Swagger/ReDoc

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Twilio Voice API](https://www.twilio.com/docs/voice)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryq.dev/)
