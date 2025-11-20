"""
Queries API endpoints
Execute SQL queries and manage query history
"""

from flask import Blueprint, request, jsonify, current_app
from backend.services.oracle_connector import SimpleOracleConnector, OracleConnectionError
from backend.services.unwrapper import UnwrapperService
from backend.models.connection import OracleConnection
from backend.models.query_history import QueryHistory
from backend.extensions import db
from backend.utils.validators import QueryValidator
from datetime import datetime
import logging
import re


logger = logging.getLogger(__name__)

# Create blueprint
queries_bp = Blueprint('queries', __name__)


@queries_bp.route('/query/execute', methods=['POST'])
def execute_query():
    """
    Execute SQL query

    POST /api/query/execute

    Request:
    {
        "connection_id": 1,
        "sql": "SELECT * FROM employees WHERE department_id = :dept",
        "params": {"dept": 10},
        "max_rows": 1000,
        "save_history": true
    }

    Response:
    {
        "success": true,
        "columns": ["ID", "NAME", ...],
        "rows": [[1, "John"], ...],
        "row_count": 10,
        "execution_time_ms": 45.23,
        "has_more": false
    }
    """
    try:
        data = request.get_json()

        # Validate request
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        connection_id = data.get('connection_id')
        sql = data.get('sql')

        if not connection_id or not sql:
            return jsonify({
                'success': False,
                'error': 'Missing connection_id or sql'
            }), 400

        # Validate SQL
        is_valid, error_msg = QueryValidator.validate_query(sql, allow_ddl=False)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Query validation failed',
                'message': error_msg
            }), 400

        # Get configuration
        max_rows = data.get('max_rows', current_app.config.get('QUERY_MAX_RESULT_ROWS', 10000))
        params = data.get('params', {})
        save_history = data.get('save_history', True)

        # Execute query
        with SimpleOracleConnector(connection_id) as connector:
            result = connector.execute_query(sql, params, max_rows)

            # Save to history if requested
            if save_history and result['success']:
                try:
                    history = QueryHistory(
                        user_id=1,  # Temporary: will use current_user.id in Phase 4
                        connection_id=connection_id,
                        sql_text=sql,
                        execution_time_ms=result['execution_time_ms'],
                        row_count=result['row_count'],
                        success=True
                    )
                    db.session.add(history)
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Failed to save query history: {str(e)}")
                    # Don't fail the request if history save fails

            return jsonify(result), 200 if result['success'] else 400

    except OracleConnectionError as e:
        return jsonify({
            'success': False,
            'error': 'Database connection failed',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Query execution failed',
            'message': str(e)
        }), 500


