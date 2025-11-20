# API Documentation Guide

## Overview

The PL/SQL Workbench provides a comprehensive RESTful API for all platform features including PL/SQL unwrapping, query management, dashboard creation, and system administration.

## API Documentation Access

### Interactive Swagger UI

**Development Environment:**
```
http://localhost:8000/api/docs/
```

**Production Environment (if enabled):**
```
https://your-domain.com/api/docs/
```

> **Security Note**: API documentation is **disabled by default in production** for security reasons. Enable only if needed for internal documentation purposes by setting `ENABLE_API_DOCS=true` in your `.env` file.

### OpenAPI Specification

The OpenAPI/Swagger specification JSON is available at:
```
http://localhost:8000/apispec.json
```

This can be imported into tools like Postman, Insomnia, or used to generate client SDKs.

## Enabling API Documentation

### Development
API documentation is **enabled by default** in development mode.

### Production
To enable in production (not recommended for public-facing instances):

1. Set environment variable in `.env`:
   ```ini
   ENABLE_API_DOCS=true
   ```

2. Restart the application:
   ```bash
   # Docker
   docker compose restart app

   # Systemd
   sudo systemctl restart plsql-workbench
   ```

3. Access at: `https://your-domain.com/api/docs/`

## Authentication

Most API endpoints require JWT authentication using Bearer tokens.

### Getting an Access Token

**1. Login Request:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "YourPassword123!"
  }'
```

**2. Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": { ... }
}
```

### Using the Access Token

Include the access token in the `Authorization` header:

```bash
curl -X GET http://localhost:8000/api/dashboards \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Token Expiration

- **Access Token**: Expires in 1 hour
- **Refresh Token**: Expires in 30 days

### Refreshing Tokens

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer <refresh_token>"
```

## API Endpoints Overview

### Authentication & Users (`/api/auth`, `/api/users`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | User login | No |
| POST | `/api/auth/logout` | User logout | Yes |
| POST | `/api/auth/refresh` | Refresh access token | Yes |
| POST | `/api/auth/forgot-password` | Request password reset | No |
| POST | `/api/auth/reset-password` | Reset password with token | No |
| GET | `/api/auth/me` | Get current user info | Yes |
| GET | `/api/users` | List all users (admin) | Yes |
| GET | `/api/users/:id` | Get user details | Yes |
| PUT | `/api/users/:id` | Update user | Yes |
| DELETE | `/api/users/:id` | Delete user (admin) | Yes |

### PL/SQL Unwrapping (`/api/unwrap`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/unwrap` | Unwrap PL/SQL code | Yes |
| POST | `/api/unwrap/batch` | Batch unwrap multiple files | Yes |

### Oracle Connections (`/api/connections`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/connections` | List connections | Yes |
| POST | `/api/connections` | Create connection | Yes |
| GET | `/api/connections/:id` | Get connection details | Yes |
| PUT | `/api/connections/:id` | Update connection | Yes |
| DELETE | `/api/connections/:id` | Delete connection | Yes |
| POST | `/api/connections/:id/test` | Test connection | Yes |

### Query Execution (`/api/queries`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/queries/execute` | Execute SQL query | Yes |
| GET | `/api/queries/:id/results` | Get query results | Yes |
| POST | `/api/queries/:id/cancel` | Cancel running query | Yes |

### Saved Queries (`/api/saved-queries`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/saved-queries` | List saved queries | Yes |
| POST | `/api/saved-queries` | Save new query | Yes |
| GET | `/api/saved-queries/:id` | Get saved query | Yes |
| PUT | `/api/saved-queries/:id` | Update saved query | Yes |
| DELETE | `/api/saved-queries/:id` | Delete saved query | Yes |
| POST | `/api/saved-queries/:id/execute` | Execute saved query | Yes |

