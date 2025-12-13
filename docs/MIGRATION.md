# Migration from MVP to Production

## What Changed

Agent Messiah has been upgraded from an MVP to a production-ready system. Here's what's new:

### 1. Database Persistence ✅

**Before**: In-memory storage (data lost on restart)
**After**: PostgreSQL database with SQLAlchemy ORM

- Lead management persists across restarts
- Meeting bookings saved to database
- Call session history tracked
- Full transaction support

**Migration**:

```bash
# Initialize database
alembic upgrade head

# Data is automatically migrated from in-memory to database on first run
```

### 2. Redis Session Management ✅

**Before**: No conversation state persistence between calls
**After**: Redis-based session storage

- Conversation history maintained during calls
- Session expiry (configurable TTL)
- Fast access to call state
- Supports distributed deployments

**Setup**:

```bash
# Install Redis
brew install redis  # macOS
sudo apt install redis-server  # Ubuntu

# Start Redis
brew services start redis  # macOS
sudo systemctl start redis-server  # Ubuntu
```

### 3. Structured Logging ✅

**Before**: Basic print statements
**After**: Production-grade structured logging with structlog

- JSON formatted logs (production)
- Pretty-printed logs (development)
- Contextual logging with metadata
- Log aggregation ready

**Example logs**:

```json
{
  "event": "call_initiated",
  "timestamp": "2024-12-12T10:30:00Z",
  "level": "info",
  "lead_id": 42,
  "call_sid": "CA123..."
}
```

### 4. Health Checks & Monitoring ✅

**Before**: No health endpoints
**After**: Comprehensive health checks

- `/health` - Basic liveness probe
- `/health/ready` - Readiness with dependency checks
- `/health/info` - System information
- `/metrics` - Prometheus metrics

### 5. Security ✅

**Before**: No authentication or validation
**After**: Production security features

- API key authentication (optional)
- Twilio webhook signature validation
- Environment-based configuration
- Sensitive data masking in logs

**Setup**:

```bash
# Add to .env
API_KEY=your_secret_api_key
WEBHOOK_SECRET=your_webhook_secret
```

### 6. Async Job Processing ✅

**Before**: Synchronous campaign calling
**After**: Celery-based async jobs

- Background task processing
- Campaign queue management
- Scheduled tasks support
- Distributed workers

**Start worker**:

```bash
celery -A app.celery_tasks worker --loglevel=info
```

### 7. Docker Support ✅

**Before**: Manual setup only
**After**: Full Docker containerization

- Multi-container setup (app, db, redis, celery)
- Docker Compose for local development
- Production-ready Dockerfile
- Health checks and auto-restart

**Quick start**:

```bash
docker-compose up -d
```

## Breaking Changes

### API Format Changes

The conversation history format now supports both formats:

**Old format** (still works):

```json
{
  "history": [{ "user": "שלום", "agent": "היי!" }]
}
```

**New format** (preferred):

```json
{
  "history": [
    { "role": "user", "content": "שלום" },
    { "role": "assistant", "content": "היי!" }
  ]
}
```

### Environment Variables

Recommended production variables:

- `DATABASE_URL` - Database connection string (defaults to SQLite for local/dev)
- `REDIS_URL` - Redis connection string (optional in local/dev)

New optional variables:

- `LOG_LEVEL` - Logging level
- `API_KEY` - API authentication
- `WEBHOOK_SECRET` - Webhook validation

## Migration Steps

### From Local Development

If you're running the MVP locally:

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL**:

   ```bash
   createdb agent_messiah
   ```

3. **Set up Redis**:

   ```bash
   brew install redis && brew services start redis
   ```

4. **Update .env**:

   ```bash
   cp .env.example .env
   # Optionally add DATABASE_URL and REDIS_URL for full production mode
   ```

5. **Run migrations**:

   ```bash
   alembic upgrade head
   ```

6. **Start application**:
   ```bash
   uvicorn app.main:app --reload
   ```

### Using Docker (Recommended)

1. **Configure environment**:

   ```bash
   cp .env.docker.example .env.docker
   # Edit .env.docker with your credentials
   ```

2. **Start services**:

   ```bash
   docker-compose up -d
   ```

3. **Check status**:
   ```bash
   curl http://localhost:8000/health/ready
   ```

## Feature Comparison

| Feature            | MVP                | Production            |
| ------------------ | ------------------ | --------------------- |
| Data Persistence   | ❌ In-memory       | ✅ PostgreSQL         |
| Session Management | ❌ None            | ✅ Redis              |
| Logging            | ⚠️ Basic           | ✅ Structured JSON    |
| Health Checks      | ❌ None            | ✅ Full suite         |
| Metrics            | ❌ None            | ✅ Prometheus         |
| Security           | ❌ None            | ✅ Auth + Validation  |
| Async Tasks        | ❌ Synchronous     | ✅ Celery             |
| Docker Support     | ❌ None            | ✅ Full               |
| Monitoring         | ❌ None            | ✅ Logs + Metrics     |
| Scalability        | ❌ Single instance | ✅ Horizontal scaling |

## Performance Improvements

- **Database pooling**: Connection pool (10 + 20 overflow)
- **Redis caching**: Fast session access
- **Async workers**: Non-blocking campaign execution
- **Health checks**: Auto-restart on failures
- **Structured logging**: Efficient log processing

## What Didn't Change

- ✅ All existing API endpoints work
- ✅ LLM integration (OpenAI GPT-4o-mini)
- ✅ Twilio voice integration
- ✅ Hebrew conversation support
- ✅ Meeting booking functionality
- ✅ Rule-based fallback mode
- ✅ Test coverage (42 tests)

## Next Steps

1. **Deploy to production**:

   - Set up on cloud provider (AWS, GCP, Azure)
   - Configure domain and SSL
   - Set up monitoring (Prometheus + Grafana)

2. **Scale horizontally**:

   - Add more app instances behind load balancer
   - Scale Celery workers based on load
   - Enable Redis clustering

3. **Add features**:
   - Rate limiting
   - Request caching
   - Email notifications
   - Advanced analytics

## Support

For issues or questions:

- Check logs: `docker-compose logs -f app`
- Health status: `curl http://localhost:8000/health/ready`
- Metrics: `curl http://localhost:8000/metrics`

## Rollback

If you need to rollback to MVP:

1. Stop new services:

   ```bash
   docker-compose down
   ```

2. Checkout previous commit:

   ```bash
   git checkout <mvp-commit-hash>
   ```

3. Restart:
   ```bash
   uvicorn app.main:app --reload
   ```

Note: You'll lose database persistence but all functionality will work.
