"""
APEX Integration API
Endpoints for importing/exporting dashboards from/to Oracle APEX
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models import Dashboard, User, DashboardComponent, DashboardDataSource
from backend.services.apex_compatibility import (
    APEXDashboardImporter,
    APEXDashboardExporter,
    convert_apex_sql_to_standard
)
from backend.extensions import db, limiter
import logging
import json

logger = logging.getLogger(__name__)

# Create blueprint
apex_bp = Blueprint('apex', __name__)


@apex_bp.route('/apex/import', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def import_apex_dashboard():
    """
    Import a dashboard from APEX page export

    POST /api/apex/import

    Request Body:
    {
        "apex_export": {
            "page_id": 1,
            "page_name": "Sales Dashboard",
            "regions": [...],
            "items": [...]
        },
        "options": {
            "auto_convert_queries": true,
            "create_data_sources": true,
            "import_as_draft": true
        }
    }

    Response:
    {
        "success": true,
        "dashboard": {...},
        "conversion_warnings": [...],
        "message": "APEX dashboard imported successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        data = request.get_json()
        apex_export = data.get('apex_export')
        options = data.get('options', {})

        if not apex_export:
            return jsonify({
                'success': False,
                'error': 'apex_export is required'
            }), 400

        # Import APEX dashboard
        importer = APEXDashboardImporter()
        dashboard_data = importer.import_apex_page(apex_export)

        # Create dashboard
        dashboard = Dashboard(
            owner_id=user_id,
            title=dashboard_data['title'],
            slug=Dashboard.generate_slug(dashboard_data['title']),
            description=dashboard_data['description'],
            category=dashboard_data['category'],
            tags=dashboard_data['tags'],
            layout_config=dashboard_data['layout_config'],
            is_published=not options.get('import_as_draft', True)
        )
        db.session.add(dashboard)
        db.session.flush()

        # Create data sources
        data_source_map = {}
        if options.get('create_data_sources', True):
            for idx, ds_data in enumerate(dashboard_data.get('data_sources', [])):
                data_source = DashboardDataSource(
                    dashboard_id=dashboard.id,
                    name=ds_data['name'],
                    source_type=ds_data['source_type'],
                    query=ds_data['query'],
                    config=ds_data.get('config', {}),
                    cache_ttl=ds_data.get('cache_ttl', 300)
                )
                db.session.add(data_source)
                db.session.flush()
                data_source_map[idx] = data_source.id

        # Create components
        for comp_data in dashboard_data.get('components', []):
            # Map data source ID if present
            if 'config' in comp_data and 'data_source_id' in comp_data['config']:
                old_ds_idx = comp_data['config']['data_source_id']
                if old_ds_idx in data_source_map:
                    comp_data['config']['data_source_id'] = data_source_map[old_ds_idx]

            component = DashboardComponent(
                dashboard_id=dashboard.id,
                component_type=comp_data['component_type'],
                title=comp_data['title'],
                description=comp_data.get('description'),
                grid_position=comp_data['grid_position'],
                config=comp_data['config'],
                order_index=comp_data['order_index']
            )
            db.session.add(component)

        db.session.commit()

        # Log conversion warnings
        warnings = dashboard_data.get('conversion_warnings', [])
        if warnings:
            logger.warning(f"APEX import warnings for dashboard {dashboard.id}: {warnings}")

        return jsonify({
            'success': True,
            'dashboard': dashboard.to_dict(include_components=True),
            'conversion_warnings': warnings,
            'message': 'APEX dashboard imported successfully'
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"APEX import error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Import failed',
            'message': str(e)
        }), 500


@apex_bp.route('/apex/export/<int:dashboard_id>', methods=['GET'])
@jwt_required()
@limiter.limit("20 per minute")
def export_dashboard_to_apex(dashboard_id):
    """
    Export a dashboard to APEX page format

    GET /api/apex/export/<dashboard_id>?app_id=100

    Query Parameters:
    - app_id: APEX application ID (default: 100)
    - page_id: APEX page ID (default: dashboard_id + 1000)

    Response:
    {
        "success": true,
        "apex_export": {
            "application_id": 100,
            "page_id": 1001,
            "page_name": "Sales Dashboard",
            "regions": [...],
            "items": []
        },
        "message": "Dashboard exported to APEX format"
    }
    """
    try:
        user_id = get_jwt_identity()
        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permissions
        if dashboard.owner_id != user_id and not dashboard.is_accessible_by(user_id):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Get query parameters
        app_id = request.args.get('app_id', 100, type=int)
        page_id = request.args.get('page_id', dashboard_id + 1000, type=int)

        # Export to APEX format
        exporter = APEXDashboardExporter()
        dashboard_dict = dashboard.to_dict(include_components=True, include_data_sources=True)
        dashboard_dict['id'] = page_id  # Override ID for APEX page_id
        apex_export = exporter.export_to_apex(dashboard_dict, app_id)

        return jsonify({
            'success': True,
            'apex_export': apex_export,
            'message': 'Dashboard exported to APEX format'
        }), 200

    except Exception as e:
        logger.error(f"APEX export error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Export failed',
            'message': str(e)
        }), 500


