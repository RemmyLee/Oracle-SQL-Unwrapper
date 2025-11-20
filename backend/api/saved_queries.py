"""
Saved Queries API endpoints
Manage user's saved/favorite queries
"""

from flask import Blueprint, request, jsonify
from backend.models.query_history import SavedQuery
from backend.extensions import db
from datetime import datetime
import logging


logger = logging.getLogger(__name__)

# Create blueprint
saved_queries_bp = Blueprint('saved_queries', __name__)


@saved_queries_bp.route('/saved-queries', methods=['GET'])
def list_saved_queries():
    """
    List all saved queries

    GET /api/saved-queries?folder=MyQueries&tag=reports

    Query Parameters:
        folder: Filter by folder name
        tag: Filter by tag
        search: Search in name, description, or SQL

    Response:
    {
        "success": true,
        "queries": [...],
        "total": 25
    }
    """
    try:
        # Base query (Phase 4 will filter by user_id)
        query = SavedQuery.query

        # Apply filters
        folder = request.args.get('folder')
        if folder:
            query = query.filter(SavedQuery.folder == folder)

        tag = request.args.get('tag')
        if tag:
            query = query.filter(SavedQuery.tags.contains([tag]))

        search = request.args.get('search')
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    SavedQuery.name.ilike(search_pattern),
                    SavedQuery.description.ilike(search_pattern),
                    SavedQuery.sql_text.ilike(search_pattern)
                )
            )

        # Order by
        order_by = request.args.get('order_by', 'name')
        if order_by == 'created':
            query = query.order_by(SavedQuery.created_at.desc())
        elif order_by == 'updated':
            query = query.order_by(SavedQuery.updated_at.desc())
        elif order_by == 'execution_count':
            query = query.order_by(SavedQuery.execution_count.desc())
        else:
            query = query.order_by(SavedQuery.name)

        queries = query.all()

        return jsonify({
            'success': True,
            'queries': [q.to_dict() for q in queries],
            'total': len(queries)
        }), 200

    except Exception as e:
        logger.error(f"Error listing saved queries: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list saved queries',
            'message': str(e)
        }), 500


