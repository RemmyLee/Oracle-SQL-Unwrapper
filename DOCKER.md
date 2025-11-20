# Docker Deployment Guide

This guide covers running PL/SQL Workbench using Docker and Docker Compose for both development and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Development Environment](#development-environment)
4. [Production Environment](#production-environment)
5. [Configuration](#configuration)
6. [Managing Containers](#managing-containers)
7. [Database Migrations](#database-migrations)
8. [Backup and Restore](#backup-and-restore)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker**: 20.10 or later
- **Docker Compose**: 1.29 or later

### Installation

#### Ubuntu/Debian
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### macOS
```bash
# Install Docker Desktop for Mac
# Download from: https://www.docker.com/products/docker-desktop
```

#### Windows
```bash
# Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop
```

### Verify Installation

```bash
docker --version
docker compose version
```

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/YourOrg/Oracle-SQL-Unwrapper.git
cd Oracle-SQL-Unwrapper
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env
```

**Minimum required changes in `.env`:**

```ini
# Security Keys (GENERATE THESE!)
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Database
POSTGRES_PASSWORD=your-secure-database-password

# Redis
REDIS_PASSWORD=your-secure-redis-password
```

**Generate secure keys:**

```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
```

### 3. Start Services

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

### 4. Initialize Database

```bash
# Run migrations
docker compose exec app alembic upgrade head

# Or run SQL migration
docker compose exec app psql -h postgres -U plsql_user -d plsql_workbench -f migrations/001_phase5_dashboard_models.sql
```

### 5. Create Admin User

```bash
docker compose exec app python -c "
from backend.app import create_app
from backend.models import User, Role
from backend.extensions import db

app = create_app('production')
with app.app_context():
    admin_role = Role(name='admin', description='Administrator')
    db.session.add(admin_role)

    admin = User(
        username='admin',
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        is_active=True,
        is_admin=True,
        email_verified=True
    )
    admin.set_password('ChangeMe123!')
    admin.roles.append(admin_role)
    db.session.add(admin)
    db.session.commit()
    print('Admin user created')
"
```

### 6. Access Application

- **Application**: http://localhost:8000
- **Health Check**: http://localhost:8000/api/health
- **Metrics**: http://localhost:8000/api/metrics

---

## Development Environment

### Start Development Environment

```bash
# Use development compose file
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# This includes:
# - Hot reload for code changes
# - Debug mode enabled
# - Adminer (database GUI) at http://localhost:8080
# - Redis Commander at http://localhost:8081
```

### Development Tools

#### Adminer (Database GUI)
- **URL**: http://localhost:8080
- **System**: PostgreSQL
- **Server**: postgres
- **Username**: plsql_user
- **Password**: (from .env)
- **Database**: plsql_workbench

#### Redis Commander (Redis GUI)
- **URL**: http://localhost:8081

### Hot Reload

The development environment mounts source code as volumes, enabling hot reload:

```bash
# Make changes to backend code
nano backend/api/dashboards.py

# Gunicorn will automatically reload
# Check logs: docker compose logs -f app
```

### Running Commands

```bash
# Python shell
docker compose exec app python

# Flask shell
docker compose exec app flask shell

# Run tests
docker compose exec app pytest

# Install new dependencies
docker compose exec app pip install package-name
# Don't forget to update requirements.txt

# Run linting
docker compose exec app flake8 backend/
docker compose exec app black backend/
```

---

## Production Environment

### 1. Prepare for Production

**Update `.env` for production:**

```ini
FLASK_ENV=production
FLASK_DEBUG=False

# Use strong passwords
POSTGRES_PASSWORD=<very-secure-password>
REDIS_PASSWORD=<very-secure-password>

# Use secure keys (64+ characters)
SECRET_KEY=<generated-secure-key>
ENCRYPTION_KEY=<generated-secure-key>
JWT_SECRET_KEY=<generated-secure-key>

# Email configuration
MAIL_SERVER=smtp.your-domain.com
MAIL_PORT=587
MAIL_USERNAME=noreply@your-domain.com
MAIL_PASSWORD=<smtp-password>

# CORS (only your domains)
CORS_ORIGINS=https://your-domain.com

# Security
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true

# Disable features not needed in production
ENABLE_API_DOCS=false
```

### 2. Enable Production Services

```bash
# Start with Nginx reverse proxy
docker compose --profile production up -d

# This starts:
# - PostgreSQL
# - Redis
# - Application (4 workers)
# - Celery worker
# - Nginx (ports 80, 443)
```

### 3. Configure Nginx

Create `nginx/conf.d/default.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Let's Encrypt validation
    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }

    # Redirect to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location /api/ {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

### 4. SSL Certificate (Let's Encrypt)

```bash
# Install certbot
docker run -it --rm \
  -v letsencrypt:/etc/letsencrypt \
  -v letsencrypt_www:/var/www/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly \
  --standalone \
  -d your-domain.com \
  --agree-tos \
  --email admin@your-domain.com

# Restart Nginx
docker compose --profile production restart nginx
```

### 5. Auto-renewal with Cron

```bash
# Add to crontab
0 3 * * * docker run --rm -v letsencrypt:/etc/letsencrypt -v letsencrypt_www:/var/www/letsencrypt certbot/certbot renew --quiet && docker compose restart nginx
```

---

## Configuration

### Environment Variables

All configuration is done through `.env` file. See `.env.example` for all available options.

**Key Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (development/production) | `production` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `changeme` |
| `REDIS_PASSWORD` | Redis password | `changeme` |
| `SECRET_KEY` | Flask secret key | - |
| `DATABASE_URL` | Database connection string | Auto-generated |
| `REDIS_URL` | Redis connection string | Auto-generated |

### Volumes

Docker Compose creates persistent volumes:

| Volume | Purpose | Location |
|--------|---------|----------|
| `postgres_data` | Database data | /var/lib/postgresql/data |
| `redis_data` | Redis data | /data |
| `app_logs` | Application logs | /app/logs |
| `app_uploads` | User uploads | /app/uploads |
| `nginx_logs` | Nginx logs | /var/log/nginx |

### Networking

All services run on the `plsql-network` bridge network:

- **app**: http://app:8000
- **postgres**: postgres:5432
- **redis**: redis:6379
- **nginx**: http://nginx:80, https://nginx:443

---

## Managing Containers

### Common Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose stop

# Restart services
docker compose restart

# Stop and remove containers
docker compose down

# Stop and remove containers + volumes (WARNING: deletes data!)
docker compose down -v

# View logs
docker compose logs -f [service-name]

# View logs for specific service
docker compose logs -f app
docker compose logs -f postgres

# Check status
docker compose ps

# View resource usage
docker stats
```

### Scaling Services

```bash
# Scale application workers
docker compose up -d --scale app=3

# Scale Celery workers
docker compose up -d --scale celery=2
```

### Updating Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose build
docker compose up -d

# Run migrations
docker compose exec app alembic upgrade head
```

---

## Database Migrations

### Using Alembic

```bash
# Check current version
docker compose exec app alembic current

# Upgrade to latest
docker compose exec app alembic upgrade head

# Downgrade one version
docker compose exec app alembic downgrade -1

# View migration history
docker compose exec app alembic history

# Create new migration
docker compose exec app alembic revision -m "description"
```

### Using SQL Scripts

```bash
# Run SQL migration
docker compose exec -T postgres psql -U plsql_user -d plsql_workbench < migrations/001_phase5_dashboard_models.sql
```

### Direct PostgreSQL Access

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U plsql_user -d plsql_workbench

# Or from host (if port exposed)
psql -h localhost -U plsql_user -d plsql_workbench
```

---

## Backup and Restore

### Database Backup

```bash
# Create backup
docker compose exec -T postgres pg_dump -U plsql_user plsql_workbench | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Automated daily backup
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
docker compose exec -T postgres pg_dump -U plsql_user plsql_workbench | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete
EOF

chmod +x backup.sh

# Add to crontab
0 2 * * * /path/to/backup.sh
```

### Database Restore

```bash
# Stop application
docker compose stop app celery

# Restore database
gunzip -c backup_20240120_020000.sql.gz | docker compose exec -T postgres psql -U plsql_user -d plsql_workbench

# Restart application
docker compose start app celery
```

### Volume Backup

```bash
# Backup volumes
docker run --rm \
  -v plsql_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /data .

# Restore volumes
docker run --rm \
  -v plsql_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/postgres_data_20240120.tar.gz -C /data
```

---

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8000/api/health

# Readiness check
curl http://localhost:8000/api/health/ready

# Metrics
curl http://localhost:8000/api/metrics

# Prometheus metrics
curl http://localhost:8000/api/metrics/prometheus
```

### Docker Health Status

```bash
# Check container health
docker compose ps

# Inspect health check details
docker inspect --format='{{json .State.Health}}' plsql-app | jq
```

### Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f app
docker compose logs -f postgres
docker compose logs -f celery

# View last 100 lines
docker compose logs --tail=100 app

# Follow logs with timestamps
docker compose logs -f -t app
```

### Resource Usage

```bash
# Container resource usage
docker stats

# Disk usage
docker system df

# Volume usage
docker volume ls
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs app

# Check configuration
docker compose config

# Validate environment
docker compose exec app env
```

### Database Connection Issues

```bash
# Test database connection
docker compose exec app python -c "
from backend.app import create_app
from backend.extensions import db
app = create_app('production')
with app.app_context():
    db.session.execute(db.text('SELECT 1'))
    print('Database connected successfully')
"

# Check PostgreSQL logs
docker compose logs postgres

# Connect to PostgreSQL directly
docker compose exec postgres psql -U plsql_user -d plsql_workbench
```

### Redis Connection Issues

```bash
# Test Redis connection
docker compose exec redis redis-cli -a <redis-password> PING

# Check Redis logs
docker compose logs redis
```

### Application Errors

```bash
# View application logs
docker compose logs app

# Access application shell
docker compose exec app python

# Check environment variables
docker compose exec app env | grep -E 'FLASK|DATABASE|REDIS'
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Increase workers (if CPU available)
# Edit docker-compose.yml and change --workers value

# Scale application
docker compose up -d --scale app=3

# Check database performance
docker compose exec postgres psql -U plsql_user -d plsql_workbench -c "
SELECT pid, query, state, wait_event_type
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;
"
```

### Networking Issues

```bash
# Check network
docker network ls
docker network inspect oracle-sql-unwrapper_plsql-network

# Test connectivity between containers
docker compose exec app ping postgres
docker compose exec app ping redis
```

### Clean Restart

```bash
# Stop and remove everything
docker compose down -v

# Remove images
docker compose down --rmi all

# Rebuild from scratch
docker compose build --no-cache
docker compose up -d
```

---

## Best Practices

### Security

1. **Always change default passwords** in `.env`
2. **Use secrets management** for production (Docker Swarm secrets, Kubernetes secrets)
3. **Don't commit `.env`** file to git
4. **Limit exposed ports** - only expose what's needed
5. **Run as non-root user** (already configured in Dockerfile)
6. **Enable security scanning**:
   ```bash
   docker scan plsql-app
   ```

### Performance

1. **Tune worker count** based on available CPUs
2. **Use volumes** for persistent data
3. **Enable Redis persistence** (already configured)
4. **Monitor resource usage** regularly
5. **Set resource limits** in docker-compose.yml:
   ```yaml
   services:
     app:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 2G
   ```

### Maintenance

1. **Regular backups** - automate with cron
2. **Update images** regularly:
   ```bash
   docker compose pull
   docker compose up -d
   ```
3. **Clean up unused resources**:
   ```bash
   docker system prune -a
   ```
4. **Monitor logs** for errors
5. **Test updates** in development first

---

## Production Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate strong SECRET_KEY, ENCRYPTION_KEY, JWT_SECRET_KEY
- [ ] Configure email settings (SMTP)
- [ ] Set CORS_ORIGINS to your domain only
- [ ] Enable FORCE_HTTPS=true
- [ ] Configure SSL certificates with Let's Encrypt
- [ ] Set up automated backups
- [ ] Configure monitoring (Prometheus, Grafana)
- [ ] Set resource limits for containers
- [ ] Review and configure rate limiting
- [ ] Test disaster recovery procedure
- [ ] Set up log aggregation (ELK, CloudWatch, etc.)
- [ ] Configure firewall rules
- [ ] Enable container health checks
- [ ] Document access credentials securely

---

## Support

For issues and questions:
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: See `DEPLOYMENT.md`, `README.md`
- **Health Checks**: Monitor `/api/health`, `/api/metrics`

---

**Last Updated**: 2025-11-20
**Version**: 1.0 (Phase 5 Production Ready)