@apex_bp.route('/apex/convert-sql', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def convert_apex_sql():
    """
    Convert APEX-specific SQL to standard Oracle SQL

    POST /api/apex/convert-sql

    Request Body:
    {
        "sql": "SELECT * FROM APEX_APPLICATIONS WHERE application_id = :APP_ID"
    }

    Response:
    {
        "success": true,
        "original_sql": "...",
        "converted_sql": "...",
        "warnings": [...],
        "message": "SQL converted successfully"
    }
    """
    try:
        data = request.get_json()
        sql = data.get('sql')

        if not sql:
            return jsonify({
                'success': False,
                'error': 'sql is required'
            }), 400

        # Convert SQL
        converted_sql, warnings = convert_apex_sql_to_standard(sql)

        return jsonify({
            'success': True,
            'original_sql': sql,
            'converted_sql': converted_sql,
            'warnings': warnings,
            'message': 'SQL converted successfully'
        }), 200

    except Exception as e:
        logger.error(f"SQL conversion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Conversion failed',
            'message': str(e)
        }), 500


@apex_bp.route('/apex/validate', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def validate_apex_export():
    """
    Validate an APEX export before import

    POST /api/apex/validate

    Request Body:
    {
        "apex_export": {...}
    }

    Response:
    {
        "success": true,
        "valid": true,
        "issues": [],
        "warnings": [],
        "component_count": 5,
        "data_source_count": 3
    }
    """
    try:
        data = request.get_json()
        apex_export = data.get('apex_export')

        if not apex_export:
            return jsonify({
                'success': False,
                'error': 'apex_export is required'
            }), 400

        issues = []
        warnings = []

        # Validate structure
        if not apex_export.get('page_name'):
            issues.append("Missing page_name")

        # Check for APEX-specific references
        regions = apex_export.get('regions', [])
        for region in regions:
            if region.get('source_type') == 'SQL' and region.get('source'):
                sql = region['source']
                _, sql_warnings = convert_apex_sql_to_standard(sql)
                warnings.extend(sql_warnings)

        # Count components
        component_count = len(regions) + len(apex_export.get('items', []))

        # Count data sources (regions with SQL)
        data_source_count = sum(1 for r in regions if r.get('source_type') == 'SQL')

        return jsonify({
            'success': True,
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'component_count': component_count,
            'data_source_count': data_source_count,
            'message': 'Validation complete'
        }), 200

    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'message': str(e)
        }), 500


@apex_bp.route('/apex/table-mappings', methods=['GET'])
@limiter.limit("100 per minute")
def get_apex_table_mappings():
    """
    Get list of APEX table/view mappings

    GET /api/apex/table-mappings

    Response:
    {
        "success": true,
        "mappings": {
            "APEX_APPLICATIONS": "USER_OBJECTS",
            ...
        },
        "function_mappings": {
            "APEX_UTIL.GET_USERNAME": "USER",
            ...
        }
    }
    """
    try:
        from backend.services.apex_compatibility import APEXTableMapper

        return jsonify({
            'success': True,
            'mappings': APEXTableMapper.APEX_TO_STANDARD,
            'function_mappings': APEXTableMapper.APEX_FUNCTIONS,
            'message': 'Table mappings retrieved'
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving mappings: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve mappings',
            'message': str(e)
        }), 500


@apex_bp.route('/apex/preview', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def preview_apex_import():
    """
    Preview APEX import without creating dashboard

    POST /api/apex/preview

    Request Body:
    {
        "apex_export": {...}
    }

    Response:
    {
        "success": true,
        "preview": {
            "title": "...",
            "component_count": 5,
            "components": [...],
            "data_sources": [...],
            "warnings": [...]
        }
    }
    """
    try:
        data = request.get_json()
        apex_export = data.get('apex_export')

        if not apex_export:
            return jsonify({
                'success': False,
                'error': 'apex_export is required'
            }), 400

        # Import without saving
        importer = APEXDashboardImporter()
        dashboard_data = importer.import_apex_page(apex_export)

        preview = {
            'title': dashboard_data['title'],
            'description': dashboard_data['description'],
            'category': dashboard_data['category'],
            'tags': dashboard_data['tags'],
            'component_count': len(dashboard_data.get('components', [])),
            'data_source_count': len(dashboard_data.get('data_sources', [])),
            'components': [
                {
                    'type': c['component_type'],
                    'title': c['title'],
                    'position': c['grid_position']
                }
                for c in dashboard_data.get('components', [])
            ],
            'data_sources': [
                {
                    'name': ds['name'],
                    'type': ds['source_type'],
                    'has_warnings': len(ds.get('config', {}).get('conversion_warnings', [])) > 0
                }
                for ds in dashboard_data.get('data_sources', [])
            ],
            'warnings': dashboard_data.get('conversion_warnings', [])
        }

        return jsonify({
            'success': True,
            'preview': preview,
            'message': 'Preview generated'
        }), 200

    except Exception as e:
        logger.error(f"Preview error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Preview failed',
            'message': str(e)
        }), 500
