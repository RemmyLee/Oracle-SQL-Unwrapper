# Phase 2 - Simplified for Small Teams (2-3 Users)

**Timeline:** 3-4 weeks (reduced from 6-8 weeks)
**Goal:** Add Oracle database connectivity with simple, direct connections

## Architecture Decision: No Connection Pooling

For 2-3 users, connection pooling adds unnecessary complexity:
- ❌ Thread-safe pooling overhead not needed
- ❌ Complex pool management
- ❌ Extra dependencies and configuration
- ✅ Simple direct connections are perfect
- ✅ One connection per user session
- ✅ Easier to debug and maintain

---

## 2.1 Simple Connection Manager

```python
# backend/services/oracle_connector.py

import cx_Oracle
from backend.models.connection import OracleConnection
from flask import session
import logging

logger = logging.getLogger(__name__)


class SimpleOracleConnector:
    """
    Simple connection manager for small teams (2-3 users)
    One connection per user session - no pooling needed
    """

    def __init__(self, connection_id: int):
        """
        Initialize connector

        Args:
            connection_id: ID of OracleConnection model
        """
        self.connection_id = connection_id
        self.connection = None
        self.config = None

    def connect(self):
        """
        Create Oracle connection if not already connected

        Returns:
            cx_Oracle.Connection object
        """
        if self.connection is None:
            try:
                # Load connection config from database
                self.config = OracleConnection.query.get(self.connection_id)

                if not self.config:
                    raise ValueError(f"Connection {self.connection_id} not found")

                # Create DSN
                dsn = cx_Oracle.makedsn(
                    self.config.host,
                    self.config.port,
                    service_name=self.config.service_name
                )

                # Connect to Oracle
                self.connection = cx_Oracle.connect(
                    user=self.config.username,
                    password=self.config.get_password(),
                    dsn=dsn,
                    encoding="UTF-8"
                )

                logger.info(f"Connected to Oracle: {self.config.name}")

            except cx_Oracle.Error as e:
                error_obj, = e.args
                logger.error(f"Connection failed: {error_obj.message}")
                raise

        return self.connection

    def disconnect(self):
        """Close connection and clean up"""
        if self.connection:
            try:
                self.connection.close()
                logger.info(f"Disconnected from: {self.config.name if self.config else 'Oracle'}")
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")
            finally:
                self.connection = None

    def test_connection(self) -> dict:
        """
        Test database connection

        Returns:
            {
                'success': bool,
                'message': str,
                'oracle_version': str
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Test query
            cursor.execute("SELECT 1 FROM DUAL")
            result = cursor.fetchone()

            # Get Oracle version
            cursor.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
            version = cursor.fetchone()[0]

            cursor.close()

            # Update connection model
            if self.config:
                from datetime import datetime
                self.config.last_tested = datetime.utcnow()
                self.config.last_test_success = True
                self.config.oracle_version = version
                from backend.extensions import db
                db.session.commit()

            return {
                'success': True,
                'message': 'Connection successful',
                'oracle_version': version
            }

        except cx_Oracle.Error as e:
            error_obj, = e.args

            # Update connection model with failure
            if self.config:
                from datetime import datetime
                self.config.last_tested = datetime.utcnow()
                self.config.last_test_success = False
                from backend.extensions import db
                db.session.commit()

            return {
                'success': False,
                'message': f"Connection failed: {error_obj.message}",
                'error_code': error_obj.code
            }

    def execute_query(self, sql: str, params: dict = None, max_rows: int = 10000) -> dict:
        """
        Execute SELECT query

        Args:
            sql: SQL query to execute
            params: Optional bind parameters
            max_rows: Maximum rows to return

        Returns:
            {
                'success': bool,
                'columns': list,
                'rows': list,
                'row_count': int,
                'execution_time_ms': float,
                'has_more': bool
            }
        """
        import time
        start_time = time.time()

        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.arraysize = 1000  # Fetch optimization

            # Execute query
            cursor.execute(sql, params or {})

            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Fetch results with limit
            rows = cursor.fetchmany(max_rows + 1)
            has_more = len(rows) > max_rows

            if has_more:
                rows = rows[:max_rows]

            cursor.close()

            execution_time = (time.time() - start_time) * 1000

            return {
                'success': True,
                'columns': columns,
                'rows': rows,
                'row_count': len(rows),
                'execution_time_ms': round(execution_time, 2),
                'has_more': has_more
            }

        except cx_Oracle.Error as e:
            error_obj, = e.args
            return {
                'success': False,
                'error': error_obj.message,
                'error_code': error_obj.code,
                'offset': error_obj.offset if hasattr(error_obj, 'offset') else None
            }

    def execute_statement(self, sql: str, params: dict = None) -> dict:
        """
        Execute DML/DDL statement (INSERT, UPDATE, DELETE, CREATE, etc.)

        Args:
            sql: SQL statement to execute
            params: Optional bind parameters

        Returns:
            {
                'success': bool,
                'rows_affected': int,
                'message': str
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute(sql, params or {})
            rows_affected = cursor.rowcount

            conn.commit()
            cursor.close()

            return {
                'success': True,
                'rows_affected': rows_affected,
                'message': f"Statement executed successfully. {rows_affected} rows affected."
            }

        except cx_Oracle.Error as e:
            # Rollback on error
            if self.connection:
                self.connection.rollback()

            error_obj, = e.args
            return {
                'success': False,
                'error': error_obj.message,
                'error_code': error_obj.code
            }

    def get_schema_objects(self, schema: str, object_type: str = None) -> list:
        """
        Get database objects in schema

        Args:
            schema: Schema name
            object_type: Optional filter by type (TABLE, VIEW, PACKAGE, etc.)

        Returns:
            List of objects
        """
        sql = """
            SELECT OBJECT_NAME, OBJECT_TYPE, STATUS, CREATED, LAST_DDL_TIME
            FROM ALL_OBJECTS
            WHERE OWNER = :schema
        """

        if object_type:
            sql += " AND OBJECT_TYPE = :object_type"

        sql += " ORDER BY OBJECT_TYPE, OBJECT_NAME"

        params = {'schema': schema.upper()}
        if object_type:
            params['object_type'] = object_type.upper()

        result = self.execute_query(sql, params)

        if result['success']:
            return result['rows']
        else:
            return []

    def get_source_code(self, schema: str, object_name: str, object_type: str) -> str:
        """
        Get source code for PL/SQL object

        Args:
            schema: Schema name
            object_name: Object name
            object_type: Object type (PACKAGE, PROCEDURE, FUNCTION, etc.)

        Returns:
            Source code as string
        """
        sql = """
            SELECT TEXT
            FROM ALL_SOURCE
            WHERE OWNER = :schema
              AND NAME = :object_name
              AND TYPE = :object_type
            ORDER BY LINE
        """

        result = self.execute_query(sql, {
            'schema': schema.upper(),
            'object_name': object_name.upper(),
            'object_type': object_type.upper()
        })

        if result['success']:
            return ''.join([row[0] for row in result['rows']])
        else:
            return ""

    def __enter__(self):
        """Context manager support"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.disconnect()
```

