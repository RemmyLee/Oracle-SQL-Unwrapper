"""
Health check and monitoring endpoints
Provides system status, metrics, and readiness checks
"""

from flask import Blueprint, jsonify, current_app
from backend.extensions import db
from backend.models import User, Dashboard, DashboardTemplate
import psutil
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprint
health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint

    GET /api/health

    Response:
    {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200


@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """
    Readiness check - verifies all dependencies are available

    GET /api/health/ready

    Response:
    {
        "ready": true,
        "checks": {
            "database": "ok",
            "cache": "ok"
        }
    }
    """
    checks = {}
    ready = True

    # Check database
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['database'] = 'ok'
    except Exception as e:
        logger.error(f"Database check failed: {str(e)}")
        checks['database'] = 'error'
        ready = False

    # Check cache (if configured)
    try:
        if hasattr(current_app, 'cache'):
            current_app.cache.get('health_check')
            checks['cache'] = 'ok'
        else:
            checks['cache'] = 'not_configured'
    except Exception as e:
        logger.error(f"Cache check failed: {str(e)}")
        checks['cache'] = 'error'
        ready = False

    status_code = 200 if ready else 503

    return jsonify({
        'ready': ready,
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }), status_code


@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Liveness check - verifies the application is running

    GET /api/health/live

    Response:
    {
        "alive": true
    }
    """
    return jsonify({
        'alive': True,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@health_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Application metrics

    GET /api/metrics

    Response:
    {
        "database": {
            "users": 100,
            "dashboards": 50,
            "templates": 10
        },
        "system": {
            "cpu_percent": 45.2,
            "memory_percent": 60.5,
            "disk_percent": 75.0
        },
        "uptime_seconds": 3600
    }
    """
    try:
        # Database metrics
        db_metrics = {}
        try:
            db_metrics['users'] = User.query.count()
            db_metrics['dashboards'] = Dashboard.query.count()
            db_metrics['dashboards_published'] = Dashboard.query.filter_by(is_published=True).count()
            db_metrics['templates'] = DashboardTemplate.query.count()
        except Exception as e:
            logger.error(f"Database metrics error: {str(e)}")
            db_metrics['error'] = 'Unable to fetch database metrics'

        # System metrics
        system_metrics = {}
        try:
            system_metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            system_metrics['memory_percent'] = memory.percent
            system_metrics['memory_available_mb'] = memory.available / (1024 * 1024)
            disk = psutil.disk_usage('/')
            system_metrics['disk_percent'] = disk.percent
            system_metrics['disk_free_gb'] = disk.free / (1024 * 1024 * 1024)
        except Exception as e:
            logger.error(f"System metrics error: {str(e)}")
            system_metrics['error'] = 'Unable to fetch system metrics'

        # Application metrics
        app_metrics = {
            'environment': current_app.config.get('ENV', 'production'),
            'debug': current_app.config.get('DEBUG', False)
        }

        return jsonify({
            'database': db_metrics,
            'system': system_metrics,
            'application': app_metrics,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Metrics endpoint error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate metrics',
            'message': str(e)
        }), 500


@health_bp.route('/metrics/prometheus', methods=['GET'])
def prometheus_metrics():
    """
    Prometheus-formatted metrics

    GET /api/metrics/prometheus

    Response: Plain text Prometheus format
    """
    try:
        metrics_lines = []

        # Database metrics
        try:
            users_count = User.query.count()
            dashboards_count = Dashboard.query.count()
            dashboards_published = Dashboard.query.filter_by(is_published=True).count()
            templates_count = DashboardTemplate.query.count()

            metrics_lines.append(f'# HELP plsql_workbench_users_total Total number of users')
            metrics_lines.append(f'# TYPE plsql_workbench_users_total gauge')
            metrics_lines.append(f'plsql_workbench_users_total {users_count}')

            metrics_lines.append(f'# HELP plsql_workbench_dashboards_total Total number of dashboards')
            metrics_lines.append(f'# TYPE plsql_workbench_dashboards_total gauge')
            metrics_lines.append(f'plsql_workbench_dashboards_total {dashboards_count}')

            metrics_lines.append(f'# HELP plsql_workbench_dashboards_published Published dashboards')
            metrics_lines.append(f'# TYPE plsql_workbench_dashboards_published gauge')
            metrics_lines.append(f'plsql_workbench_dashboards_published {dashboards_published}')

            metrics_lines.append(f'# HELP plsql_workbench_templates_total Total number of templates')
            metrics_lines.append(f'# TYPE plsql_workbench_templates_total gauge')
            metrics_lines.append(f'plsql_workbench_templates_total {templates_count}')
        except Exception as e:
            logger.error(f"Database metrics error: {str(e)}")

        # System metrics
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            metrics_lines.append(f'# HELP plsql_workbench_cpu_percent CPU usage percentage')
            metrics_lines.append(f'# TYPE plsql_workbench_cpu_percent gauge')
            metrics_lines.append(f'plsql_workbench_cpu_percent {cpu}')

            metrics_lines.append(f'# HELP plsql_workbench_memory_percent Memory usage percentage')
            metrics_lines.append(f'# TYPE plsql_workbench_memory_percent gauge')
            metrics_lines.append(f'plsql_workbench_memory_percent {memory.percent}')

            metrics_lines.append(f'# HELP plsql_workbench_disk_percent Disk usage percentage')
            metrics_lines.append(f'# TYPE plsql_workbench_disk_percent gauge')
            metrics_lines.append(f'plsql_workbench_disk_percent {disk.percent}')
        except Exception as e:
            logger.error(f"System metrics error: {str(e)}")

        response_text = '\n'.join(metrics_lines) + '\n'
        return response_text, 200, {'Content-Type': 'text/plain; version=0.0.4'}

    except Exception as e:
        logger.error(f"Prometheus metrics endpoint error: {str(e)}")
        return f'# ERROR: {str(e)}\n', 500, {'Content-Type': 'text/plain'}


@health_bp.route('/info', methods=['GET'])
def info():
    """
    Application information

    GET /api/info

    Response:
    {
        "name": "PL/SQL Workbench",
        "version": "1.0.0",
        "environment": "production",
        "features": [...]
    }
    """
    return jsonify({
        'name': 'PL/SQL Workbench',
        'version': '1.0.0',
        'description': 'Enterprise Dashboard & Query Management System for Oracle Databases',
        'environment': current_app.config.get('ENV', 'production'),
        'features': [
            'SQL Unwrapper',
            'Oracle Connection Management',
            'Query Execution & Caching',
            'Data Export (CSV, Excel, JSON)',
            'User Management & RBAC',
            'Dashboard Builder',
            'Component System',
            'Data Source Integration',
            'Version Control',
            'Template Library'
        ],
        'api_version': 'v1',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