### Dashboards (`/api/dashboards`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/dashboards` | List dashboards | Yes |
| POST | `/api/dashboards` | Create dashboard | Yes |
| GET | `/api/dashboards/:id` | Get dashboard | Yes |
| PUT | `/api/dashboards/:id` | Update dashboard | Yes |
| DELETE | `/api/dashboards/:id` | Delete dashboard | Yes |
| POST | `/api/dashboards/:id/publish` | Publish dashboard | Yes |
| POST | `/api/dashboards/:id/duplicate` | Duplicate dashboard | Yes |
| GET | `/api/dashboards/:id/versions` | List versions | Yes |
| POST | `/api/dashboards/:id/restore/:version` | Restore version | Yes |
| GET | `/api/public/dashboards/:token` | Access public dashboard | No |

### Dashboard Components (`/api/dashboards/:id/components`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/dashboards/:id/components` | List components | Yes |
| POST | `/api/dashboards/:id/components` | Add component | Yes |
| PUT | `/api/dashboards/:id/components/:cid` | Update component | Yes |
| DELETE | `/api/dashboards/:id/components/:cid` | Delete component | Yes |

### Dashboard Data Sources (`/api/dashboards/:id/data-sources`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/dashboards/:id/data-sources` | List data sources | Yes |
| POST | `/api/dashboards/:id/data-sources` | Add data source | Yes |
| PUT | `/api/dashboards/:id/data-sources/:dsid` | Update data source | Yes |
| DELETE | `/api/dashboards/:id/data-sources/:dsid` | Delete data source | Yes |
| POST | `/api/dashboards/:id/data-sources/:dsid/refresh` | Refresh data | Yes |

### Dashboard Sharing (`/api/dashboards/:id/shares`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/dashboards/:id/shares` | List shares | Yes |
| POST | `/api/dashboards/:id/shares` | Share dashboard | Yes |
| DELETE | `/api/dashboards/:id/shares/:sid` | Remove share | Yes |
| POST | `/api/dashboards/:id/public-link` | Create public link | Yes |
| DELETE | `/api/dashboards/:id/public-link` | Remove public link | Yes |

### Dashboard Templates (`/api/templates`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/templates` | Browse templates | No |
| GET | `/api/templates/:id` | Get template details | No |
| POST | `/api/templates` | Create template | Yes |
| PUT | `/api/templates/:id` | Update template | Yes |
| DELETE | `/api/templates/:id` | Delete template | Yes |
| POST | `/api/templates/:id/use` | Create dashboard from template | Yes |
| POST | `/api/dashboards/:id/create-template` | Save dashboard as template | Yes |

### Roles & Permissions (`/api/roles`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/roles` | List roles (admin) | Yes |
| POST | `/api/roles` | Create role (admin) | Yes |
| PUT | `/api/roles/:id` | Update role (admin) | Yes |
| DELETE | `/api/roles/:id` | Delete role (admin) | Yes |

### Admin Operations (`/api/admin`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/admin/stats` | System statistics | Yes (admin) |
| GET | `/api/admin/audit-logs` | Audit log entries | Yes (admin) |
| POST | `/api/admin/maintenance` | Run maintenance tasks | Yes (admin) |

### Health & Monitoring (`/api/health`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/health` | Basic health check | No |
| GET | `/api/health/ready` | Readiness check | No |
| GET | `/api/health/live` | Liveness check | No |
| GET | `/api/metrics` | Application metrics | No |
| GET | `/api/metrics/prometheus` | Prometheus metrics | No |
| GET | `/api/info` | Application info | No |

## Rate Limiting

API endpoints are protected by rate limiting to prevent abuse:

### Default Limits

| Endpoint Type | Limit |
|--------------|-------|
| Authentication | 5 requests/minute |
| Public | 50 requests/minute |
| API (General) | 100 requests/minute |
| API (Strict) | 1000 requests/hour |

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642089600
```

### Rate Limit Exceeded

When exceeded, you'll receive a `429 Too Many Requests` response:

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later."
}
```

## Error Handling

All API responses follow a consistent format:

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable error message",
  "details": { ... }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource conflict (e.g., duplicate) |