---

## 2.2 Usage Examples

### Test Connection
```python
connector = SimpleOracleConnector(connection_id=1)
result = connector.test_connection()

if result['success']:
    print(f"Connected! Oracle version: {result['oracle_version']}")
else:
    print(f"Failed: {result['message']}")
```

### Execute Query
```python
connector = SimpleOracleConnector(connection_id=1)

result = connector.execute_query(
    "SELECT employee_id, first_name, last_name FROM employees WHERE department_id = :dept",
    params={'dept': 10}
)

if result['success']:
    print(f"Found {result['row_count']} rows")
    for row in result['rows']:
        print(row)
```

### Use with Context Manager
```python
# Automatically connects and disconnects
with SimpleOracleConnector(connection_id=1) as connector:
    result = connector.execute_query("SELECT * FROM employees")
    print(result['rows'])
# Connection automatically closed here
```

### Get Source Code and Unwrap
```python
connector = SimpleOracleConnector(connection_id=1)

# Get wrapped source code
source = connector.get_source_code(
    schema='MY_SCHEMA',
    object_name='MY_PACKAGE',
    object_type='PACKAGE BODY'
)

# Check if it's wrapped
import re
if re.search(r'^[0-9a-f]+\s+[0-9a-f]+', source, re.MULTILINE):
    # Unwrap it
    from backend.services.unwrapper import UnwrapperService
    unwrapper = UnwrapperService()
    result = unwrapper.unwrap(source)

    if result['success']:
        print("Unwrapped source:")
        print(result['unwrapped'])
```

---

## 2.3 API Endpoints

