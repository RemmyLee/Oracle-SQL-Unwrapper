"""
Connections API endpoints
Manage Oracle database connections
"""

from flask import Blueprint, request, jsonify, current_app
from backend.services.oracle_connector import SimpleOracleConnector, OracleConnectionError
from backend.models.connection import OracleConnection
from backend.extensions import db
from backend.utils.validators import ConnectionValidator
import logging


logger = logging.getLogger(__name__)

# Create blueprint
connections_bp = Blueprint('connections', __name__)


@connections_bp.route('/connections', methods=['GET'])
def list_connections():
    """
    Get all active connections

    GET /api/connections

    Response:
    {
        "success": true,
        "connections": [...]
    }

    Note: In Phase 4, this will filter by current_user.id
    For now, returns all connections
    """
    try:
        connections = OracleConnection.query.filter_by(is_active=True).all()

        return jsonify({
            'success': True,
            'connections': [c.to_dict() for c in connections]
        }), 200

    except Exception as e:
        logger.error(f"Error listing connections: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list connections',
            'message': str(e)
        }), 500


@connections_bp.route('/connections', methods=['POST'])
def create_connection():
    """
    Create new Oracle database connection

    POST /api/connections

    Request:
    {
        "name": "Production DB",
        "description": "Main production database",
        "host": "oracle.example.com",
        "port": 1521,
        "service_name": "ORCL",
        "username": "admin",
        "password": "secure_password",
        "connection_type": "service_name",
        "color": "#205AA7"
    }

    Response:
    {
        "success": true,
        "connection": {...}
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required = ['name', 'host', 'port', 'username', 'password']
        missing = [field for field in required if field not in data]

        if missing:
            return jsonify({
                'success': False,
                'error': 'Missing required fields',
                'missing_fields': missing
            }), 400

        # Validate connection parameters
        is_valid, error_msg = ConnectionValidator.validate_connection_params(
            host=data['host'],
            port=data['port'],
            username=data['username']
        )

        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'message': error_msg
            }), 400

        # Require either service_name or sid
        connection_type = data.get('connection_type', 'service_name')

        if connection_type == 'service_name' and not data.get('service_name'):
            return jsonify({
                'success': False,
                'error': 'service_name is required when connection_type is service_name'
            }), 400

        if connection_type == 'sid' and not data.get('sid'):
            return jsonify({
                'success': False,
                'error': 'sid is required when connection_type is sid'
            }), 400

        # Create connection
        # Note: user_id will be set to current_user.id in Phase 4
        connection = OracleConnection(
            user_id=1,  # Temporary: will use current_user.id in Phase 4
            name=data['name'],
            description=data.get('description'),
            host=data['host'],
            port=data['port'],
            service_name=data.get('service_name'),
            sid=data.get('sid'),
            username=data['username'],
            connection_type=connection_type,
            color=data.get('color', '#205AA7'),
            ssl_enabled=data.get('ssl_enabled', False)
        )

        # Set encrypted password
        connection.set_password(data['password'])

        # Save to database
        db.session.add(connection)
        db.session.commit()

        logger.info(f"Created connection: {connection.name} (ID: {connection.id})")

        return jsonify({
            'success': True,
            'connection': connection.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create connection',
            'message': str(e)
        }), 500


@connections_bp.route('/connections/<int:id>', methods=['GET'])
def get_connection(id):
    """
    Get connection details

    GET /api/connections/<id>

    Response:
    {
        "success": true,
        "connection": {...}
    }
    """
    try:
        connection = OracleConnection.query.get(id)

        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404

        return jsonify({
            'success': True,
            'connection': connection.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error getting connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get connection',
            'message': str(e)
        }), 500


@connections_bp.route('/connections/<int:id>', methods=['PUT'])
def update_connection(id):
    """
    Update connection

    PUT /api/connections/<id>

    Request:
    {
        "name": "Updated name",
        "description": "Updated description",
        ...
    }

    Response:
    {
        "success": true,
        "connection": {...}
    }
    """
    try:
        connection = OracleConnection.query.get(id)

        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404

        data = request.get_json()

        # Update allowed fields
        if 'name' in data:
            connection.name = data['name']
        if 'description' in data:
            connection.description = data['description']
        if 'host' in data:
            connection.host = data['host']
        if 'port' in data:
            connection.port = data['port']
        if 'service_name' in data:
            connection.service_name = data['service_name']
        if 'sid' in data:
            connection.sid = data['sid']
        if 'username' in data:
            connection.username = data['username']
        if 'password' in data:
            connection.set_password(data['password'])
        if 'connection_type' in data:
            connection.connection_type = data['connection_type']
        if 'color' in data:
            connection.color = data['color']
        if 'ssl_enabled' in data:
            connection.ssl_enabled = data['ssl_enabled']

        db.session.commit()

        logger.info(f"Updated connection: {connection.name} (ID: {connection.id})")

        return jsonify({
            'success': True,
            'connection': connection.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update connection',
            'message': str(e)
        }), 500


@connections_bp.route('/connections/<int:id>', methods=['DELETE'])
def delete_connection(id):
    """
    Delete connection (soft delete)

    DELETE /api/connections/<id>

    Response:
    {
        "success": true,
        "message": "Connection deleted"
    }
    """
    try:
        connection = OracleConnection.query.get(id)

        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404

        # Soft delete
        connection.is_active = False
        db.session.commit()

        logger.info(f"Deleted connection: {connection.name} (ID: {connection.id})")

        return jsonify({
            'success': True,
            'message': 'Connection deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete connection',
            'message': str(e)
        }), 500


@connections_bp.route('/connections/<int:id>/test', methods=['POST'])
def test_connection(id):
    """
    Test Oracle database connection

    POST /api/connections/<id>/test

    Response:
    {
        "success": true,
        "message": "Connection successful",
        "oracle_version": "Oracle Database 19c...",
        "oracle_edition": "Enterprise Edition"
    }
    """
    try:
        connection = OracleConnection.query.get(id)

        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404

        # Test the connection
        connector = SimpleOracleConnector(id)

        try:
            result = connector.test_connection()
            return jsonify(result), 200 if result['success'] else 400

        finally:
            connector.disconnect()

    except OracleConnectionError as e:
        logger.error(f"Connection test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Connection test failed',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to test connection',
            'message': str(e)
        }), 500


@connections_bp.route('/connections/<int:id>/schemas', methods=['GET'])
def get_schemas(id):
    """
    Get all schemas accessible from this connection

    GET /api/connections/<id>/schemas

    Response:
    {
        "success": true,
        "schemas": [
            ["SCOTT", "2024-01-01 00:00:00", "OPEN"],
            ...
        ]
    }
    """
    try:
        connection = OracleConnection.query.get(id)

        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404

        # Get schemas
        with SimpleOracleConnector(id) as connector:
            schemas = connector.get_schemas()

            return jsonify({
                'success': True,
                'schemas': schemas
            }), 200

    except OracleConnectionError as e:
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve schemas',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error getting schemas: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get schemas',
            'message': str(e)
        }), 500