@saved_queries_bp.route('/saved-queries', methods=['POST'])
def create_saved_query():
    """
    Create new saved query

    POST /api/saved-queries

    Request:
    {
        "name": "My Query",
        "description": "Description here",
        "sql_text": "SELECT * FROM employees",
        "folder": "Reports",
        "tags": ["report", "employees"],
        "color": "#FF5733"
    }

    Response:
    {
        "success": true,
        "query": {...}
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate required fields
        if not data.get('name') or not data.get('sql_text'):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, sql_text'
            }), 400

        # Create saved query
        saved_query = SavedQuery(
            user_id=1,  # Temporary: will use current_user.id in Phase 4
            name=data['name'],
            description=data.get('description'),
            sql_text=data['sql_text'],
            folder=data.get('folder'),
            tags=data.get('tags', []),
            color=data.get('color')
        )

        db.session.add(saved_query)
        db.session.commit()

        logger.info(f"Created saved query: {saved_query.name} (ID: {saved_query.id})")

        return jsonify({
            'success': True,
            'query': saved_query.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating saved query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create saved query',
            'message': str(e)
        }), 500


@saved_queries_bp.route('/saved-queries/<int:id>', methods=['GET'])
def get_saved_query(id):
    """
    Get saved query details

    GET /api/saved-queries/<id>

    Response:
    {
        "success": true,
        "query": {...}
    }
    """
    try:
        saved_query = SavedQuery.query.get(id)

        if not saved_query:
            return jsonify({
                'success': False,
                'error': 'Saved query not found'
            }), 404

        return jsonify({
            'success': True,
            'query': saved_query.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error getting saved query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get saved query',
            'message': str(e)
        }), 500


@saved_queries_bp.route('/saved-queries/<int:id>', methods=['PUT'])
def update_saved_query(id):
    """
    Update saved query

    PUT /api/saved-queries/<id>

    Request:
    {
        "name": "Updated Name",
        "description": "Updated description",
        ...
    }

    Response:
    {
        "success": true,
        "query": {...}
    }
    """
    try:
        saved_query = SavedQuery.query.get(id)

        if not saved_query:
            return jsonify({
                'success': False,
                'error': 'Saved query not found'
            }), 404

        data = request.get_json()

        # Update allowed fields
        if 'name' in data:
            saved_query.name = data['name']
        if 'description' in data:
            saved_query.description = data['description']
        if 'sql_text' in data:
            saved_query.sql_text = data['sql_text']
        if 'folder' in data:
            saved_query.folder = data['folder']
        if 'tags' in data:
            saved_query.tags = data['tags']
        if 'color' in data:
            saved_query.color = data['color']

        saved_query.updated_at = datetime.utcnow()

        db.session.commit()

        logger.info(f"Updated saved query: {saved_query.name} (ID: {saved_query.id})")

        return jsonify({
            'success': True,
            'query': saved_query.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating saved query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update saved query',
            'message': str(e)
        }), 500


@saved_queries_bp.route('/saved-queries/<int:id>', methods=['DELETE'])
def delete_saved_query(id):
    """
    Delete saved query

    DELETE /api/saved-queries/<id>

    Response:
    {
        "success": true,
        "message": "Saved query deleted"
    }
    """
    try:
        saved_query = SavedQuery.query.get(id)

        if not saved_query:
            return jsonify({
                'success': False,
                'error': 'Saved query not found'
            }), 404

        db.session.delete(saved_query)
        db.session.commit()

        logger.info(f"Deleted saved query: {saved_query.name} (ID: {id})")

        return jsonify({
            'success': True,
            'message': 'Saved query deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting saved query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete saved query',
            'message': str(e)
        }), 500


@saved_queries_bp.route('/saved-queries/<int:id>/execute', methods=['POST'])
def execute_saved_query(id):
    """
    Execute a saved query and update statistics

    POST /api/saved-queries/<int:id>/execute

    Request:
    {
        "connection_id": 1,
        "params": {}
    }

    Response:
    {
        "success": true,
        "result": {
            "columns": [...],
            "rows": [...],
            ...
        }
    }
    """
    try:
        saved_query = SavedQuery.query.get(id)

        if not saved_query:
            return jsonify({
                'success': False,
                'error': 'Saved query not found'
            }), 404

        data = request.get_json() or {}
        connection_id = data.get('connection_id')

        if not connection_id:
            return jsonify({
                'success': False,
                'error': 'Missing connection_id'
            }), 400

        # Execute the query
        from backend.services.oracle_connector import SimpleOracleConnector

        with SimpleOracleConnector(connection_id) as connector:
            result = connector.execute_query(
                saved_query.sql_text,
                data.get('params', {})
            )

            if result['success']:
                # Update statistics
                saved_query.execution_count += 1
                saved_query.last_executed = datetime.utcnow()
                db.session.commit()

            return jsonify({
                'success': result['success'],
                'result': result,
                'query_name': saved_query.name
            }), 200 if result['success'] else 400

    except Exception as e:
        logger.error(f"Error executing saved query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to execute saved query',
            'message': str(e)
        }), 500


@saved_queries_bp.route('/saved-queries/folders', methods=['GET'])
def get_folders():
    """
    Get list of all folder names

    GET /api/saved-queries/folders

    Response:
    {
        "success": true,
        "folders": ["Reports", "Analysis", "Maintenance"]
    }
    """
    try:
        # Get unique folder names
        folders = db.session.query(SavedQuery.folder).filter(
            SavedQuery.folder.isnot(None)
        ).distinct().all()

        folder_names = [f[0] for f in folders]
        folder_names.sort()

        return jsonify({
            'success': True,
            'folders': folder_names
        }), 200

    except Exception as e:
        logger.error(f"Error getting folders: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get folders',
            'message': str(e)
        }), 500


@saved_queries_bp.route('/saved-queries/tags', methods=['GET'])
def get_tags():
    """
    Get list of all tags

    GET /api/saved-queries/tags

    Response:
    {
        "success": true,
        "tags": ["report", "analysis", "maintenance"]
    }
    """
    try:
        # Get all saved queries
        queries = SavedQuery.query.all()

        # Collect all unique tags
        all_tags = set()
        for query in queries:
            if query.tags:
                all_tags.update(query.tags)

        tags_list = sorted(list(all_tags))

        return jsonify({
            'success': True,
            'tags': tags_list
        }), 200

    except Exception as e:
        logger.error(f"Error getting tags: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get tags',
            'message': str(e)
        }), 500