```python
# backend/api/connections.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.services.oracle_connector import SimpleOracleConnector
from backend.models.connection import OracleConnection
from backend.extensions import db

connections_bp = Blueprint('connections', __name__)


@connections_bp.route('/connections', methods=['GET'])
@login_required
def list_connections():
    """Get all user's connections"""
    connections = OracleConnection.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    return jsonify({
        'success': True,
        'connections': [c.to_dict() for c in connections]
    })


@connections_bp.route('/connections', methods=['POST'])
@login_required
def create_connection():
    """Create new connection"""
    data = request.get_json()

    # Validate required fields
    required = ['name', 'host', 'port', 'username', 'password']
    if not all(field in data for field in required):
        return jsonify({
            'success': False,
            'error': 'Missing required fields'
        }), 400

    # Create connection
    connection = OracleConnection(
        user_id=current_user.id,
        name=data['name'],
        description=data.get('description'),
        host=data['host'],
        port=data['port'],
        service_name=data.get('service_name'),
        username=data['username']
    )

    connection.set_password(data['password'])

    db.session.add(connection)
    db.session.commit()

    return jsonify({
        'success': True,
        'connection': connection.to_dict()
    }), 201


@connections_bp.route('/connections/<int:id>/test', methods=['POST'])
@login_required
def test_connection(id):
    """Test connection"""
    connection = OracleConnection.query.get_or_404(id)

    # Check ownership
    if connection.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    # Test connection
    connector = SimpleOracleConnector(id)
    result = connector.test_connection()

    return jsonify(result)


@connections_bp.route('/connections/<int:id>', methods=['DELETE'])
@login_required
def delete_connection(id):
    """Delete connection"""
    connection = OracleConnection.query.get_or_404(id)

    if connection.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    connection.is_active = False  # Soft delete
    db.session.commit()

    return jsonify({'success': True})
```

```python
# backend/api/queries.py

from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.services.oracle_connector import SimpleOracleConnector

queries_bp = Blueprint('queries', __name__)


@queries_bp.route('/query/execute', methods=['POST'])
@login_required
def execute_query():
    """Execute SQL query"""
    data = request.get_json()

    connection_id = data.get('connection_id')
    sql = data.get('sql')

    if not connection_id or not sql:
        return jsonify({
            'success': False,
            'error': 'Missing connection_id or sql'
        }), 400

    # Execute query
    connector = SimpleOracleConnector(connection_id)
    result = connector.execute_query(sql, data.get('params'))

    return jsonify(result)


@queries_bp.route('/unwrap-from-db', methods=['POST'])
@login_required
def unwrap_from_database():
    """Unwrap PL/SQL object directly from database"""
    data = request.get_json()

    connection_id = data.get('connection_id')
    schema = data.get('schema')
    object_name = data.get('object_name')
    object_type = data.get('object_type')

    if not all([connection_id, schema, object_name, object_type]):
        return jsonify({
            'success': False,
            'error': 'Missing required fields'
        }), 400

    # Get source code
    connector = SimpleOracleConnector(connection_id)
    source = connector.get_source_code(schema, object_name, object_type)

    if not source:
        return jsonify({
            'success': False,
            'error': 'Object not found or no source available'
        }), 404

    # Check if wrapped
    import re
    if not re.search(r'^[0-9a-f]+\s+[0-9a-f]+', source, re.MULTILINE):
        return jsonify({
            'success': False,
            'error': 'Object is not wrapped',
            'source': source
        })

    # Unwrap it
    from backend.services.unwrapper import UnwrapperService
    unwrapper = UnwrapperService()
    result = unwrapper.unwrap(source)

    if result['success']:
        return jsonify({
            'success': True,
            'wrapped': source,
            'unwrapped': result['unwrapped'],
            'format_detected': result['format_detected'],
            'metadata': result['metadata']
        })
    else:
        return jsonify(result), 400
```

---

## 2.4 Updated Requirements

```python
# Add to requirements.txt

# Oracle Database Connectivity
cx-Oracle==8.3.0
# or use the newer pure-python driver:
# python-oracledb==1.4.0
```

---

## Phase 2 Summary

**What's Removed:**
- ❌ Connection pooling complexity
- ❌ Thread-safe locks
- ❌ Pool management code
- ❌ Redis dependency (not needed for pooling)

**What's Added:**
- ✅ Simple direct connections
- ✅ One connection per user session
- ✅ Easy test connection functionality
- ✅ Query execution
- ✅ Unwrap from database
- ✅ Clean context manager support

**Timeline:** 3-4 weeks instead of 6-8 weeks
**Complexity:** Significantly reduced
**Perfect for:** 2-3 users

---

Ready to implement this simplified Phase 2?