| 413 | Payload Too Large - Request body too large |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Service temporarily unavailable |

## Pagination

List endpoints support pagination using query parameters:

```bash
GET /api/dashboards?page=1&per_page=20&sort_by=created_at&sort_order=desc
```

### Pagination Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `per_page` | integer | 20 | Items per page (max: 100) |
| `sort_by` | string | varies | Sort field |
| `sort_order` | string | desc | Sort order (asc/desc) |

### Pagination Response

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

## Filtering and Search

Many list endpoints support filtering:

```bash
# Filter dashboards by category
GET /api/dashboards?category=analytics

# Search dashboards
GET /api/dashboards?search=sales

# Filter by tags
GET /api/dashboards?tags=finance,reports

# Combine filters
GET /api/dashboards?category=analytics&is_published=true&search=revenue
```

## CORS

CORS is configured to allow requests from specified origins. Configure allowed origins in `.env`:

```ini
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
```

## Examples

### Complete Authentication Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'

# 2. Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}' \
  | jq -r '.access_token')

# 3. Access protected endpoint
curl -X GET http://localhost:8000/api/dashboards \
  -H "Authorization: Bearer $TOKEN"
```

### Create Dashboard with Components

```bash
# 1. Create dashboard
DASHBOARD_ID=$(curl -X POST http://localhost:8000/api/dashboards \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales Dashboard",
    "description": "Q1 Sales Analytics",
    "category": "sales",
    "layout_config": {"columns": 12}
  }' | jq -r '.dashboard.id')

# 2. Add component
curl -X POST http://localhost:8000/api/dashboards/$DASHBOARD_ID/components \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "component_type": "chart",
    "title": "Monthly Revenue",
    "config": {
      "chart_type": "line",
      "x_axis": "month",
      "y_axis": "revenue"
    },
    "grid_position": {"x": 0, "y": 0, "w": 6, "h": 4}
  }'

# 3. Publish dashboard
curl -X POST http://localhost:8000/api/dashboards/$DASHBOARD_ID/publish \
  -H "Authorization: Bearer $TOKEN"
```

### Execute Query

```bash
curl -X POST http://localhost:8000/api/queries/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": 1,
    "query": "SELECT * FROM employees WHERE department = :dept",
    "parameters": {"dept": "Sales"},
    "limit": 100
  }'
```

## SDKs and Client Libraries

### Generate Client SDK

You can generate client SDKs from the OpenAPI specification using tools like:

- **OpenAPI Generator**: https://openapi-generator.tech/
- **Swagger Codegen**: https://swagger.io/tools/swagger-codegen/

```bash
# Generate Python client
openapi-generator-cli generate \
  -i http://localhost:8000/apispec.json \
  -g python \
  -o ./sdk/python

# Generate JavaScript/TypeScript client
openapi-generator-cli generate \
  -i http://localhost:8000/apispec.json \
  -g typescript-axios \
  -o ./sdk/typescript
```

### Postman Collection

Import the OpenAPI spec into Postman:

1. Open Postman
2. Click **Import**
3. Enter URL: `http://localhost:8000/apispec.json`
4. Click **Import**

## WebSocket Support (Future)

Real-time features (live dashboard updates, query streaming) will be added in future releases using WebSocket connections.

## API Versioning

The current API is version 1.0. Future versions will be namespaced:

- **v1**: `/api/v1/...`
- **v2**: `/api/v2/...`

The current `/api/...` endpoints will remain stable and map to the latest stable version.

## Support and Resources

- **Swagger UI**: http://localhost:8000/api/docs/ (development)
- **OpenAPI Spec**: http://localhost:8000/apispec.json
- **Health Checks**: http://localhost:8000/api/health
- **GitHub Issues**: Report bugs and request features
- **Documentation**: See `DEPLOYMENT.md`, `DOCKER.md`, `README.md`

---

**Last Updated**: 2025-11-20
**Version**: 1.0 (Phase 5)
