# Production Deployment Guide

## Overview

This guide covers deploying the NYC Subway ETA application to production environments with high availability, performance monitoring, and scalability.

## Architecture Components

### Backend Services
- **FastAPI Application**: Core API server
- **PostgreSQL Database**: Primary data storage
- **Redis Cache**: Real-time arrivals caching
- **NGINX**: Reverse proxy and load balancer

### Frontend
- **Static HTML/CSS/JS**: Single-page application
- **CDN Integration**: Assets delivered via CDN

## Deployment Options

### 1. Docker Compose (Recommended for Single Server)

```bash
# Clone repository
git clone https://github.com/ryleymao/NYC-Subway-ETA.git
cd NYC-Subway-ETA

# Set up environment
cp .env.example .env
# Edit .env with production values

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Health check
curl http://localhost/health
```

### 2. Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nyc-subway-eta
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nyc-subway-eta
  template:
    metadata:
      labels:
        app: nyc-subway-eta
    spec:
      containers:
      - name: api
        image: ryleymao/nyc-subway-eta:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

### 3. Cloud Platform Deployment

#### AWS ECS with Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker build -t nyc-subway-eta .
docker tag nyc-subway-eta:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/nyc-subway-eta:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/nyc-subway-eta:latest

# Deploy with ECS CLI
ecs-cli compose --project-name nyc-subway-eta service up --create-log-groups --cluster-config production
```

#### Google Cloud Run
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/nyc-subway-eta
gcloud run deploy --image gcr.io/PROJECT-ID/nyc-subway-eta --platform managed --region us-central1
```

#### Azure Container Instances
```bash
# Create resource group and deploy
az group create --name nyc-subway-eta --location eastus
az container create --resource-group nyc-subway-eta --name nyc-subway-eta-api --image ryleymao/nyc-subway-eta:latest --ports 8000
```

## Environment Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/subway_eta

# MTA API
MTA_API_KEY=your_mta_api_key_here

# Redis Cache
REDIS_URL=redis://localhost:6379

# Application
DEBUG=False
LOG_LEVEL=INFO
API_TITLE="NYC Subway ETA API"
API_VERSION="1.0.0"

# Security
SECRET_KEY=your-secure-random-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Performance
MAX_CONNECTIONS=100
POOL_SIZE=20
CACHE_TTL=30
```

### Optional Environment Variables

```bash
# Monitoring
SENTRY_DSN=https://your-sentry-dsn
PROMETHEUS_ENABLED=true
JAEGER_ENDPOINT=http://jaeger:14268

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_CREDENTIALS=true
```

## Performance Optimization

### Database Optimization
```sql
-- Create indexes for common queries
CREATE INDEX idx_arrivals_stop_id ON arrivals(stop_id);
CREATE INDEX idx_arrivals_route_id ON arrivals(route_id);
CREATE INDEX idx_arrivals_eta ON arrivals(eta_s);

-- Enable connection pooling
ALTER SYSTEM SET max_connections = '200';
ALTER SYSTEM SET shared_buffers = '256MB';
```

### Redis Configuration
```conf
# redis.conf optimizations
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### NGINX Configuration
```nginx
# nginx.conf
upstream api_backend {
    server api:8000 max_fails=3 fail_timeout=30s;
    server api:8001 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    client_max_body_size 10M;

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache api_cache;
        proxy_cache_valid 200 30s;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        gzip on;
        gzip_types text/css application/javascript application/json;
    }
}
```

## Monitoring and Observability

### Health Checks
```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging Configuration
```python
# logging.conf
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}
```

### Metrics Collection
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')
```

## Security Configuration

### SSL/TLS Setup
```bash
# Certbot with Let's Encrypt
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Or with custom certificates
ssl_certificate /etc/ssl/certs/yourdomain.com.pem;
ssl_certificate_key /etc/ssl/private/yourdomain.com.key;
ssl_protocols TLSv1.2 TLSv1.3;
```

### Firewall Configuration
```bash
# UFW rules
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw deny 8000/tcp  # Block direct API access
ufw enable
```

## Scaling Strategies

### Horizontal Scaling
```yaml
# Auto-scaling with Kubernetes
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nyc-subway-eta-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nyc-subway-eta
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Database Scaling
```sql
-- Read replicas for query scaling
CREATE PUBLICATION arrivals_pub FOR TABLE arrivals;

-- Partitioning for large datasets
CREATE TABLE arrivals_2024 PARTITION OF arrivals
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

## Backup and Recovery

### Database Backups
```bash
# Automated backup script
#!/bin/bash
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
aws s3 cp backup_*.sql.gz s3://your-backup-bucket/
find . -name "backup_*.sql.gz" -mtime +7 -delete
```

### Disaster Recovery
```bash
# Recovery procedure
gunzip -c backup_20240101_120000.sql.gz | psql $DATABASE_URL
systemctl restart nyc-subway-eta
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   docker stats
   # Restart services if needed
   docker-compose restart api
   ```

2. **Database Connection Issues**
   ```bash
   # Check connection pool
   SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
   # Restart database if needed
   docker-compose restart postgres
   ```

3. **API Timeouts**
   ```bash
   # Check API logs
   docker-compose logs api
   # Monitor response times
   curl -w "@curl-format.txt" -s -o /dev/null http://localhost/api/health
   ```

### Performance Debugging
```python
# Enable SQL query logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Profile slow endpoints
from monitoring import monitor_performance

@monitor_performance
async def slow_endpoint():
    # Your endpoint code
    pass
```

## Maintenance

### Regular Tasks
- Update dependencies monthly
- Rotate database credentials quarterly
- Review and archive logs weekly
- Performance testing before major releases
- Security scanning with automated tools

### Update Procedure
```bash
# Rolling update
docker-compose pull
docker-compose up -d --no-deps api
docker-compose up -d --no-deps frontend
```