"""
Simple Oracle database connector for small teams (2-3 users)
No connection pooling - one connection per user session
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

try:
    import cx_Oracle
    CX_ORACLE_AVAILABLE = True
except ImportError:
    CX_ORACLE_AVAILABLE = False
    # Will provide helpful error message if used without cx_Oracle installed


logger = logging.getLogger(__name__)


class OracleConnectionError(Exception):
    """Oracle connection error"""
    pass


class SimpleOracleConnector:
    """
    Simple Oracle connection manager for small teams (2-3 users)

    Features:
    - Direct connections (no pooling)
    - One connection per user session
    - Context manager support
    - Query execution with safety checks
    - Source code retrieval
    - Automatic cleanup

    Usage:
        # Direct usage
        connector = SimpleOracleConnector(connection_id=1)
        result = connector.execute_query("SELECT * FROM employees")
        connector.disconnect()

        # Context manager (recommended)
        with SimpleOracleConnector(connection_id=1) as connector:
            result = connector.execute_query("SELECT * FROM employees")
    """

    def __init__(self, connection_id: int):
        """
        Initialize connector

        Args:
            connection_id: ID of OracleConnection model

        Raises:
            ImportError: If cx_Oracle is not installed
        """
        if not CX_ORACLE_AVAILABLE:
            raise ImportError(
                "cx_Oracle is not installed. Install it with: pip install cx_Oracle"
            )

        self.connection_id = connection_id
        self.connection = None
        self.config = None

    def connect(self):
        """
        Create Oracle connection if not already connected

        Returns:
            cx_Oracle.Connection object

        Raises:
            OracleConnectionError: If connection fails
        """
        if self.connection is not None:
            # Already connected
            return self.connection

        try:
            # Import here to avoid circular imports
            from backend.models.connection import OracleConnection

            # Load connection config from database
            self.config = OracleConnection.query.get(self.connection_id)

            if not self.config:
                raise OracleConnectionError(f"Connection {self.connection_id} not found")

            if not self.config.is_active:
                raise OracleConnectionError(f"Connection {self.connection_id} is inactive")

            # Create DSN (Data Source Name)
            if self.config.connection_type == 'service_name':
                dsn = cx_Oracle.makedsn(
                    self.config.host,
                    self.config.port,
                    service_name=self.config.service_name
                )
            elif self.config.connection_type == 'sid':
                dsn = cx_Oracle.makedsn(
                    self.config.host,
                    self.config.port,
                    sid=self.config.sid
                )
            else:
                raise OracleConnectionError(f"Invalid connection type: {self.config.connection_type}")

            # Connect to Oracle
            self.connection = cx_Oracle.connect(
                user=self.config.username,
                password=self.config.get_password(),
                dsn=dsn,
                encoding="UTF-8"
            )

            logger.info(f"Connected to Oracle: {self.config.name} ({self.config.host})")

            return self.connection

        except cx_Oracle.Error as e:
            error_obj, = e.args
            error_message = f"Oracle connection failed: {error_obj.message}"
            logger.error(error_message)
            raise OracleConnectionError(error_message)

        except Exception as e:
            error_message = f"Connection failed: {str(e)}"
            logger.error(error_message)
            raise OracleConnectionError(error_message)

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

    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self.connection is not None

    def test_connection(self) -> Dict:
        """
        Test database connection

        Returns:
            {
                'success': bool,
                'message': str,
                'oracle_version': str,
                'oracle_edition': str
            }
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Test query
            cursor.execute("SELECT 1 FROM DUAL")
            cursor.fetchone()

            # Get Oracle version and edition
            cursor.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
            version_row = cursor.fetchone()
            version = version_row[0] if version_row else "Unknown"

            # Try to get edition (may not have permission)
            try:
                cursor.execute("SELECT * FROM V$OPTION WHERE PARAMETER = 'Partitioning'")
                edition_row = cursor.fetchone()
                edition = "Enterprise Edition" if edition_row else "Standard Edition"
            except:
                edition = "Unknown"

            cursor.close()

            # Update connection model with success
            if self.config:
                from backend.extensions import db
                self.config.last_tested = datetime.utcnow()
                self.config.last_test_success = True
                self.config.oracle_version = version
                db.session.commit()

            return {
                'success': True,
                'message': 'Connection successful',
                'oracle_version': version,
                'oracle_edition': edition
            }

        except cx_Oracle.Error as e:
            error_obj, = e.args

            # Update connection model with failure
            if self.config:
                from backend.extensions import db
                self.config.last_tested = datetime.utcnow()
                self.config.last_test_success = False
                db.session.commit()

            return {
                'success': False,
                'message': f"Connection failed: {error_obj.message}",
                'error_code': error_obj.code
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"Connection test failed: {str(e)}"
            }

    def execute_query(self, sql: str, params: Optional[Dict] = None,
                     max_rows: int = 10000) -> Dict:
        """
        Execute SELECT query

        Args:
            sql: SQL query to execute
            params: Optional bind parameters (dict)
            max_rows: Maximum rows to return (default 10000)

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

            logger.info(f"Query executed: {len(rows)} rows in {execution_time:.2f}ms")

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
            logger.error(f"Query execution failed: {error_obj.message}")

            return {
                'success': False,
                'error': error_obj.message,
                'error_code': error_obj.code,
                'offset': error_obj.offset if hasattr(error_obj, 'offset') else None
            }

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def execute_statement(self, sql: str, params: Optional[Dict] = None) -> Dict:
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

            logger.info(f"Statement executed: {rows_affected} rows affected")

            return {
                'success': True,
                'rows_affected': rows_affected,
                'message': f"Statement executed successfully. {rows_affected} rows affected."
            }

        except cx_Oracle.Error as e:
            # Rollback on error
            if self.connection:
                try:
                    self.connection.rollback()
                except:
                    pass

            error_obj, = e.args
            logger.error(f"Statement execution failed: {error_obj.message}")

            return {
                'success': False,
                'error': error_obj.message,
                'error_code': error_obj.code
            }

        except Exception as e:
            logger.error(f"Statement execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_schemas(self) -> List:
        """
        Get all accessible schemas

        Returns:
            List of schema information
        """
        sql = """
            SELECT USERNAME, CREATED, ACCOUNT_STATUS
            FROM ALL_USERS
            ORDER BY USERNAME
        """

        result = self.execute_query(sql)

        if result['success']:
            return result['rows']
        else:
            return []

    def get_tables(self, schema: str) -> List:
        """
        Get tables in schema

        Args:
            schema: Schema name

        Returns:
            List of table information
        """
        sql = """
            SELECT TABLE_NAME, NUM_ROWS, TABLESPACE_NAME, LAST_ANALYZED
            FROM ALL_TABLES
            WHERE OWNER = :schema
            ORDER BY TABLE_NAME
        """

        result = self.execute_query(sql, {'schema': schema.upper()})

        if result['success']:
            return result['rows']
        else:
            return []

    def get_table_columns(self, schema: str, table: str) -> List:
        """
        Get column details for table

        Args:
            schema: Schema name
            table: Table name

        Returns:
            List of column information
        """
        sql = """
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                DATA_LENGTH,
                DATA_PRECISION,
                DATA_SCALE,
                NULLABLE,
                COLUMN_ID
            FROM ALL_TAB_COLUMNS
            WHERE OWNER = :schema AND TABLE_NAME = :table
            ORDER BY COLUMN_ID
        """

        result = self.execute_query(sql, {
            'schema': schema.upper(),
            'table': table.upper()
        })

        if result['success']:
            return result['rows']
        else:
            return []

    def get_schema_objects(self, schema: str, object_type: Optional[str] = None) -> List:
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

        params = {'schema': schema.upper()}

        if object_type:
            sql += " AND OBJECT_TYPE = :object_type"
            params['object_type'] = object_type.upper()

        sql += " ORDER BY OBJECT_TYPE, OBJECT_NAME"

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

    def is_wrapped(self, source_code: str) -> bool:
        """
        Check if source code is wrapped

        Args:
            source_code: PL/SQL source code

        Returns:
            True if wrapped, False otherwise
        """
        import re
        return bool(re.search(r'^[0-9a-f]+\s+[0-9a-f]+', source_code, re.MULTILINE))

    def __enter__(self):
        """Context manager support - connect on entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support - disconnect on exit"""
        self.disconnect()
        return False  # Don't suppress exceptions

    def __repr__(self):
        """String representation"""
        status = "connected" if self.is_connected() else "disconnected"
        return f"<SimpleOracleConnector connection_id={self.connection_id} status={status}>"
