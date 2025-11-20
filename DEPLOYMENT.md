# Production Deployment Guide

This guide covers deploying the PL/SQL Workbench application to a production environment with best practices for security, performance, and reliability.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Prerequisites](#prerequisites)
3. [Database Setup](#database-setup)
4. [Redis Setup](#redis-setup)
5. [Application Setup](#application-setup)
6. [Web Server Configuration](#web-server-configuration)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Process Management](#process-management)
9. [Monitoring & Logging](#monitoring--logging)
10. [Backup & Maintenance](#backup--maintenance)
11. [Security Checklist](#security-checklist)
12. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores (4+ recommended)
- **RAM**: 4GB (8GB+ recommended)
- **Disk**: 20GB (SSD recommended)
- **OS**: Ubuntu 20.04 LTS or later, CentOS 8+, Debian 11+

### Software Requirements
- **Python**: 3.9 or later
- **PostgreSQL**: 13 or later (recommended) or MySQL 8.0+
- **Redis**: 6.0 or later
- **Nginx**: 1.18 or later (or Apache 2.4+)
- **Oracle Client**: 19c or later (for Oracle database connectivity)

---

## Prerequisites

### 1. Update System Packages

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2. Install Python and Dependencies

```bash
# Ubuntu/Debian
sudo apt install -y python3.9 python3.9-venv python3.9-dev python3-pip
sudo apt install -y build-essential libpq-dev libaio1

# CentOS/RHEL
sudo yum install -y python39 python39-devel python39-pip
sudo yum install -y gcc postgresql-devel
```

### 3. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install -y postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install -y postgresql-server postgresql-contrib
sudo postgresql-setup initdb
```

### 4. Install Redis

```bash
# Ubuntu/Debian
sudo apt install -y redis-server

# CentOS/RHEL
sudo yum install -y redis
```

### 5. Install Nginx

```bash
# Ubuntu/Debian
sudo apt install -y nginx

# CentOS/RHEL
sudo yum install -y nginx
```

---

## Database Setup

### 1. Create PostgreSQL Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE plsql_workbench;
CREATE USER plsql_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE plsql_workbench TO plsql_user;
ALTER DATABASE plsql_workbench OWNER TO plsql_user;
\q
```

### 2. Configure PostgreSQL for Production

Edit `/etc/postgresql/13/main/postgresql.conf`:

```ini
# Connection Settings
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 128MB

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

# Performance
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200  # For SSD
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### 3. Test Database Connection

```bash
psql -h localhost -U plsql_user -d plsql_workbench
# Enter password when prompted
# Should connect successfully
\q
```

---

## Redis Setup

### 1. Configure Redis

Edit `/etc/redis/redis.conf`:

```ini
# Bind to localhost for security (or specific IP)
bind 127.0.0.1

# Set password (uncomment and change)
requirepass your_redis_password_here

# Enable persistence
appendonly yes
appendfsync everysec

# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log
```

### 2. Start and Enable Redis

```bash
sudo systemctl start redis
sudo systemctl enable redis

# Test connection
redis-cli
# In redis-cli:
AUTH your_redis_password_here
PING
# Should return PONG
exit
```

---

## Application Setup

### 1. Create Application User

```bash
sudo useradd -m -s /bin/bash plsql
sudo usermod -aG www-data plsql  # For Nginx
```

### 2. Clone and Setup Application

```bash
# Switch to plsql user
sudo su - plsql

# Clone repository
git clone https://github.com/YourOrg/Oracle-SQL-Unwrapper.git
cd Oracle-SQL-Unwrapper

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install Oracle Instant Client (if needed)
# Download from Oracle website and install
# Then set environment variables:
export ORACLE_HOME=/opt/oracle/instantclient_19_8
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
```

### 3. Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit with production values
nano .env
```

**Important `.env` Settings for Production:**

```ini
# Flask Environment
FLASK_ENV=production
FLASK_DEBUG=False
PORT=8000

# Security Keys (GENERATE STRONG RANDOM VALUES!)
SECRET_KEY=<generate-with-python-secrets-module>
ENCRYPTION_KEY=<generate-with-python-secrets-module>
JWT_SECRET_KEY=<generate-with-python-secrets-module>

# Database (PostgreSQL)
DATABASE_URL=postgresql://plsql_user:your_secure_password_here@localhost:5432/plsql_workbench

# Database Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Redis
REDIS_URL=redis://:your_redis_password_here@localhost:6379/0

# Email/SMTP
MAIL_SERVER=smtp.your-domain.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=noreply@your-domain.com
MAIL_PASSWORD=your_smtp_password
MAIL_DEFAULT_SENDER=PL/SQL Workbench <noreply@your-domain.com>

# CORS Origins (your frontend domains)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Rate Limiting
RATELIMIT_ENABLED=true
RATELIMIT_DEFAULT=100 per minute
RATELIMIT_API_STRICT=1000 per hour
RATELIMIT_AUTH=5 per minute
RATELIMIT_PUBLIC=50 per minute

# Security Headers
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# Monitoring
METRICS_PORT=9090
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true

# Celery
CELERY_BROKER_URL=redis://:your_redis_password_here@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:your_redis_password_here@localhost:6379/0

# Feature Flags
ENABLE_REGISTRATION=true
ENABLE_API_DOCS=false  # Disable in production for security
ENABLE_METRICS=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

**Generate Secure Keys:**

```python
# Run in Python console
import secrets
print("SECRET_KEY:", secrets.token_urlsafe(64))
print("ENCRYPTION_KEY:", secrets.token_urlsafe(64))
print("JWT_SECRET_KEY:", secrets.token_urlsafe(64))
```

### 4. Run Database Migrations

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Option 1: Using Alembic (recommended)
alembic upgrade head

# Option 2: Using SQL migration script
psql -h localhost -U plsql_user -d plsql_workbench -f migrations/001_phase5_dashboard_models.sql

# Option 3: Using SQLAlchemy (if running app for first time)
python -c "from backend.app import create_app; from backend.extensions import db; app = create_app('production'); app.app_context().push(); db.create_all()"
```

### 5. Create Admin User

```bash
# Create admin user script
python -c "
from backend.app import create_app
from backend.models import User, Role
from backend.extensions import db

app = create_app('production')
with app.app_context():
    # Create admin role
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='Administrator')
        db.session.add(admin_role)
        db.session.commit()

    # Create admin user
    admin = User(
        username='admin',
        email='admin@your-domain.com',
        first_name='Admin',
        last_name='User',
        is_active=True,
        is_admin=True,
        email_verified=True
    )
    admin.set_password('ChangeThisPassword123!')
    admin.roles.append(admin_role)
    db.session.add(admin)
    db.session.commit()
    print('Admin user created successfully')
"
```

### 6. Create Required Directories

```bash
mkdir -p logs uploads
chmod 755 logs uploads
```

### 7. Test Application

```bash
# Test with Flask development server
python backend/app.py

# Test with Gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 "backend.app:create_app('production')"

# Open another terminal and test
curl http://localhost:8000/api/health
# Should return: {"status":"healthy",...}
```

---

## Web Server Configuration

### Nginx Configuration

Create `/etc/nginx/sites-available/plsql-workbench`:

```nginx
# Upstream application server
upstream plsql_app {
    server 127.0.0.1:8000;
    # For multiple workers, add more:
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=public_limit:10m rate=50r/m;

# HTTP - Redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;

    # Let's Encrypt validation
    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS - Main application
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/plsql-workbench-access.log;
    error_log /var/log/nginx/plsql-workbench-error.log;

    # Max upload size
    client_max_body_size 100M;

    # Root directory
    root /home/plsql/Oracle-SQL-Unwrapper/frontend/dist;
    index index.html;

    # Health check (no rate limiting)
    location /api/health {
        proxy_pass http://plsql_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }

    # Authentication endpoints (strict rate limiting)
    location ~ ^/api/auth/(login|register|forgot-password|reset-password) {
        limit_req zone=auth_limit burst=2 nodelay;
        proxy_pass http://plsql_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }

    # Public dashboard endpoints (moderate rate limiting)
    location /api/public/ {
        limit_req zone=public_limit burst=10 nodelay;
        proxy_pass http://plsql_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }

    # API endpoints (general rate limiting)
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://plsql_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;  # 5 minutes for long queries
        proxy_connect_timeout 60s;
    }

    # Static files
    location /static/ {
        alias /home/plsql/Oracle-SQL-Unwrapper/frontend/dist/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Frontend routes (SPA)
    location / {
        try_files $uri $uri/ /index.html;
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/plsql-workbench /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## SSL/TLS Configuration

### Using Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Auto-renewal Cron Job

```bash
# Add to crontab
sudo crontab -e

# Add this line:
0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

---

## Process Management

### Using Systemd

Create `/etc/systemd/system/plsql-workbench.service`:

```ini
[Unit]
Description=PL/SQL Workbench Gunicorn Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=plsql
Group=www-data
WorkingDirectory=/home/plsql/Oracle-SQL-Unwrapper
Environment="PATH=/home/plsql/Oracle-SQL-Unwrapper/venv/bin"
Environment="ORACLE_HOME=/opt/oracle/instantclient_19_8"
Environment="LD_LIBRARY_PATH=/opt/oracle/instantclient_19_8"
EnvironmentFile=/home/plsql/Oracle-SQL-Unwrapper/.env

ExecStart=/home/plsql/Oracle-SQL-Unwrapper/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --threads 2 \
    --bind 127.0.0.1:8000 \
    --timeout 300 \
    --access-logfile /home/plsql/Oracle-SQL-Unwrapper/logs/gunicorn-access.log \
    --error-logfile /home/plsql/Oracle-SQL-Unwrapper/logs/gunicorn-error.log \
    --log-level info \
    "backend.app:create_app('production')"

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Celery Worker Service

Create `/etc/systemd/system/plsql-celery.service`:

```ini
[Unit]
Description=PL/SQL Workbench Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=plsql
Group=www-data
WorkingDirectory=/home/plsql/Oracle-SQL-Unwrapper
Environment="PATH=/home/plsql/Oracle-SQL-Unwrapper/venv/bin"
EnvironmentFile=/home/plsql/Oracle-SQL-Unwrapper/.env

ExecStart=/home/plsql/Oracle-SQL-Unwrapper/venv/bin/celery -A backend.celery_app worker \
    --loglevel=info \
    --logfile=/home/plsql/Oracle-SQL-Unwrapper/logs/celery.log

[Install]
WantedBy=multi-user.target
```

### Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start and enable services
sudo systemctl start plsql-workbench
sudo systemctl enable plsql-workbench

sudo systemctl start plsql-celery
sudo systemctl enable plsql-celery

# Check status
sudo systemctl status plsql-workbench
sudo systemctl status plsql-celery

# View logs
sudo journalctl -u plsql-workbench -f
sudo journalctl -u plsql-celery -f
```

---

## Monitoring & Logging

### 1. Application Logs

```bash
# Application logs
tail -f /home/plsql/Oracle-SQL-Unwrapper/logs/app.log

# Gunicorn logs
tail -f /home/plsql/Oracle-SQL-Unwrapper/logs/gunicorn-access.log
tail -f /home/plsql/Oracle-SQL-Unwrapper/logs/gunicorn-error.log

# Nginx logs
tail -f /var/log/nginx/plsql-workbench-access.log
tail -f /var/log/nginx/plsql-workbench-error.log
```

### 2. Log Rotation

Create `/etc/logrotate.d/plsql-workbench`:

```
/home/plsql/Oracle-SQL-Unwrapper/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 plsql www-data
    sharedscripts
    postrotate
        systemctl reload plsql-workbench > /dev/null 2>&1 || true
    endscript
}
```

### 3. Health Checks

```bash
# Check application health
curl https://your-domain.com/api/health

# Check readiness (database, cache)
curl https://your-domain.com/api/health/ready

# Check metrics
curl https://your-domain.com/api/metrics

# Prometheus metrics
curl https://your-domain.com/api/metrics/prometheus
```

### 4. Monitoring with Prometheus (Optional)

Install Prometheus and configure scrape:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'plsql-workbench'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/api/metrics/prometheus'
```

---

## Backup & Maintenance

### Database Backups

#### Automated Daily Backup Script

Create `/home/plsql/backup-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/plsql/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="plsql_workbench"
DB_USER="plsql_user"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump -U "$DB_USER" -h localhost "$DB_NAME" | gzip > "$BACKUP_DIR/plsql_workbench_$DATE.sql.gz"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "plsql_workbench_*.sql.gz" -mtime +30 -delete

echo "Backup completed: plsql_workbench_$DATE.sql.gz"
```

Make executable and add to crontab:

```bash
chmod +x /home/plsql/backup-db.sh

# Add to crontab
crontab -e
# Add:
0 2 * * * /home/plsql/backup-db.sh >> /home/plsql/logs/backup.log 2>&1
```

#### Restore from Backup

```bash
# Stop application
sudo systemctl stop plsql-workbench

# Restore database
gunzip -c /home/plsql/backups/plsql_workbench_20240120_020000.sql.gz | \
    psql -U plsql_user -h localhost -d plsql_workbench

# Start application
sudo systemctl start plsql-workbench
```

### Application Updates

```bash
# Stop services
sudo systemctl stop plsql-workbench plsql-celery

# Switch to plsql user
sudo su - plsql
cd Oracle-SQL-Unwrapper

# Backup current version
cp -r . ../Oracle-SQL-Unwrapper-backup-$(date +%Y%m%d)

# Pull updates
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt --upgrade

# Run migrations
alembic upgrade head

# Exit plsql user
exit

# Restart services
sudo systemctl start plsql-workbench plsql-celery

# Verify
sudo systemctl status plsql-workbench
curl https://your-domain.com/api/health
```

---

## Security Checklist

- [ ] **Change all default passwords** (database, Redis, admin user)
- [ ] **Generate strong SECRET_KEY, ENCRYPTION_KEY, JWT_SECRET_KEY**
- [ ] **Enable HTTPS with valid SSL certificate**
- [ ] **Configure firewall** (UFW/firewalld)
  ```bash
  sudo ufw allow 22/tcp   # SSH
  sudo ufw allow 80/tcp   # HTTP (for Let's Encrypt)
  sudo ufw allow 443/tcp  # HTTPS
  sudo ufw enable
  ```
- [ ] **Disable PostgreSQL remote access** (unless needed)
- [ ] **Set secure file permissions**
  ```bash
  chmod 600 /home/plsql/Oracle-SQL-Unwrapper/.env
  chmod 700 /home/plsql/Oracle-SQL-Unwrapper/logs
  ```
- [ ] **Enable rate limiting** (Nginx + Flask-Limiter)
- [ ] **Configure security headers** (in Nginx)
- [ ] **Disable debug mode** (FLASK_DEBUG=False)
- [ ] **Disable API documentation** in production (ENABLE_API_DOCS=false)
- [ ] **Enable audit logging** for sensitive operations
- [ ] **Configure CORS properly** (only allow trusted origins)
- [ ] **Set up monitoring and alerting**
- [ ] **Enable database backups**
- [ ] **Review and limit user permissions**
- [ ] **Keep system and dependencies updated**

---

## Troubleshooting

### Application Won't Start

```bash
# Check service status
sudo systemctl status plsql-workbench

# Check logs
sudo journalctl -u plsql-workbench -n 100 --no-pager

# Check Gunicorn logs
tail -100 /home/plsql/Oracle-SQL-Unwrapper/logs/gunicorn-error.log

# Test manually
sudo su - plsql
cd Oracle-SQL-Unwrapper
source venv/bin/activate
python backend/app.py
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -h localhost -U plsql_user -d plsql_workbench

# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -100 /var/log/postgresql/postgresql-13-main.log
```

### Redis Connection Issues

```bash
# Test Redis connection
redis-cli
AUTH your_redis_password_here
PING

# Check Redis status
sudo systemctl status redis

# Check Redis logs
sudo tail -100 /var/log/redis/redis-server.log
```

### Nginx Issues

```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx status
sudo systemctl status nginx

# Check Nginx logs
sudo tail -100 /var/log/nginx/plsql-workbench-error.log
```

### High Memory Usage

```bash
# Check processes
ps aux | grep -E 'gunicorn|celery|postgres|redis'

# Reduce Gunicorn workers (edit service file)
sudo nano /etc/systemd/system/plsql-workbench.service
# Change --workers to 2 instead of 4

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart plsql-workbench
```

### Slow Query Performance

```bash
# Enable query logging in PostgreSQL
# Edit postgresql.conf
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000  # Log queries taking >1s

# Analyze slow queries
sudo tail -f /var/log/postgresql/postgresql-13-main.log | grep "duration:"
```

### Certificate Renewal Fails

```bash
# Test renewal
sudo certbot renew --dry-run

# Check certbot logs
sudo tail -100 /var/log/letsencrypt/letsencrypt.log

# Manually renew
sudo certbot renew --force-renewal
```

---

## Support and Resources

- **Documentation**: See `README.md`, `IMPLEMENTATION_GUIDE.md`
- **GitHub Issues**: Report bugs and feature requests
- **Logs**: Check application, Gunicorn, Nginx, PostgreSQL logs
- **Health Checks**: Monitor `/api/health`, `/api/health/ready`, `/api/metrics`

---

**Last Updated**: 2025-11-20
**Version**: 1.0 (Phase 5 Production Ready)