@queries_bp.route('/query/execute-statement', methods=['POST'])
def execute_statement():
    """
    Execute DML/DDL statement

    POST /api/query/execute-statement

    Request:
    {
        "connection_id": 1,
        "sql": "UPDATE employees SET salary = salary * 1.1 WHERE department_id = :dept",
        "params": {"dept": 10}
    }

    Response:
    {
        "success": true,
        "rows_affected": 5,
        "message": "Statement executed successfully. 5 rows affected."
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        connection_id = data.get('connection_id')
        sql = data.get('sql')

        if not connection_id or not sql:
            return jsonify({
                'success': False,
                'error': 'Missing connection_id or sql'
            }), 400

        # Validate SQL (allow DDL for this endpoint)
        is_valid, error_msg = QueryValidator.validate_query(sql, allow_ddl=True)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Statement validation failed',
                'message': error_msg
            }), 400

        params = data.get('params', {})

        # Execute statement
        with SimpleOracleConnector(connection_id) as connector:
            result = connector.execute_statement(sql, params)

            # Save to history
            try:
                history = QueryHistory(
                    user_id=1,  # Temporary
                    connection_id=connection_id,
                    sql_text=sql,
                    row_count=result.get('rows_affected', 0),
                    success=result['success'],
                    error_message=result.get('error') if not result['success'] else None
                )
                db.session.add(history)
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to save query history: {str(e)}")

            return jsonify(result), 200 if result['success'] else 400

    except OracleConnectionError as e:
        return jsonify({
            'success': False,
            'error': 'Database connection failed',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error executing statement: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Statement execution failed',
            'message': str(e)
        }), 500


@queries_bp.route('/schema/<int:connection_id>/<schema>/objects', methods=['GET'])
def get_schema_objects(connection_id, schema):
    """
    Get database objects in schema

    GET /api/schema/<connection_id>/<schema>/objects?type=TABLE

    Query Parameters:
        type: Optional object type filter (TABLE, VIEW, PACKAGE, etc.)

    Response:
    {
        "success": true,
        "objects": [
            ["EMPLOYEES", "TABLE", "VALID", "2024-01-01", "2024-01-15"],
            ...
        ]
    }
    """
    try:
        object_type = request.args.get('type')

        with SimpleOracleConnector(connection_id) as connector:
            objects = connector.get_schema_objects(schema, object_type)

            return jsonify({
                'success': True,
                'objects': objects,
                'schema': schema.upper(),
                'object_type': object_type.upper() if object_type else 'ALL'
            }), 200

    except OracleConnectionError as e:
        return jsonify({
            'success': False,
            'error': 'Database connection failed',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error getting schema objects: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get schema objects',
            'message': str(e)
        }), 500


@queries_bp.route('/schema/<int:connection_id>/<schema>/tables/<table>/columns', methods=['GET'])
def get_table_columns(connection_id, schema, table):
    """
    Get table column details

    GET /api/schema/<connection_id>/<schema>/tables/<table>/columns

    Response:
    {
        "success": true,
        "columns": [
            ["EMPLOYEE_ID", "NUMBER", 22, 0, 0, "N", 1],
            ...
        ]
    }
    """
    try:
        with SimpleOracleConnector(connection_id) as connector:
            columns = connector.get_table_columns(schema, table)

            return jsonify({
                'success': True,
                'columns': columns,
                'schema': schema.upper(),
                'table': table.upper()
            }), 200

    except OracleConnectionError as e:
        return jsonify({
            'success': False,
            'error': 'Database connection failed',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error getting table columns: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get table columns',
            'message': str(e)
        }), 500


@queries_bp.route('/source/<int:connection_id>/<schema>/<object_type>/<object_name>', methods=['GET'])
def get_source_code(connection_id, schema, object_type, object_name):
    """
    Get PL/SQL source code

    GET /api/source/<connection_id>/<schema>/<object_type>/<object_name>

    Response:
    {
        "success": true,
        "source": "CREATE OR REPLACE PACKAGE...",
        "is_wrapped": false
    }
    """
    try:
        with SimpleOracleConnector(connection_id) as connector:
            source = connector.get_source_code(schema, object_name, object_type)

            if not source:
                return jsonify({
                    'success': False,
                    'error': 'Source code not found',
                    'message': f'No source found for {schema}.{object_name} ({object_type})'
                }), 404

            is_wrapped = connector.is_wrapped(source)

            return jsonify({
                'success': True,
                'source': source,
                'is_wrapped': is_wrapped,
                'schema': schema.upper(),
                'object_name': object_name.upper(),
                'object_type': object_type.upper()
            }), 200

    except OracleConnectionError as e:
        return jsonify({
            'success': False,
            'error': 'Database connection failed',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error getting source code: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get source code',
            'message': str(e)
        }), 500


@queries_bp.route('/unwrap-from-db', methods=['POST'])
def unwrap_from_database():
    """
    Unwrap PL/SQL object directly from database

    POST /api/unwrap-from-db

    Request:
    {
        "connection_id": 1,
        "schema": "SCOTT",
        "object_name": "MY_PACKAGE",
        "object_type": "PACKAGE BODY"
    }

    Response:
    {
        "success": true,
        "wrapped": "original wrapped source",
        "unwrapped": "unwrapped source code",
        "format_detected": "11g",
        "metadata": {...}
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
        required = ['connection_id', 'schema', 'object_name', 'object_type']
        missing = [field for field in required if field not in data]

        if missing:
            return jsonify({
                'success': False,
                'error': 'Missing required fields',
                'missing_fields': missing
            }), 400

        connection_id = data['connection_id']
        schema = data['schema']
        object_name = data['object_name']
        object_type = data['object_type']

        # Get source code from database
        with SimpleOracleConnector(connection_id) as connector:
            source = connector.get_source_code(schema, object_name, object_type)

            if not source:
                return jsonify({
                    'success': False,
                    'error': 'Object not found',
                    'message': f'No source found for {schema}.{object_name} ({object_type})'
                }), 404

            # Check if wrapped
            if not connector.is_wrapped(source):
                return jsonify({
                    'success': False,
                    'error': 'Object is not wrapped',
                    'message': 'The source code is not wrapped',
                    'source': source
                }), 400

        # Unwrap the source code
        unwrapper = UnwrapperService()
        result = unwrapper.unwrap(source)

        if result['success']:
            return jsonify({
                'success': True,
                'wrapped': source,
                'unwrapped': result['unwrapped'],
                'format_detected': result['format_detected'],
                'metadata': result['metadata'],
                'warnings': result.get('warnings', []),
                'schema': schema.upper(),
                'object_name': object_name.upper(),
                'object_type': object_type.upper()
            }), 200
        else:
            return jsonify(result), 400

    except OracleConnectionError as e:
        return jsonify({
            'success': False,
            'error': 'Database connection failed',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error unwrapping from database: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unwrap operation failed',
            'message': str(e)
        }), 500


@queries_bp.route('/query/history', methods=['GET'])
def get_query_history():
    """
    Get query execution history

    GET /api/query/history?limit=50&offset=0

    Query Parameters:
        limit: Number of records to return (default 50)
        offset: Number of records to skip (default 0)

    Response:
    {
        "success": true,
        "history": [...],
        "total": 150
    }
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        # Limit the maximum
        limit = min(limit, 1000)

        # Query history
        # Note: In Phase 4, filter by current_user.id
        query = QueryHistory.query.order_by(QueryHistory.executed_at.desc())

        total = query.count()
        history = query.limit(limit).offset(offset).all()

        return jsonify({
            'success': True,
            'history': [h.to_dict() for h in history],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        logger.error(f"Error getting query history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get query history',
            'message': str(e)
        }), 500
