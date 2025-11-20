# PL/SQL Workbench - Technical Documentation

**Version:** 1.0 (Phase 5 - Production Ready)
**Last Updated:** 2025-11-20

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Core Features](#core-features)
4. [Technology Stack](#technology-stack)
5. [Database Schema](#database-schema)
6. [API Architecture](#api-architecture)
7. [Security Implementation](#security-implementation)
8. [Deployment Options](#deployment-options)
9. [Configuration Management](#configuration-management)
10. [Monitoring & Observability](#monitoring--observability)
11. [Scaling & Performance](#scaling--performance)
12. [Troubleshooting](#troubleshooting)

---

## Executive Summary

### What is PL/SQL Workbench?

PL/SQL Workbench is an **enterprise-grade Oracle database management platform** that combines PL/SQL code unwrapping, query execution, dashboard creation, and database administration tools into a single unified web application.

### Primary Capabilities

1. **PL/SQL Unwrapping** - Decode Oracle's wrapped/obfuscated PL/SQL code (11g-20c+)
2. **Database Connectivity** - Manage multiple Oracle database connections with encrypted credentials
3. **Query Management** - Execute SQL queries, save templates, track history
4. **Dashboard System** - Create, share, and manage interactive data dashboards with real-time data
5. **User Management** - Multi-user authentication with role-based access control
6. **API Platform** - RESTful API for programmatic access to all features

### Target Users

- **Database Administrators** - Manage Oracle databases, unwrap vendor code, execute queries
- **Developers** - Build dashboards, analyze data, reverse engineer wrapped code
- **Security Researchers** - Audit Oracle PL/SQL code for vulnerabilities
- **Data Analysts** - Create dashboards, export data, visualize metrics

### Production Readiness

This system includes:
- ✅ Complete authentication and authorization
- ✅ Production-grade security (encryption, rate limiting, HTTPS)
- ✅ Health checks and monitoring (Kubernetes-ready)
- ✅ Docker containerization
- ✅ Database migrations
- ✅ Comprehensive API documentation
- ✅ Background task processing (Celery)
- ✅ Horizontal scalability support

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet / VPN                        │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Load Balancer │ (Optional)
                    │  (AWS ELB/ALB)  │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        ┌───────▼────────┐       ┌───────▼────────┐
        │  Nginx (HTTPS) │       │  Nginx (HTTPS) │
        │  Reverse Proxy │       │  Reverse Proxy │
        └───────┬────────┘       └───────┬────────┘
                │                         │
                └────────────┬────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
┌───────▼────────┐                       ┌───────▼────────┐
│  Flask App     │◄──────────────────────┤  Flask App     │
│  (Gunicorn)    │   Load Balanced       │  (Gunicorn)    │
│  Port 8000     │                       │  Port 8000     │
└───────┬────────┘                       └───────┬────────┘
        │                                         │
        └────────────┬────────────────────────────┘
                     │
        ┌────────────┼────────────────────────────┐
        │            │                            │
┌───────▼────┐  ┌───▼────┐  ┌──────────┐  ┌─────▼──────┐
│ PostgreSQL │  │ Redis  │  │  Celery  │  │   Oracle   │
│ (Metadata) │  │ (Cache)│  │ Worker   │  │  Databases │
│            │  │        │  │          │  │  (Target)  │
└────────────┘  └────────┘  └──────────┘  └────────────┘
```

### Component Overview

#### **Frontend Layer**
- Single-page application (SPA) with modern JavaScript
- Responsive design (desktop, tablet, mobile)
- Dark theme UI (VS Code inspired)
- Real-time updates via AJAX

#### **Web Server Layer**
- **Nginx** - Reverse proxy, SSL/TLS termination, static file serving, rate limiting
- Load balancing across multiple application instances
- Security headers (HSTS, CSP, X-Frame-Options)

#### **Application Layer**
- **Flask 2.3+** - Python web framework
- **Gunicorn** - Production WSGI server (4 workers, 2 threads per worker)
- **Flask-JWT-Extended** - JWT authentication
- **Flask-Login** - Session management
- **SQLAlchemy 2.0** - ORM for metadata database

#### **Data Layer**
- **PostgreSQL 13+** - Application metadata (users, dashboards, queries)
- **Redis 6+** - Caching, rate limiting, Celery message broker
- **Oracle Database** - Target databases for unwrapping and querying

#### **Background Processing**
- **Celery** - Asynchronous task queue
- **Redis** - Message broker and result backend
- Scheduled tasks, email notifications, data exports

---

## Core Features

### 1. PL/SQL Unwrapping Engine

#### How It Works

Oracle's wrap utility obfuscates PL/SQL code using a multi-layer encoding:

1. **Text Encoding** - Character substitution using Oracle's proprietary character map (256-byte table)
2. **Base64 Encoding** - Encoded content is Base64 encoded
3. **zlib Compression** - Base64 content is compressed with zlib
4. **Header Addition** - 20-byte metadata header prepended

**Unwrapping Process:**

```python
def unwrap(wrapped_code):
    # 1. Parse wrapped format (hex header + base64 body)
    header, base64_content = parse_wrapped_format(wrapped_code)

    # 2. Decode Base64
    decoded_bytes = base64.b64decode(base64_content)

    # 3. Skip 20-byte Oracle header
    payload = decoded_bytes[20:]

    # 4. Character substitution (reverse Oracle's character map)
    substituted = character_substitution(payload, oracle_charmap)

    # 5. Decompress with zlib
    original_code = zlib.decompress(substituted)

    return original_code
```

**Supported Oracle Versions:**
- Oracle 11g (11.1, 11.2)
- Oracle 12c (12.1, 12.2)
- Oracle 18c
- Oracle 19c
- Oracle 20c
- Oracle 21c (likely compatible)

**Supported Object Types:**
- Packages (PACKAGE, PACKAGE BODY)
- Procedures (PROCEDURE)
- Functions (FUNCTION)
- Triggers (TRIGGER)
- Type Bodies (TYPE BODY)

#### API Endpoints

**Unwrap from Text:**
```bash
POST /api/unwrap
Content-Type: application/json

{
  "content": "a7 100\n4b4b4b4b..."  # Wrapped PL/SQL code
}

Response:
{
  "success": true,
  "unwrapped_code": "CREATE OR REPLACE PACKAGE BODY...",
  "object_type": "PACKAGE BODY",
  "lines": 245
}
```

**Unwrap from Database:**
```bash
POST /api/unwrap-from-db
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "connection_id": 1,
  "schema": "HR",
  "object_type": "PACKAGE BODY",
  "object_name": "EMPLOYEE_PKG"
}

Response:
{
  "success": true,
  "unwrapped_code": "...",
  "source_schema": "HR",
  "source_object": "EMPLOYEE_PKG"
}
```

### 2. User Authentication & Authorization

#### Authentication Flow

**Registration:**
```
User → POST /api/auth/register → Create User
                                → Send Verification Email
                                → Return JWT Tokens (if email verification disabled)
```

**Login:**
```
User → POST /api/auth/login → Validate Credentials
                            → Create Session Record
                            → Generate Access Token (1 hour)
                            → Generate Refresh Token (30 days)
                            → Return Tokens + User Info
```

**Token Refresh:**
```
User → POST /api/auth/refresh → Validate Refresh Token
                               → Generate New Access Token
                               → Return New Access Token
```

**Logout:**
```
User → POST /api/auth/logout → Revoke Session
                              → Add Token to Blacklist (if implemented)
```

#### Authorization Model

**Role-Based Access Control (RBAC):**

```
Users ──┬── Roles ──┬── Permissions
        │           │
        │           ├── read:dashboards
        │           ├── write:dashboards
        │           ├── delete:dashboards
        │           ├── manage:users
        │           └── admin:system
        │
        ├── admin (superuser)
        ├── power_user
        ├── analyst
        └── viewer
```

**Permission Checks:**
```python
@jwt_required()
@require_permission('write:dashboards')
def create_dashboard():
    # User must have 'write:dashboards' permission
    pass
```

**Owner-Based Access:**
```python
# User can only access/modify their own resources
def get_dashboard(dashboard_id):
    dashboard = Dashboard.query.get(dashboard_id)
    if dashboard.owner_id != current_user.id:
        abort(403, "Access denied")
```

#### Security Features

**Password Security:**
- **Hashing:** Argon2id (memory-hard, resistant to GPU attacks)
- **Requirements:** Min 8 chars, uppercase, lowercase, digits, special chars
- **Account Lockout:** 5 failed attempts → 30 minute lockout

**Token Security:**
- **Access Token:** Short-lived (1 hour)
- **Refresh Token:** Long-lived (30 days), can be revoked
- **Token Storage:** HTTPOnly cookies (web) or Authorization header (API)
- **CSRF Protection:** Enabled for cookie-based auth

**Session Management:**
- Session records in database with IP, user agent, last activity
- Multi-session support (user can have multiple active sessions)
- Session revocation on logout or password change

### 3. Oracle Database Connectivity

#### Connection Management

**Connection Storage:**
```python
class OracleConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'))
    name = db.Column(db.String(255))  # "Production HR DB"
    connection_type = db.Column(db.String(20))  # 'service_name', 'sid', 'tns'
    host = db.Column(db.String(255))
    port = db.Column(db.Integer, default=1521)
    service_name = db.Column(db.String(255))
    sid = db.Column(db.String(255))
    username = db.Column(db.String(255))
    password_encrypted = db.Column(db.Text)  # AES-256 encrypted
    is_active = db.Column(db.Boolean, default=True)
```

**Password Encryption:**
```python
from cryptography.fernet import Fernet

# Encryption
cipher = Fernet(ENCRYPTION_KEY)
encrypted = cipher.encrypt(password.encode())

# Decryption
decrypted = cipher.decrypt(encrypted).decode()
```

**Connection Pooling:**
```python
# cx_Oracle connection pool
pool = cx_Oracle.SessionPool(
    user=username,
    password=password,
    dsn=dsn,
    min=2,           # Minimum connections
    max=10,          # Maximum connections
    increment=1,     # Growth increment
    threaded=True
)
```

**Connection String Generation:**
```python
# Service Name
dsn = f"{host}:{port}/{service_name}"
# Example: "prod-db.example.com:1521/HRDB"

# SID
dsn = cx_Oracle.makedsn(host, port, sid=sid)
# Example: "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=...)...))"

# TNS
dsn = tns_name  # From tnsnames.ora
# Example: "PROD_HR"
```

#### Query Execution

**Synchronous Execution:**
```python
def execute_query(connection, sql, parameters=None):
    # 1. Get connection from pool
    conn = pool.acquire()
    cursor = conn.cursor()

    # 2. Set query timeout
    cursor.callproc("DBMS_LOCK.SLEEP", [0])  # Heartbeat

    # 3. Execute query
    start_time = time.time()
    cursor.execute(sql, parameters or {})

    # 4. Fetch results (paginated)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchmany(FETCH_SIZE)  # 1000 rows at a time

    # 5. Return results
    return {
        'columns': columns,
        'rows': rows,
        'execution_time': time.time() - start_time,
        'row_count': cursor.rowcount
    }
```

**Asynchronous Execution (Celery):**
```python
@celery.task
def execute_query_async(query_id, connection_id, sql):
    # Execute in background
    result = execute_query(connection, sql)

    # Store result in Redis
    cache.set(f'query_result:{query_id}', result, timeout=3600)

    # Notify user (WebSocket or polling)
    return query_id
```

### 4. Dashboard System

#### Architecture

**Dashboard Components:**
```
Dashboard
├── Metadata (title, description, category, tags)
├── Layout Config (grid system, columns, responsive breakpoints)
├── Access Control (private, team, organization, public)
├── Components (widgets)
│   ├── Charts (line, bar, pie, scatter, area)
│   ├── Tables (data grids with sorting, filtering)
│   ├── Metrics (KPIs, single values)
│   ├── Text (markdown, HTML)
│   └── Filters (date range, dropdown, search)
├── Data Sources (SQL queries, REST APIs, static data)
├── Shares (user/role sharing)
├── Versions (snapshot history)
└── Public Links (shareable URLs with optional passwords)
```

#### Component Types

**1. Chart Component:**
```json
{
  "id": 1,
  "type": "chart",
  "title": "Monthly Revenue",
  "config": {
    "chart_type": "line",
    "data_source_id": 1,
    "x_axis": "month",
    "y_axis": "revenue",
    "aggregation": "sum",
    "colors": ["#3498db", "#2ecc71"],
    "show_legend": true,
    "show_grid": true
  },
  "grid_position": {"x": 0, "y": 0, "w": 6, "h": 4}
}
```

**2. Metric Component:**
```json
{
  "type": "metric",
  "title": "Total Sales",
  "config": {
    "data_source_id": 2,
    "value_field": "total_sales",
    "format": "currency",
    "prefix": "$",
    "decimals": 2,
    "trend": "up",
    "comparison": {
      "value": 15.3,
      "period": "vs last month"
    }
  },
  "grid_position": {"x": 6, "y": 0, "w": 3, "h": 2}
}
```

**3. Table Component:**
```json
{
  "type": "table",
  "title": "Top Products",
  "config": {
    "data_source_id": 3,
    "columns": [
      {"field": "product_name", "header": "Product", "sortable": true},
      {"field": "quantity", "header": "Sold", "sortable": true},
      {"field": "revenue", "header": "Revenue", "format": "currency"}
    ],
    "page_size": 10,
    "enable_search": true,
    "enable_export": true
  },
  "grid_position": {"x": 0, "y": 4, "w": 12, "h": 6}
}
```

#### Data Source Types

**1. SQL Query:**
```json
{
  "type": "sql_query",
  "connection_id": 1,
  "query": "SELECT month, SUM(revenue) as revenue FROM sales WHERE year = :year GROUP BY month",
  "parameters": {
    "year": 2024
  },
  "cache_ttl": 300  // 5 minutes
}
```

**2. REST API:**
```json
{
  "type": "rest_api",
  "url": "https://api.example.com/metrics",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer token..."
  },
  "cache_ttl": 60
}
```

**3. Static Data:**
```json
{
  "type": "static",
  "data": {
    "columns": ["month", "value"],
    "rows": [
      ["Jan", 100],
      ["Feb", 150]
    ]
  }
}
```

#### Dashboard Sharing

**Access Levels:**
- **Private** - Only owner can access
- **Team** - Shared with specific users (read or edit)
- **Organization** - All users in organization can access
- **Public** - Anyone with link can access (optional password)

**Public Link Generation:**
```python
def create_public_link(dashboard_id, password=None, expires_days=None):
    # Generate unique token
    token = secrets.token_urlsafe(32)

    # Hash password if provided
    password_hash = hash_password(password) if password else None

    # Set expiration
    expires_at = datetime.now() + timedelta(days=expires_days) if expires_days else None

    # Update dashboard
    dashboard.public_token = token
    dashboard.public_password_hash = password_hash
    dashboard.public_link_expires_at = expires_at

    return f"https://your-domain.com/public/dashboards/{token}"
```

#### Version Control

**Automatic Versioning:**
```python
def publish_dashboard(dashboard_id):
    dashboard = Dashboard.query.get(dashboard_id)

    # Create version snapshot
    version = DashboardVersion(
        dashboard_id=dashboard_id,
        version_number=dashboard.version + 1,
        title=dashboard.title,
        description=f"Published on {datetime.now()}",
        snapshot_data={
            'layout': dashboard.layout_config,
            'components': [c.to_dict() for c in dashboard.components],
            'data_sources': [ds.to_dict() for ds in dashboard.data_sources]
        },
        created_by=current_user.id
    )
    db.session.add(version)

    # Update dashboard
    dashboard.version += 1
    dashboard.is_published = True
    db.session.commit()
```

**Restore from Version:**
```python
def restore_version(dashboard_id, version_number):
    version = DashboardVersion.query.filter_by(
        dashboard_id=dashboard_id,
        version_number=version_number
    ).first()

    # Restore snapshot data
    dashboard = version.dashboard
    dashboard.layout_config = version.snapshot_data['layout']

    # Recreate components
    dashboard.components.delete()
    for comp_data in version.snapshot_data['components']:
        component = DashboardComponent(**comp_data)
        dashboard.components.append(component)

    db.session.commit()
```

#### Dashboard Templates

**Template Library:**
- Pre-built dashboard templates for common use cases
- Community-contributed templates
- Template marketplace (future)

**Template Categories:**
- Analytics (web analytics, sales analytics, marketing)
- Operations (system monitoring, DevOps, infrastructure)
- Finance (P&L, cash flow, budget tracking)
- HR (employee metrics, recruitment, performance)
- Custom (user-created templates)

**Creating Template from Dashboard:**
```python
def create_template_from_dashboard(dashboard_id):
    dashboard = Dashboard.query.get(dashboard_id)

    template = DashboardTemplate(
        name=dashboard.title,
        description=dashboard.description,
        category=dashboard.category,
        tags=dashboard.tags,
        template_data={
            'layout': dashboard.layout_config,
            'components': [c.to_dict(exclude_data=True) for c in dashboard.components],
            'data_sources': [ds.to_dict(exclude_connection=True) for ds in dashboard.data_sources]
        },
        thumbnail_url=generate_thumbnail(dashboard),
        is_featured=False,
        created_by=current_user.id
    )
    db.session.add(template)
    db.session.commit()

    return template
```

**Using Template:**
```python
def create_dashboard_from_template(template_id, user_id):
    template = DashboardTemplate.query.get(template_id)

    # Create new dashboard from template
    dashboard = Dashboard(
        owner_id=user_id,
        title=f"{template.name} (Copy)",
        description=template.description,
        category=template.category,
        tags=template.tags,
        layout_config=template.template_data['layout']
    )
    db.session.add(dashboard)
    db.session.flush()

    # Create components
    for comp_data in template.template_data['components']:
        component = DashboardComponent(
            dashboard_id=dashboard.id,
            **comp_data
        )
        db.session.add(component)

    # Increment template usage count
    template.usage_count += 1

    db.session.commit()
    return dashboard
```

### 5. Query Management

#### Saved Queries

**Organization:**
```
Saved Queries
├── Personal Queries (private to user)
├── Team Queries (shared with team)
├── Organization Queries (shared with all)
└── Folders
    ├── DDL Scripts
    ├── Performance Tuning
    ├── Data Analysis
    └── Reports
```

**Query Templates:**
- 40+ pre-built SQL templates
- Organized by category (DDL, DML, PL/SQL, Admin, Performance)
- Parameterized with placeholders
- Search and filter capabilities

**Template Example:**
```json
{
  "name": "Find Expensive Queries",
  "category": "Performance",
  "description": "Find queries with high CPU or I/O usage",
  "sql": "SELECT sql_id, sql_text, executions, cpu_time, disk_reads\nFROM v$sql\nWHERE cpu_time > :cpu_threshold\nORDER BY cpu_time DESC\nFETCH FIRST :limit ROWS ONLY",
  "parameters": [
    {"name": "cpu_threshold", "type": "number", "default": 1000000},
    {"name": "limit", "type": "number", "default": 50}
  ],
  "tags": ["performance", "monitoring", "tuning"]
}
```

#### Query History

**Tracking:**
```python
class QueryHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'))
    connection_id = db.Column(db.Integer, ForeignKey('oracle_connections.id'))
    sql_text = db.Column(db.Text)
    execution_time = db.Column(db.Float)  # seconds
    row_count = db.Column(db.Integer)
    status = db.Column(db.String(20))  # 'success', 'error', 'cancelled'
    error_message = db.Column(db.Text)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Retention:**
- Keep history for 90 days (configurable)
- Automatic cleanup via scheduled task
- Export history before deletion

---

## Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.9+ | Programming language |
| **Flask** | 2.3.3 | Web framework |
| **SQLAlchemy** | 2.0.20 | ORM for metadata database |
| **cx_Oracle** | 8.3.0 | Oracle database driver |
| **Flask-JWT-Extended** | 4.5.2 | JWT authentication |
| **Flask-Login** | 0.6.2 | Session management |
| **Flask-Mail** | 0.9.1 | Email sending |
| **Flask-Caching** | 2.1.0 | Response caching |
| **Flask-Limiter** | 3.5.0 | Rate limiting |
| **Flask-CORS** | 4.0.0 | CORS handling |
| **Flasgger** | 0.9.7.1 | Swagger/OpenAPI docs |
| **Celery** | 5.3.4 | Background tasks |
| **Redis** | 5.0.1 | Cache & message broker |
| **Gunicorn** | 21.2.0 | WSGI server |
| **cryptography** | 41.0.4 | Encryption (Fernet) |
| **Alembic** | 1.12.0 | Database migrations |

### Database

| Technology | Version | Purpose |
|------------|---------|---------|
| **PostgreSQL** | 13+ | Metadata storage (users, dashboards, queries) |
| **Redis** | 6+ | Caching, rate limiting, Celery broker |
| **Oracle Database** | 11g-21c | Target databases for unwrapping/querying |

### Infrastructure

| Technology | Version | Purpose |
|------------|---------|---------|
| **Nginx** | 1.18+ | Reverse proxy, SSL termination |
| **Docker** | 20.10+ | Containerization |
| **Docker Compose** | 1.29+ | Multi-container orchestration |

### Frontend

| Technology | Purpose |
|------------|---------|
| **HTML5/CSS3** | Structure and styling |
| **JavaScript (ES6+)** | Client-side logic |
| **Bootstrap 5** | Responsive UI framework |
| **jQuery** | DOM manipulation (legacy) |
| **Chart.js** | Data visualization |

### Development & Operations

| Tool | Purpose |
|------|---------|
| **pytest** | Unit & integration testing |
| **black** | Code formatting |
| **flake8** | Code linting |
| **Prometheus** | Metrics collection |
| **Grafana** | Metrics visualization (optional) |

---

## Database Schema

### Application Metadata (PostgreSQL)

#### Core Tables

**1. users**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- Argon2id
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(100),
    email_verification_sent_at TIMESTAMP,
    password_reset_token VARCHAR(100),
    password_reset_sent_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_users_email (email),
    INDEX idx_users_username (username)
);
```

**2. roles**
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(80) UNIQUE NOT NULL,
    description TEXT,
    permissions JSON,  -- {"read:dashboards": true, "write:dashboards": true}
    created_at TIMESTAMP DEFAULT NOW()
);
```

**3. user_roles (many-to-many)**
```sql
CREATE TABLE user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);
```

**4. sessions**
```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    last_activity TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_sessions_token (session_token),
    INDEX idx_sessions_user (user_id)
);
```

**5. oracle_connections**
```sql
CREATE TABLE oracle_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    connection_type VARCHAR(20),  -- 'service_name', 'sid', 'tns'
    host VARCHAR(255),
    port INTEGER DEFAULT 1521,
    service_name VARCHAR(255),
    sid VARCHAR(255),
    username VARCHAR(255),
    password_encrypted TEXT,  -- Fernet encrypted
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_connections_user (user_id)
);
```

**6. query_history**
```sql
CREATE TABLE query_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    connection_id INTEGER REFERENCES oracle_connections(id) ON DELETE SET NULL,
    sql_text TEXT NOT NULL,
    execution_time FLOAT,  -- seconds
    row_count INTEGER,
    status VARCHAR(20),  -- 'success', 'error', 'cancelled'
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_query_history_user (user_id),
    INDEX idx_query_history_executed (executed_at DESC)
);
```

**7. saved_queries**
```sql
CREATE TABLE saved_queries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sql_text TEXT NOT NULL,
    folder VARCHAR(255),
    tags JSON,  -- ["tag1", "tag2"]
    is_template BOOLEAN DEFAULT FALSE,
    is_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_saved_queries_user (user_id),
    INDEX idx_saved_queries_folder (folder)
);
```

**8. dashboards** (Phase 5)
```sql
CREATE TABLE dashboards (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    tags JSON,
    access_level VARCHAR(20) DEFAULT 'private',  -- 'private', 'team', 'organization', 'public'
    public_token VARCHAR(64) UNIQUE,
    public_password_hash VARCHAR(255),
    public_link_expires_at TIMESTAMP,
    layout_config JSON,  -- Grid layout configuration
    theme VARCHAR(50) DEFAULT 'default',
    is_published BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,
    INDEX idx_dashboards_owner (owner_id),
    INDEX idx_dashboards_slug (slug),
    INDEX idx_dashboards_access_level (access_level),
    INDEX idx_dashboards_published (is_published),
    INDEX idx_dashboards_category (category)
);
```

**9. dashboard_components** (Phase 5)
```sql
CREATE TABLE dashboard_components (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER REFERENCES dashboards(id) ON DELETE CASCADE,
    component_type VARCHAR(50) NOT NULL,  -- 'chart', 'table', 'metric', 'text', 'filter'
    title VARCHAR(255),
    description TEXT,
    grid_position JSON,  -- {"x": 0, "y": 0, "w": 6, "h": 4}
    config JSON,  -- Component-specific configuration
    order_index INTEGER DEFAULT 0,
    is_visible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_components_dashboard (dashboard_id)
);
```

**10. dashboard_data_sources** (Phase 5)
```sql
CREATE TABLE dashboard_data_sources (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER REFERENCES dashboards(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'sql_query', 'rest_api', 'static'
    connection_id INTEGER REFERENCES oracle_connections(id) ON DELETE SET NULL,
    query TEXT,
    config JSON,  -- Source-specific config (API URL, headers, etc.)
    cache_ttl INTEGER DEFAULT 300,  -- seconds
    last_refresh TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_data_sources_dashboard (dashboard_id)
);
```

**11. dashboard_shares** (Phase 5)
```sql
CREATE TABLE dashboard_shares (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER REFERENCES dashboards(id) ON DELETE CASCADE,
    shared_with_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    shared_with_role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_level VARCHAR(20),  -- 'view', 'edit', 'admin'
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_shares_dashboard (dashboard_id),
    INDEX idx_shares_user (shared_with_user_id)
);
```

**12. dashboard_versions** (Phase 5)
```sql
CREATE TABLE dashboard_versions (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER REFERENCES dashboards(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    title VARCHAR(255),
    description TEXT,
    snapshot_data JSON,  -- Complete dashboard state
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (dashboard_id, version_number),
    INDEX idx_versions_dashboard (dashboard_id)
);
```

**13. dashboard_templates** (Phase 5)
```sql
CREATE TABLE dashboard_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    tags JSON,
    template_data JSON,  -- Serialized dashboard structure
    thumbnail_url VARCHAR(500),
    is_featured BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_templates_category (category),
    INDEX idx_templates_featured (is_featured),
    INDEX idx_templates_usage (usage_count DESC)
);
```

**14. audit_logs**
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,  -- 'login', 'create_dashboard', 'delete_query', etc.
    resource_type VARCHAR(50),  -- 'dashboard', 'query', 'connection'
    resource_id INTEGER,
    details JSON,  -- Additional context
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_created (created_at DESC),
    INDEX idx_audit_action (action)
);
```

### Redis Schema

#### Cache Keys

```
# User sessions
session:{session_token} → {user_id, expires_at, ...}

# Query results
query_result:{query_id} → {columns, rows, ...}

# Dashboard data
dashboard_data:{dashboard_id}:{component_id} → {data, cached_at}

# Rate limiting
ratelimit:{ip}:{endpoint} → {count, reset_time}

# Connection pools
connection_pool:{connection_id} → {pool_object}
```

---

## API Architecture

### RESTful Endpoints

**Total:** 70+ endpoints across 13 categories

#### Endpoint Categories

1. **Authentication** (`/api/auth`) - 11 endpoints
   - Registration, login, logout, token refresh
   - Password reset, email verification
   - User profile management

2. **Users** (`/api/users`) - 6 endpoints
   - User CRUD operations
   - Role assignment
   - User search and filtering

3. **Connections** (`/api/connections`) - 6 endpoints
   - Connection CRUD
   - Connection testing
   - Schema browsing

4. **Unwrapping** (`/api/unwrap`) - 2 endpoints
   - Unwrap from text
   - Unwrap from database

5. **Queries** (`/api/queries`) - 8 endpoints
   - Query execution
   - Query history
   - Saved queries CRUD

6. **Templates** (`/api/templates`) - 3 endpoints
   - List templates
   - Search templates
   - Load template

7. **Dashboards** (`/api/dashboards`) - 11 endpoints
   - Dashboard CRUD
   - Publish/unpublish
   - Duplicate dashboard
   - Version management

8. **Dashboard Components** (`/api/dashboards/:id/components`) - 4 endpoints
   - Component CRUD
   - Component reordering

9. **Dashboard Data Sources** (`/api/dashboards/:id/data-sources`) - 5 endpoints
   - Data source CRUD
   - Data refresh

10. **Dashboard Sharing** (`/api/dashboards/:id/shares`) - 5 endpoints
    - Share management
    - Public link generation

11. **Dashboard Templates** (`/api/templates`) - 7 endpoints
    - Template library browsing
    - Create/use templates

12. **Roles** (`/api/roles`) - 4 endpoints
    - Role CRUD (admin only)

13. **Health & Monitoring** (`/api/health`) - 6 endpoints
    - Health checks (ready, live)
    - Metrics (application, Prometheus)
    - System info

### API Patterns

#### Request/Response Format

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed",
  "pagination": {  // For list endpoints
    "page": 1,
    "per_page": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Invalid input data",
  "details": {
    "field": "email",
    "issue": "Email already registered"
  }
}
```

#### Pagination

**Query Parameters:**
```
?page=1              # Page number (1-indexed)
&per_page=20         # Items per page (max: 100)
&sort_by=created_at  # Sort field
&sort_order=desc     # asc or desc
```

#### Filtering

**Query Parameters:**
```
?category=analytics              # Exact match
&tags=finance,reports            # Any of (OR)
&search=revenue                  # Full-text search
&is_published=true               # Boolean filter
&created_after=2024-01-01        # Date filter
```

#### Rate Limiting

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642089600
```

**Limits:**
- Authentication: 5 requests/minute
- Public endpoints: 50 requests/minute
- API (general): 100 requests/minute
- API (strict): 1000 requests/hour

---

## Security Implementation

### 1. Authentication Security

#### Password Hashing
```python
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=2,       # Number of iterations
    memory_cost=65536, # 64 MiB memory
    parallelism=1,     # Single thread
    hash_len=32,       # 32-byte hash
    salt_len=16        # 16-byte salt
)

# Hash
hashed = ph.hash(password)

# Verify
ph.verify(hashed, password)
```

#### JWT Tokens
```python
from flask_jwt_extended import create_access_token

access_token = create_access_token(
    identity=user.id,
    expires_delta=timedelta(hours=1),
    additional_claims={
        'username': user.username,
        'roles': [r.name for r in user.roles]
    }
)
```

### 2. Data Encryption

#### Database Password Encryption
```python
from cryptography.fernet import Fernet

# Generate key once (store in .env)
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt
encrypted = cipher.encrypt(password.encode())

# Decrypt
decrypted = cipher.decrypt(encrypted).decode()
```

#### Encryption Key Rotation
```python
def rotate_encryption_key(old_key, new_key):
    old_cipher = Fernet(old_key)
    new_cipher = Fernet(new_key)

    # Re-encrypt all passwords
    for conn in OracleConnection.query.all():
        decrypted = old_cipher.decrypt(conn.password_encrypted)
        conn.password_encrypted = new_cipher.encrypt(decrypted)

    db.session.commit()
```

### 3. Input Validation

#### SQL Injection Prevention
```python
# GOOD: Parameterized query
cursor.execute("SELECT * FROM users WHERE id = :id", {'id': user_id})

# BAD: String concatenation (vulnerable to SQL injection)
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

#### Input Sanitization
```python
from bleach import clean

def sanitize_html(html_input):
    """Remove dangerous HTML tags"""
    return clean(
        html_input,
        tags=['p', 'br', 'strong', 'em', 'a'],
        attributes={'a': ['href', 'title']},
        strip=True
    )
```

### 4. HTTPS/TLS

#### Nginx SSL Configuration
```nginx
ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_stapling on;
ssl_stapling_verify on;
```

### 5. Security Headers

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'" always;
```

### 6. Rate Limiting

#### Application-Level (Flask-Limiter)
```python
from flask_limiter import Limiter

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/0"
)

@app.route('/api/auth/login')
@limiter.limit("5 per minute")
def login():
    pass
```

#### Nginx-Level
```nginx
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;

location /api/auth/login {
    limit_req zone=auth_limit burst=2 nodelay;
    proxy_pass http://app;
}
```

### 7. CSRF Protection

```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# Exempt API endpoints (use JWT instead)
csrf.exempt('/api/*')
```

---

## Deployment Options

### Option 1: Traditional Deployment (VPS/Bare Metal)

**Use Case:** Full control, existing infrastructure

**Steps:**
1. Install PostgreSQL, Redis, Python, Nginx
2. Clone repository and set up virtual environment
3. Configure `.env` with production settings
4. Run database migrations
5. Set up systemd services for Flask and Celery
6. Configure Nginx reverse proxy with SSL
7. Set up automated backups and monitoring

**Pros:**
- Full control over infrastructure
- No containerization overhead
- Direct access to logs and debugging

**Cons:**
- Manual dependency management
- Platform-specific configuration
- More complex updates

**Best For:** Single-server deployments, legacy infrastructure

See: `DEPLOYMENT.md` for complete instructions

### Option 2: Docker Deployment

**Use Case:** Containerized environments, consistent deployment

**Steps:**
1. Install Docker and Docker Compose
2. Configure `.env` with production settings
3. Run `docker compose up -d`
4. Access application on configured port

**Pros:**
- Consistent environment across dev/staging/prod
- Easy rollback (versioned images)
- Simple updates (`docker compose pull && docker compose up -d`)
- Includes all dependencies

**Cons:**
- Docker overhead
- Requires Docker expertise
- Additional layer of abstraction

**Best For:** Cloud deployments, CI/CD pipelines, multi-environment setups

See: `DOCKER.md` for complete instructions

### Option 3: Kubernetes Deployment

**Use Case:** Large-scale, highly available deployments

**Components:**
- Deployment for Flask application (3+ replicas)
- StatefulSet for PostgreSQL (with persistent volumes)
- StatefulSet for Redis
- Deployment for Celery workers
- Ingress for external access
- ConfigMaps for configuration
- Secrets for sensitive data

**Pros:**
- Auto-scaling
- Self-healing (automatic restarts)
- Rolling updates with zero downtime
- Service discovery
- Load balancing

**Cons:**
- Complex setup
- Kubernetes expertise required
- Higher resource requirements
- Overkill for small deployments

**Best For:** Enterprise deployments, high-traffic applications, multi-region

### Option 4: Cloud Platform Deployment

#### AWS

**Services:**
- **Elastic Beanstalk** - Application hosting
- **RDS PostgreSQL** - Managed database
- **ElastiCache Redis** - Managed cache
- **Application Load Balancer** - Load balancing
- **Certificate Manager** - SSL certificates
- **CloudWatch** - Monitoring

#### Google Cloud Platform

**Services:**
- **Cloud Run** - Serverless containers
- **Cloud SQL** - Managed PostgreSQL
- **Memorystore** - Managed Redis
- **Cloud Load Balancing**
- **Cloud Monitoring**

#### Azure

**Services:**
- **App Service** - Web app hosting
- **Database for PostgreSQL** - Managed database
- **Azure Cache for Redis**
- **Application Gateway** - Load balancing
- **Application Insights** - Monitoring

---

## Configuration Management

### Environment Variables

**Complete List (128 settings):**

See `.env.example` for all available settings organized by category:

1. **Flask Environment** (3 settings)
2. **Security Keys** (5 settings)
3. **Database Configuration** (9 settings)
4. **Redis Configuration** (2 settings)
5. **Email/SMTP Configuration** (7 settings)
6. **CORS** (1 setting)
7. **Unwrapper Settings** (2 settings)
8. **Query Execution** (2 settings)
9. **Dashboard Settings** (6 settings)
10. **Rate Limiting** (5 settings)
11. **Security Headers** (4 settings)
12. **Monitoring** (3 settings)
13. **Background Tasks** (2 settings)
14. **File Uploads** (2 settings)
15. **Logging** (2 settings)
16. **Feature Flags** (3 settings)

### Configuration by Environment

**Development:**
```ini
FLASK_ENV=development
FLASK_DEBUG=True
ENABLE_API_DOCS=true
RATELIMIT_ENABLED=false
DATABASE_URL=sqlite:///plsql_workbench.db
```

**Staging:**
```ini
FLASK_ENV=production
FLASK_DEBUG=False
ENABLE_API_DOCS=true  # Can keep enabled for testing
RATELIMIT_ENABLED=true
DATABASE_URL=postgresql://user:pass@staging-db:5432/plsql
```

**Production:**
```ini
FLASK_ENV=production
FLASK_DEBUG=False
ENABLE_API_DOCS=false  # Security: disable public docs
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true
RATELIMIT_ENABLED=true
DATABASE_URL=postgresql://user:pass@prod-db:5432/plsql
```

---

## Monitoring & Observability

### Health Check Endpoints

#### Basic Health (`/api/health`)
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "version": "1.0.0"
}
```

#### Readiness Check (`/api/health/ready`)
```json
{
  "ready": true,
  "checks": {
    "database": "ok",
    "cache": "ok"
  },
  "timestamp": "2024-01-20T10:30:00Z"
}
```

#### Liveness Check (`/api/health/live`)
```json
{
  "alive": true,
  "uptime": 86400,
  "timestamp": "2024-01-20T10:30:00Z"
}
```

### Metrics Endpoints

#### Application Metrics (`/api/metrics`)
```json
{
  "database": {
    "users": 1250,
    "dashboards": 450,
    "dashboards_published": 320,
    "templates": 45
  },
  "system": {
    "cpu_percent": 25.3,
    "memory_percent": 42.1,
    "memory_available_mb": 2048,
    "disk_percent": 65.5,
    "disk_free_gb": 50.2
  },
  "timestamp": "2024-01-20T10:30:00Z"
}
```

#### Prometheus Metrics (`/api/metrics/prometheus`)
```
# HELP plsql_workbench_users_total Total number of users
# TYPE plsql_workbench_users_total gauge
plsql_workbench_users_total 1250

# HELP plsql_workbench_dashboards_total Total number of dashboards
# TYPE plsql_workbench_dashboards_total gauge
plsql_workbench_dashboards_total 450

# HELP plsql_workbench_http_requests_total Total HTTP requests
# TYPE plsql_workbench_http_requests_total counter
plsql_workbench_http_requests_total{method="GET",endpoint="/api/dashboards",status="200"} 12450
```

### Logging

**Log Levels:**
- DEBUG - Detailed diagnostic info
- INFO - General informational messages
- WARNING - Warning messages
- ERROR - Error messages
- CRITICAL - Critical failures

**Log Format:**
```
[2024-01-20 10:30:00,123] INFO in app: User john@example.com logged in from 192.168.1.100
[2024-01-20 10:30:15,456] ERROR in queries: Query execution failed: ORA-00942: table or view does not exist
```

**Log Locations:**
- Application: `logs/app.log`
- Gunicorn Access: `logs/gunicorn-access.log`
- Gunicorn Error: `logs/gunicorn-error.log`
- Celery: `logs/celery.log`
- Nginx Access: `/var/log/nginx/plsql-workbench-access.log`
- Nginx Error: `/var/log/nginx/plsql-workbench-error.log`

### Alerting (Optional)

**Example Prometheus Alerts:**
```yaml
groups:
  - name: plsql_workbench
    rules:
      - alert: HighErrorRate
        expr: rate(plsql_workbench_http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseDown
        expr: plsql_workbench_database_up == 0
        for: 1m
        annotations:
          summary: "Database connection is down"
```

---

## Scaling & Performance

### Horizontal Scaling

**Application Servers:**
```
Load Balancer
    ├── App Server 1 (Gunicorn 4 workers)
    ├── App Server 2 (Gunicorn 4 workers)
    └── App Server 3 (Gunicorn 4 workers)
```

**Session Management:**
- Use Redis for session storage (not in-memory)
- Enables session sharing across app servers

**Database Connection Pooling:**
```python
# Each app server maintains its own pool
SQLALCHEMY_POOL_SIZE = 10          # Per server
SQLALCHEMY_MAX_OVERFLOW = 20       # Per server

# With 3 app servers:
# Total connections: 3 × (10 + 20) = 90 max
```

### Vertical Scaling

**Gunicorn Workers:**
```
# Formula: (2 × CPU_cores) + 1
# 4-core server: (2 × 4) + 1 = 9 workers

gunicorn --workers 9 --threads 2
```

**Database:**
- Increase `shared_buffers` (25% of RAM)
- Increase `effective_cache_size` (50-75% of RAM)
- Add indexes for common queries

**Redis:**
- Increase `maxmemory` (e.g., 2GB)
- Use Redis Cluster for sharding (if needed)

### Caching Strategy

**Levels:**

1. **Browser Cache** (Static assets)
   ```nginx
   location /static/ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

2. **Redis Cache** (Query results, dashboard data)
   ```python
   @cache.memoize(timeout=300)  # 5 minutes
   def get_dashboard_data(dashboard_id):
       return fetch_from_database(dashboard_id)
   ```

3. **Database Query Cache** (PostgreSQL)
   ```sql
   -- Materialized views for expensive queries
   CREATE MATERIALIZED VIEW dashboard_metrics AS
   SELECT ...;

   REFRESH MATERIALIZED VIEW dashboard_metrics;
   ```

### Performance Optimization

**Database:**
- Index commonly queried fields
- Use EXPLAIN ANALYZE to identify slow queries
- Implement pagination (don't fetch all rows)
- Use connection pooling

**Application:**
- Minimize N+1 queries (use `joinedload()`)
- Lazy load relationships when possible
- Use background tasks for slow operations
- Compress responses (gzip)

**Frontend:**
- Minify JavaScript/CSS
- Use CDN for static assets
- Lazy load images
- Debounce search inputs

---

## Troubleshooting

### Common Issues

#### Issue 1: Application Won't Start

**Symptoms:**
- `systemctl status plsql-workbench` shows "failed"
- Port already in use error

**Diagnosis:**
```bash
# Check logs
sudo journalctl -u plsql-workbench -n 100

# Check if port is in use
sudo netstat -tulpn | grep 8000

# Test configuration
python -m backend.app
```

**Solutions:**
- Check `.env` configuration
- Ensure PostgreSQL and Redis are running
- Verify Oracle Instant Client is installed
- Check file permissions

#### Issue 2: Database Connection Failed

**Symptoms:**
- "SQLALCHEMY_DATABASE_URI not configured"
- "Connection refused"

**Diagnosis:**
```bash
# Test PostgreSQL connection
psql -h localhost -U plsql_user -d plsql_workbench

# Check PostgreSQL status
sudo systemctl status postgresql

# Verify DATABASE_URL in .env
grep DATABASE_URL .env
```

**Solutions:**
- Ensure PostgreSQL is running
- Check credentials in `.env`
- Verify database exists
- Check firewall rules

#### Issue 3: Oracle Connection Fails

**Symptoms:**
- "ORA-12154: TNS:could not resolve the connect identifier"
- "ORA-12541: TNS:no listener"

**Diagnosis:**
```bash
# Check Oracle Instant Client
echo $ORACLE_HOME
echo $LD_LIBRARY_PATH

# Test connection
sqlplus username/password@host:1521/service_name

# Check listener
lsnrctl status
```

**Solutions:**
- Install Oracle Instant Client
- Set environment variables (ORACLE_HOME, LD_LIBRARY_PATH)
- Verify Oracle listener is running
- Check connection details (host, port, service name)

#### Issue 4: High Memory Usage

**Symptoms:**
- Application consumes excessive memory
- OOM killer terminates process

**Diagnosis:**
```bash
# Check memory usage
free -h
docker stats  # If using Docker

# Check process memory
ps aux | grep gunicorn
```

**Solutions:**
- Reduce Gunicorn workers
- Decrease database pool size
- Implement pagination for large queries
- Clear old query history
- Add memory limits (Docker/systemd)

#### Issue 5: Slow Performance

**Symptoms:**
- Requests take >5 seconds
- Database queries timeout

**Diagnosis:**
```bash
# Check slow queries (PostgreSQL)
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# Check application logs
tail -f logs/app.log | grep "execution_time"

# Check system resources
top
iotop
```

**Solutions:**
- Add database indexes
- Optimize SQL queries
- Enable query result caching
- Increase database resources
- Scale horizontally (add app servers)

---

## Additional Documentation

- **API.md** - Complete API reference with examples
- **DEPLOYMENT.md** - Production deployment guide (traditional)
- **DOCKER.md** - Docker deployment guide
- **CLAUDE.md** - AI assistant development guide
- **IMPLEMENTATION_GUIDE.md** - Feature implementation roadmap

---

## Support & Contributing

### Getting Help

1. **Documentation** - Read this file and linked docs
2. **GitHub Issues** - Report bugs and request features
3. **Health Checks** - Monitor `/api/health` and `/api/metrics`

### Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Follow PEP 8 style guide
5. Submit a pull request

### License

MIT License - See LICENSE file for details

---

**Built for the Oracle community by developers who understand the challenges of working with Oracle databases.**

**⭐ Star this repo if you find it useful!**

---

**Version:** 1.0.0 (Phase 5 - Production Ready)
**Last Updated:** 2025-11-20
**Repository:** https://github.com/RemmyLee/Oracle-SQL-Unwrapper
