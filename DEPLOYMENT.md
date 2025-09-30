# NYC Subway ETA Deployment Guide

## Production Deployment Options

### Option 1: Docker Production Setup (Recommended)

```bash
# 1. Clone and setup
git clone <repository-url>
cd nyc-subway-eta

# 2. Configure environment
cp infra/.env.example infra/.env
# Edit infra/.env with your MTA API key and production settings

# 3. Run production setup
./run_production.sh
```

### Option 2: Manual Production Deployment

#### Prerequisites
- Docker Desktop or Docker Engine
- 4GB+ RAM available
- Valid MTA API key from https://api.mta.info/

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Database setup
export DATABASE_URL="postgresql://user:pass@localhost:5432/nyc_subway"
alembic upgrade head

# Load GTFS data
python scripts/load_gtfs_static.py --download

# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend
# Frontend is pure HTML/CSS/JS - serve with any web server
python -m http.server 3000
# Or use nginx, Apache, etc.
```

### Option 3: Cloud Deployment

#### Docker Cloud Platforms
- **Heroku**: Use the included Dockerfile
- **AWS ECS**: Container-ready with docker-compose
- **Google Cloud Run**: Stateless container deployment
- **Azure Container Instances**: Simple container hosting

#### Configuration for Cloud
```bash
# Set environment variables
export MTA_FEED_URLS="comma,separated,feed,urls"
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://..."
export GTFS_RT_POLL_INTERVAL_SECONDS=45
```

## Performance Tuning

### Database Optimization
```sql
-- Add indexes for faster queries
CREATE INDEX idx_stops_name ON stops(stop_name);
CREATE INDEX idx_stop_times_stop_id ON stop_times(stop_id);
CREATE INDEX idx_trips_route_id ON trips(route_id);
```

### Redis Configuration
```
# redis.conf optimizations
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/frontend;
        try_files $uri $uri/ /index.html;

        # Caching
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Caching for static endpoints
        location /api/stops {
            proxy_cache api_cache;
            proxy_cache_valid 200 1h;
        }
    }
}
```

## Monitoring & Maintenance

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database connection
docker-compose exec postgres pg_isready

# Redis status
docker-compose exec redis redis-cli ping
```

### Log Monitoring
```bash
# View API logs
docker-compose logs -f api

# View background poller logs
docker-compose logs -f poller

# Check performance metrics
docker-compose exec api python -c "from monitoring import monitor; print(monitor.get_performance_stats())"
```

### Backup Strategy
```bash
# Database backup
docker-compose exec postgres pg_dump -U postgres nyc_subway > backup.sql

# Environment backup
cp infra/.env backup.env

# Redis backup (if persistence enabled)
docker-compose exec redis redis-cli BGSAVE
```

## Scaling Considerations

### Horizontal Scaling
- **API Servers**: Run multiple API containers behind load balancer
- **Background Pollers**: Distribute feeds across multiple poller instances
- **Database**: PostgreSQL read replicas for query scaling
- **Redis**: Redis Cluster for high availability

### Vertical Scaling
- **Memory**: 4GB+ recommended for production
- **CPU**: 2+ cores for concurrent request handling
- **Storage**: 10GB+ for GTFS data and logs

## Security Best Practices

### Environment Security
```bash
# Use secrets management
export MTA_API_KEY=$(cat /run/secrets/mta_api_key)

# Restrict network access
# Only allow necessary ports (80, 443)

# Enable HTTPS
# Use Let's Encrypt or cloud provider SSL
```

### Database Security
```sql
-- Create read-only user for monitoring
CREATE USER readonly_user WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

## Troubleshooting

### Common Issues
1. **MTA API Rate Limiting**: Reduce poll frequency in config
2. **Memory Usage**: Check marker clustering settings
3. **Database Connection**: Verify connection string and credentials
4. **Redis Connection**: Ensure Redis is running and accessible

### Performance Issues
```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/stops?q=times

# Monitor database queries
docker-compose exec postgres psql -U postgres -c "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check memory usage
docker stats
```

For additional support, check the GitHub issues or create a new issue with detailed logs and environment information.