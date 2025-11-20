# Oracle Database Toolkit - Implementation Guide

## Vision

Transform the Oracle SQL Unwrapper into a comprehensive web-based Oracle Database toolkit that combines code unwrapping with database connectivity, query execution, schema exploration, and advanced PL/SQL development features.

## Table of Contents

1. [Project Rename & Rebranding](#project-rename--rebranding)
2. [Architecture Overview](#architecture-overview)
3. [Phase 1: Foundation & Core Features](#phase-1-foundation--core-features)
4. [Phase 2: Database Connectivity](#phase-2-database-connectivity)
5. [Phase 3: Advanced Features](#phase-3-advanced-features)
6. [Phase 4: Enterprise Features](#phase-4-enterprise-features)
7. [Technical Stack](#technical-stack)
8. [Security Architecture](#security-architecture)
9. [UI/UX Design](#uiux-design)
10. [Testing Strategy](#testing-strategy)
11. [Deployment Options](#deployment-options)

---

## Project Rename & Rebranding

### Suggested Names
- **OracleKit** - Simple, memorable
- **PL/SQL Workbench** - Professional, descriptive
- **Oracle DevTools** - Clear purpose
- **DBUnwrap Pro** - Maintains original identity, suggests expansion

### Recommended: **PL/SQL Workbench**

---

## Architecture Overview

### Current State (v1.0)
```
Flask App (Single File)
└── Unwrapper Feature
    ├── Base64 Decode
    ├── Character Substitution
    └── Zlib Decompression
```

### Target State (v2.0)
```
PL/SQL Workbench (Modular Architecture)
├── Core Services
│   ├── Unwrapper Service
│   ├── Database Connection Pool
│   ├── Query Executor
│   └── Schema Inspector
├── API Layer (REST + WebSocket)
├── Frontend (Modern SPA)
└── Background Workers (Celery)
```

### Technology Stack Evolution

**Backend:**
- Flask → **Flask + Flask-RESTful** (API)
- Add **SQLAlchemy** (ORM, not for Oracle connection)
- Add **cx_Oracle / python-oracledb** (Oracle connectivity)
- Add **Celery** (async tasks)
- Add **Redis** (caching, task queue)
- Add **Flask-Login** (authentication)
- Add **Flask-CORS** (cross-origin support)

**Frontend:**
- Plain HTML/JS → **Vue.js 3 or React** (SPA)
- Add **Monaco Editor** (SQL editing)
- Add **Chart.js** (visualizations)
- Add **Tailwind CSS** (modern styling)

**Database:**
- Add **PostgreSQL or SQLite** (app metadata, user prefs, connection configs)

---

## Phase 1: Foundation & Core Features

**Timeline:** 4-6 weeks
**Goal:** Refactor existing code, add essential features, establish architecture

### 1.1 Project Restructuring

```
plsql-workbench/
├── backend/
│   ├── __init__.py
│   ├── app.py                    # Flask app initialization
│   ├── config.py                 # Configuration management
│   ├── extensions.py             # Flask extensions (db, login, etc.)
│   ├── models/                   # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── connection.py
│   │   └── query_history.py
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── unwrapper.py         # Existing unwrap logic
│   │   ├── oracle_connector.py  # Oracle DB connections
│   │   ├── query_executor.py    # Query execution
│   │   └── schema_inspector.py  # Schema browsing
│   ├── api/                      # REST API endpoints
│   │   ├── __init__.py
│   │   ├── unwrap.py
│   │   ├── connections.py
│   │   ├── queries.py
│   │   └── schema.py
│   └── utils/                    # Helpers
│       ├── __init__.py
│       ├── validators.py
│       └── formatters.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── store/               # State management
│   │   └── services/            # API calls
│   └── package.json
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── requirements.txt
├── docker-compose.yml
└── README.md
```

### 1.2 Enhanced Unwrapper Features

#### Feature: Multiple Format Support
```python
# backend/services/unwrapper.py

class UnwrapperService:
    """Enhanced unwrapper with multiple format support"""

    def unwrap(self, content: str, format_type: str = 'auto') -> dict:
        """
        Unwrap Oracle wrapped code

        Args:
            content: Wrapped PL/SQL content
            format_type: 'auto', '10g', '11g', '12c', '19c'

        Returns:
            {
                'success': bool,
                'unwrapped': str,
                'format_detected': str,
                'metadata': dict,
                'warnings': list
            }
        """
        pass

    def detect_format(self, content: str) -> str:
        """Auto-detect Oracle version format"""
        pass

    def validate_wrapped_content(self, content: str) -> tuple[bool, list]:
        """Validate input is wrapped SQL"""
        pass
```

#### Feature: Batch Unwrapping
- Upload multiple files
- Unwrap entire directory structures
- Export as ZIP archive
- Progress tracking via WebSocket

#### Feature: Unwrap from Database
```python
def unwrap_from_database(connection_id: int, object_type: str,
                         object_name: str, schema: str = None) -> dict:
    """
    Connect to Oracle DB and unwrap objects directly

    Supported types:
    - PACKAGE
    - PACKAGE BODY
    - PROCEDURE
    - FUNCTION
    - TRIGGER
    - TYPE BODY
    """
    pass
```

### 1.3 Security Hardening

#### Input Validation
```python
# backend/utils/validators.py

class UnwrapValidator:
    MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_LINE_LENGTH = 32768

    @staticmethod
    def validate_wrapped_input(content: str) -> tuple[bool, str]:
        """Comprehensive input validation"""
        if len(content) > UnwrapValidator.MAX_INPUT_SIZE:
            return False, "Input exceeds maximum size"

        if not re.match(r'^[0-9a-f]+ [0-9a-f]+', content, re.MULTILINE):
            return False, "Invalid wrapped format"

        # Check for malicious patterns
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'onclick=',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, "Potentially malicious content detected"

        return True, "Valid"
```

#### Error Handling
```python
# backend/services/unwrapper.py

class UnwrapError(Exception):
    """Base exception for unwrapping errors"""
    pass

class InvalidFormatError(UnwrapError):
    """Invalid wrapped format"""
    pass

class DecompressionError(UnwrapError):
    """Decompression failed"""
    pass

def decode_base64_package_safe(base64str: str) -> dict:
    """Safe version with comprehensive error handling"""
    try:
        # Validate input
        is_valid, error_msg = UnwrapValidator.validate_wrapped_input(base64str)
        if not is_valid:
            raise InvalidFormatError(error_msg)

        # Decode with timeout
        with timeout(seconds=30):
            base64dec = base64.decodebytes(
                bytearray(base64str.encode("latin-1"))
            )[20:]

            decoded = ""
            for byte in range(0, len(base64dec)):
                decoded += chr(charmap[ord(chr(base64dec[byte]))])

            result = zlib.decompress(
                bytearray(decoded.encode("latin-1"))
            )

        return {
            'success': True,
            'unwrapped': result.decode('utf-8'),
            'size_bytes': len(result)
        }

    except zlib.error as e:
        raise DecompressionError(f"Decompression failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unwrap error: {str(e)}")
        raise UnwrapError(f"Unwrapping failed: {str(e)}")
```

### 1.4 API Design

#### REST Endpoints

```python
# backend/api/unwrap.py

from flask import Blueprint, request, jsonify
from flask_login import login_required

unwrap_bp = Blueprint('unwrap', __name__)

@unwrap_bp.route('/api/unwrap', methods=['POST'])
@login_required  # Optional: add auth
def unwrap_code():
    """
    POST /api/unwrap

    Request:
    {
        "content": "wrapped SQL content",
        "format": "auto",
        "options": {
            "preserve_formatting": true,
            "add_comments": false
        }
    }

    Response:
    {
        "success": true,
        "result": {
            "unwrapped": "unwrapped SQL",
            "format_detected": "11g",
            "statistics": {
                "original_size": 1024,
                "unwrapped_size": 2048,
                "compression_ratio": 0.5
            }
        },
        "warnings": []
    }
    """
    data = request.get_json()
    service = UnwrapperService()
    result = service.unwrap(data['content'], data.get('format', 'auto'))
    return jsonify(result)

@unwrap_bp.route('/api/unwrap/batch', methods=['POST'])
def unwrap_batch():
    """Batch unwrapping endpoint"""
    pass

@unwrap_bp.route('/api/unwrap/from-db', methods=['POST'])
def unwrap_from_db():
    """Unwrap directly from connected database"""
    pass
```

---

## Phase 2: Database Connectivity

**Timeline:** 6-8 weeks
**Goal:** Full Oracle database connectivity with secure connection management

### 2.1 Connection Management

#### Connection Model
```python
# backend/models/connection.py

from extensions import db
from datetime import datetime
from cryptography.fernet import Fernet

class OracleConnection(db.Model):
    __tablename__ = 'oracle_connections'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # Connection details (encrypted)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, default=1521)
    service_name = db.Column(db.String(100))
    sid = db.Column(db.String(100))
    username = db.Column(db.String(100), nullable=False)
    password_encrypted = db.Column(db.LargeBinary, nullable=False)

    # Connection options
    connection_type = db.Column(db.String(20))  # 'basic', 'tns', 'easy_connect'
    ssl_enabled = db.Column(db.Boolean, default=False)
    wallet_path = db.Column(db.String(255))

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_tested = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    user = db.relationship('User', backref='connections')

    def set_password(self, password: str):
        """Encrypt and store password"""
        cipher = Fernet(current_app.config['ENCRYPTION_KEY'])
        self.password_encrypted = cipher.encrypt(password.encode())

    def get_password(self) -> str:
        """Decrypt password"""
        cipher = Fernet(current_app.config['ENCRYPTION_KEY'])
        return cipher.decrypt(self.password_encrypted).decode()

    def get_connection_string(self) -> str:
        """Generate cx_Oracle connection string"""
        if self.connection_type == 'service_name':
            return f"{self.username}/{self.get_password()}@{self.host}:{self.port}/{self.service_name}"
        elif self.connection_type == 'sid':
            return f"{self.username}/{self.get_password()}@{self.host}:{self.port}/{self.sid}"
```

#### Connection Pool Service
```python
# backend/services/oracle_connector.py

import cx_Oracle
from contextlib import contextmanager
from threading import Lock

class OracleConnectionPool:
    """Thread-safe Oracle connection pool manager"""

    def __init__(self):
        self.pools = {}
        self.lock = Lock()

    def get_pool(self, connection_id: int):
        """Get or create connection pool for a connection"""
        with self.lock:
            if connection_id not in self.pools:
                conn_config = OracleConnection.query.get(connection_id)

                dsn = cx_Oracle.makedsn(
                    conn_config.host,
                    conn_config.port,
                    service_name=conn_config.service_name
                )

                self.pools[connection_id] = cx_Oracle.SessionPool(
                    user=conn_config.username,
                    password=conn_config.get_password(),
                    dsn=dsn,
                    min=2,
                    max=10,
                    increment=1,
                    threaded=True,
                    encoding="UTF-8"
                )

            return self.pools[connection_id]

    @contextmanager
    def get_connection(self, connection_id: int):
        """Context manager for connection acquisition"""
        pool = self.get_pool(connection_id)
        conn = pool.acquire()
        try:
            yield conn
        finally:
            pool.release(conn)

    def test_connection(self, connection_id: int) -> dict:
        """Test database connection"""
        try:
            with self.get_connection(connection_id) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                result = cursor.fetchone()

                # Get Oracle version
                cursor.execute("SELECT * FROM v$version WHERE ROWNUM = 1")
                version = cursor.fetchone()[0]

                return {
                    'success': True,
                    'message': 'Connection successful',
                    'oracle_version': version
                }
        except cx_Oracle.Error as e:
            error_obj, = e.args
            return {
                'success': False,
                'message': f"Connection failed: {error_obj.message}",
                'error_code': error_obj.code
            }
```

### 2.2 Query Executor

```python
# backend/services/query_executor.py

class QueryExecutor:
    """Execute SQL queries with safety checks"""

    MAX_RESULT_ROWS = 10000
    QUERY_TIMEOUT = 300  # 5 minutes

    def __init__(self, connection_id: int):
        self.connection_id = connection_id
        self.pool = OracleConnectionPool()

    def execute_query(self, sql: str, params: dict = None) -> dict:
        """
        Execute SELECT query

        Returns:
        {
            'success': bool,
            'columns': ['COL1', 'COL2'],
            'rows': [[val1, val2], ...],
            'row_count': int,
            'execution_time_ms': float,
            'has_more': bool  # If result was truncated
        }
        """
        import time
        start_time = time.time()

        try:
            with self.pool.get_connection(self.connection_id) as conn:
                cursor = conn.cursor()
                cursor.arraysize = 1000  # Fetch optimization

                # Execute with timeout
                cursor.execute(sql, params or {})

                # Get column names
                columns = [desc[0] for desc in cursor.description]

                # Fetch results with limit
                rows = cursor.fetchmany(self.MAX_RESULT_ROWS + 1)
                has_more = len(rows) > self.MAX_RESULT_ROWS

                if has_more:
                    rows = rows[:self.MAX_RESULT_ROWS]

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
                'offset': error_obj.offset
            }

    def execute_statement(self, sql: str) -> dict:
        """Execute DML/DDL statement (INSERT, UPDATE, DELETE, CREATE, etc.)"""
        try:
            with self.pool.get_connection(self.connection_id) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)

                rows_affected = cursor.rowcount
                conn.commit()

                return {
                    'success': True,
                    'rows_affected': rows_affected,
                    'message': f"Statement executed successfully. {rows_affected} rows affected."
                }

        except cx_Oracle.Error as e:
            error_obj, = e.args
            return {
                'success': False,
                'error': error_obj.message,
                'error_code': error_obj.code
            }

    def execute_script(self, sql_script: str) -> list:
        """Execute multiple SQL statements"""
        statements = self.parse_sql_script(sql_script)
        results = []

        for stmt in statements:
            if stmt.strip().upper().startswith('SELECT'):
                result = self.execute_query(stmt)
            else:
                result = self.execute_statement(stmt)
            results.append(result)

        return results

    def explain_plan(self, sql: str) -> dict:
        """Get execution plan for query"""
        plan_table = f"PLAN_TABLE_{hash(sql) % 10000}"

        try:
            with self.pool.get_connection(self.connection_id) as conn:
                cursor = conn.cursor()

                # Explain plan
                cursor.execute(f"EXPLAIN PLAN SET STATEMENT_ID = 'stmt1' FOR {sql}")

                # Get plan
                cursor.execute("""
                    SELECT PLAN_TABLE_OUTPUT
                    FROM TABLE(DBMS_XPLAN.DISPLAY('PLAN_TABLE', 'stmt1', 'ALL'))
                """)

                plan = [row[0] for row in cursor.fetchall()]

                return {
                    'success': True,
                    'plan': '\n'.join(plan)
                }

        except cx_Oracle.Error as e:
            error_obj, = e.args
            return {
                'success': False,
                'error': error_obj.message
            }
```

### 2.3 Schema Inspector

```python
# backend/services/schema_inspector.py

class SchemaInspector:
    """Inspect Oracle database schema"""

    def __init__(self, connection_id: int):
        self.connection_id = connection_id
        self.pool = OracleConnectionPool()

    def get_schemas(self) -> list:
        """Get all accessible schemas"""
        sql = """
            SELECT USERNAME, CREATED, ACCOUNT_STATUS
            FROM ALL_USERS
            ORDER BY USERNAME
        """
        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            return cursor.fetchall()

    def get_tables(self, schema: str = None) -> list:
        """Get tables in schema"""
        sql = """
            SELECT TABLE_NAME, NUM_ROWS, TABLESPACE_NAME, LAST_ANALYZED
            FROM ALL_TABLES
            WHERE OWNER = :schema
            ORDER BY TABLE_NAME
        """
        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, {'schema': schema.upper()})
            return cursor.fetchall()

    def get_table_columns(self, schema: str, table: str) -> list:
        """Get column details for table"""
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
        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, {'schema': schema.upper(), 'table': table.upper()})
            return cursor.fetchall()

    def get_indexes(self, schema: str, table: str) -> list:
        """Get indexes for table"""
        sql = """
            SELECT
                i.INDEX_NAME,
                i.INDEX_TYPE,
                i.UNIQUENESS,
                LISTAGG(ic.COLUMN_NAME, ', ') WITHIN GROUP (ORDER BY ic.COLUMN_POSITION) as COLUMNS
            FROM ALL_INDEXES i
            JOIN ALL_IND_COLUMNS ic ON i.INDEX_NAME = ic.INDEX_NAME AND i.OWNER = ic.INDEX_OWNER
            WHERE i.OWNER = :schema AND i.TABLE_NAME = :table
            GROUP BY i.INDEX_NAME, i.INDEX_TYPE, i.UNIQUENESS
            ORDER BY i.INDEX_NAME
        """
        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, {'schema': schema.upper(), 'table': table.upper()})
            return cursor.fetchall()

    def get_plsql_objects(self, schema: str, object_type: str = None) -> list:
        """
        Get PL/SQL objects (procedures, functions, packages, triggers)

        object_type: 'PROCEDURE', 'FUNCTION', 'PACKAGE', 'PACKAGE BODY', 'TRIGGER', 'TYPE'
        """
        sql = """
            SELECT
                OBJECT_NAME,
                OBJECT_TYPE,
                STATUS,
                CREATED,
                LAST_DDL_TIME
            FROM ALL_OBJECTS
            WHERE OWNER = :schema
            AND OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION', 'PACKAGE', 'PACKAGE BODY', 'TRIGGER', 'TYPE', 'TYPE BODY')
        """

        if object_type:
            sql += " AND OBJECT_TYPE = :object_type"

        sql += " ORDER BY OBJECT_TYPE, OBJECT_NAME"

        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()
            params = {'schema': schema.upper()}
            if object_type:
                params['object_type'] = object_type.upper()
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_source_code(self, schema: str, object_name: str, object_type: str) -> str:
        """Get source code for PL/SQL object"""
        sql = """
            SELECT TEXT
            FROM ALL_SOURCE
            WHERE OWNER = :schema
            AND NAME = :object_name
            AND TYPE = :object_type
            ORDER BY LINE
        """
        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, {
                'schema': schema.upper(),
                'object_name': object_name.upper(),
                'object_type': object_type.upper()
            })
            lines = cursor.fetchall()
            return ''.join([line[0] for line in lines])

    def is_wrapped(self, schema: str, object_name: str, object_type: str) -> bool:
        """Check if PL/SQL object is wrapped"""
        source = self.get_source_code(schema, object_name, object_type)
        return bool(re.search(r'^[0-9a-f]+ [0-9a-f]+', source, re.MULTILINE))

    def get_dependencies(self, schema: str, object_name: str) -> dict:
        """Get object dependencies"""
        # Dependencies this object uses
        sql_uses = """
            SELECT
                REFERENCED_OWNER,
                REFERENCED_NAME,
                REFERENCED_TYPE,
                DEPENDENCY_TYPE
            FROM ALL_DEPENDENCIES
            WHERE OWNER = :schema AND NAME = :object_name
            ORDER BY REFERENCED_NAME
        """

        # Dependencies that use this object
        sql_used_by = """
            SELECT
                OWNER,
                NAME,
                TYPE,
                DEPENDENCY_TYPE
            FROM ALL_DEPENDENCIES
            WHERE REFERENCED_OWNER = :schema AND REFERENCED_NAME = :object_name
            ORDER BY NAME
        """

        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()

            cursor.execute(sql_uses, {'schema': schema.upper(), 'object_name': object_name.upper()})
            uses = cursor.fetchall()

            cursor.execute(sql_used_by, {'schema': schema.upper(), 'object_name': object_name.upper()})
            used_by = cursor.fetchall()

            return {
                'uses': uses,
                'used_by': used_by
            }
```

### 2.4 API Endpoints for Database Features

```python
# backend/api/connections.py

@connections_bp.route('/api/connections', methods=['GET'])
@login_required
def list_connections():
    """List all user's connections"""
    connections = OracleConnection.query.filter_by(
        user_id=current_user.id
    ).all()
    return jsonify([c.to_dict() for c in connections])

@connections_bp.route('/api/connections', methods=['POST'])
@login_required
def create_connection():
    """Create new connection"""
    data = request.get_json()
    # Validation and creation logic
    pass

@connections_bp.route('/api/connections/<int:id>/test', methods=['POST'])
@login_required
def test_connection(id):
    """Test connection"""
    pool = OracleConnectionPool()
    result = pool.test_connection(id)
    return jsonify(result)

# backend/api/queries.py

@queries_bp.route('/api/query/execute', methods=['POST'])
@login_required
def execute_query():
    """
    POST /api/query/execute
    {
        "connection_id": 1,
        "sql": "SELECT * FROM employees WHERE dept_id = :dept",
        "params": {"dept": 10},
        "limit": 1000
    }
    """
    data = request.get_json()
    executor = QueryExecutor(data['connection_id'])
    result = executor.execute_query(data['sql'], data.get('params'))
    return jsonify(result)

# backend/api/schema.py

@schema_bp.route('/api/schema/<int:connection_id>/schemas', methods=['GET'])
@login_required
def get_schemas(connection_id):
    """Get all schemas"""
    inspector = SchemaInspector(connection_id)
    schemas = inspector.get_schemas()
    return jsonify(schemas)

@schema_bp.route('/api/schema/<int:connection_id>/<schema>/objects', methods=['GET'])
@login_required
def get_schema_objects(connection_id, schema):
    """Get all objects in schema"""
    object_type = request.args.get('type')
    inspector = SchemaInspector(connection_id)

    result = {
        'tables': inspector.get_tables(schema),
        'plsql_objects': inspector.get_plsql_objects(schema, object_type)
    }
    return jsonify(result)
```

---

## Phase 3: Advanced Features

**Timeline:** 8-10 weeks
**Goal:** Add professional development tools and productivity features

### 3.1 SQL Editor with IntelliSense

```javascript
// frontend/src/components/SqlEditor.vue

<template>
  <div class="sql-editor">
    <div ref="editorContainer" class="editor-container"></div>
  </div>
</template>

<script setup>
import * as monaco from 'monaco-editor'
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  connectionId: Number,
  schema: String
})

const editorContainer = ref(null)
let editor = null

onMounted(() => {
  // Initialize Monaco editor
  editor = monaco.editor.create(editorContainer.value, {
    value: '-- Enter your SQL query here\nSELECT * FROM ',
    language: 'sql',
    theme: 'vs-dark',
    automaticLayout: true,
    minimap: { enabled: true },
    fontSize: 14,
    formatOnPaste: true,
    formatOnType: true
  })

  // Register completion provider for IntelliSense
  monaco.languages.registerCompletionItemProvider('sql', {
    provideCompletionItems: async (model, position) => {
      const word = model.getWordUntilPosition(position)
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn
      }

      // Fetch schema objects from API
      const suggestions = await fetchAutocompleteSuggestions(
        props.connectionId,
        props.schema,
        word.word
      )

      return {
        suggestions: suggestions.map(s => ({
          label: s.name,
          kind: monaco.languages.CompletionItemKind[s.kind],
          insertText: s.insertText,
          detail: s.detail,
          documentation: s.documentation,
          range: range
        }))
      }
    }
  })
})

async function fetchAutocompleteSuggestions(connId, schema, prefix) {
  const response = await fetch(
    `/api/autocomplete/${connId}/${schema}?prefix=${prefix}`
  )
  return response.json()
}
</script>
```

### 3.2 Query History & Favorites

```python
# backend/models/query_history.py

class QueryHistory(db.Model):
    __tablename__ = 'query_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    connection_id = db.Column(db.Integer, db.ForeignKey('oracle_connections.id'))

    sql_text = db.Column(db.Text, nullable=False)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    execution_time_ms = db.Column(db.Float)
    row_count = db.Column(db.Integer)

    success = db.Column(db.Boolean)
    error_message = db.Column(db.Text)

    is_favorite = db.Column(db.Boolean, default=False)
    favorite_name = db.Column(db.String(100))
    tags = db.Column(db.JSON)

    # Relationships
    user = db.relationship('User', backref='query_history')
    connection = db.relationship('OracleConnection')

class SavedQuery(db.Model):
    """User's saved/favorite queries"""
    __tablename__ = 'saved_queries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sql_text = db.Column(db.Text, nullable=False)

    folder = db.Column(db.String(100))  # Organize in folders
    tags = db.Column(db.JSON)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='saved_queries')
```

### 3.3 Data Export/Import

```python
# backend/services/data_exporter.py

class DataExporter:
    """Export query results to various formats"""

    SUPPORTED_FORMATS = ['csv', 'json', 'xlsx', 'sql', 'html', 'markdown']

    def export(self, data: dict, format: str, options: dict = None) -> bytes:
        """
        Export data to specified format

        Args:
            data: Query result dict with 'columns' and 'rows'
            format: Output format
            options: Format-specific options
        """
        if format == 'csv':
            return self._export_csv(data, options)
        elif format == 'json':
            return self._export_json(data, options)
        elif format == 'xlsx':
            return self._export_xlsx(data, options)
        elif format == 'sql':
            return self._export_sql(data, options)
        elif format == 'html':
            return self._export_html(data, options)
        elif format == 'markdown':
            return self._export_markdown(data, options)

    def _export_csv(self, data: dict, options: dict) -> bytes:
        """Export as CSV"""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(data['columns'])

        # Write rows
        writer.writerows(data['rows'])

        return output.getvalue().encode('utf-8')

    def _export_xlsx(self, data: dict, options: dict) -> bytes:
        """Export as Excel"""
        from openpyxl import Workbook
        from io import BytesIO

        wb = Workbook()
        ws = wb.active
        ws.title = options.get('sheet_name', 'Query Results')

        # Write header with formatting
        ws.append(data['columns'])
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", fill_type="solid")

        # Write data
        for row in data['rows']:
            ws.append(row)

        # Auto-size columns
        for column in ws.columns:
            max_length = max(len(str(cell.value)) for cell in column)
            ws.column_dimensions[column[0].column_letter].width = max_length + 2

        output = BytesIO()
        wb.save(output)
        return output.getvalue()

    def _export_sql(self, data: dict, options: dict) -> bytes:
        """Export as SQL INSERT statements"""
        table_name = options.get('table_name', 'exported_table')
        statements = []

        for row in data['rows']:
            values = ', '.join([
                f"'{str(v).replace(\"'\", \"''\")}" if v is not None else 'NULL'
                for v in row
            ])
            statements.append(
                f"INSERT INTO {table_name} ({', '.join(data['columns'])}) "
                f"VALUES ({values});"
            )

        return '\n'.join(statements).encode('utf-8')

    def _export_markdown(self, data: dict, options: dict) -> bytes:
        """Export as Markdown table"""
        lines = []

        # Header
        lines.append('| ' + ' | '.join(data['columns']) + ' |')
        lines.append('|' + '|'.join(['---' for _ in data['columns']]) + '|')

        # Rows
        for row in data['rows']:
            lines.append('| ' + ' | '.join([str(v) for v in row]) + ' |')

        return '\n'.join(lines).encode('utf-8')

# API endpoint
@export_bp.route('/api/export', methods=['POST'])
@login_required
def export_data():
    """
    POST /api/export
    {
        "data": {
            "columns": ["ID", "NAME"],
            "rows": [[1, "John"], [2, "Jane"]]
        },
        "format": "xlsx",
        "options": {
            "sheet_name": "Employees"
        }
    }
    """
    data = request.get_json()
    exporter = DataExporter()

    result = exporter.export(
        data['data'],
        data['format'],
        data.get('options', {})
    )

    return send_file(
        BytesIO(result),
        mimetype=f'application/{data["format"]}',
        as_attachment=True,
        download_name=f'export.{data["format"]}'
    )
```

### 3.4 PL/SQL Debugger (Advanced)

```python
# backend/services/plsql_debugger.py

class PLSQLDebugger:
    """Debug PL/SQL code using DBMS_DEBUG"""

    def __init__(self, connection_id: int):
        self.connection_id = connection_id
        self.pool = OracleConnectionPool()
        self.breakpoints = []
        self.session_id = None

    def start_debug_session(self, schema: str, object_name: str,
                           object_type: str) -> dict:
        """Initialize debug session"""
        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()

            # Initialize debugging
            cursor.execute("BEGIN DBMS_DEBUG.INITIALIZE; END;")
            cursor.execute("BEGIN :session_id := DBMS_DEBUG.START_SESSION; END;",
                         session_id=cursor.var(str))

            self.session_id = cursor.getvalue(0)

            return {
                'success': True,
                'session_id': self.session_id,
                'message': 'Debug session started'
            }

    def set_breakpoint(self, line_number: int) -> dict:
        """Set breakpoint at line number"""
        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                BEGIN
                    DBMS_DEBUG.SET_BREAKPOINT(
                        program => :program,
                        line => :line,
                        breakpoint => :bp_id
                    );
                END;
            """, program=self.current_program, line=line_number,
                 bp_id=cursor.var(int))

            bp_id = cursor.getvalue(0)
            self.breakpoints.append(bp_id)

            return {
                'success': True,
                'breakpoint_id': bp_id
            }

    def step_over(self) -> dict:
        """Step over current line"""
        pass

    def step_into(self) -> dict:
        """Step into function/procedure"""
        pass

    def get_variables(self) -> dict:
        """Get current variable values"""
        pass
```

### 3.5 Performance Analysis Tools

```python
# backend/services/performance_analyzer.py

class PerformanceAnalyzer:
    """Analyze query and database performance"""

    def __init__(self, connection_id: int):
        self.connection_id = connection_id
        self.pool = OracleConnectionPool()

    def analyze_query(self, sql: str) -> dict:
        """Comprehensive query analysis"""
        with self.pool.get_connection(self.connection_id) as conn:
            cursor = conn.cursor()

            # Get execution plan
            plan = self._get_execution_plan(cursor, sql)

            # Get statistics
            stats = self._get_query_statistics(cursor, sql)

            # Get recommendations
            recommendations = self._get_recommendations(plan, stats)

            return {
                'execution_plan': plan,
                'statistics': stats,
                'recommendations': recommendations
            }

    def get_table_statistics(self, schema: str, table: str) -> dict:
        """Get table statistics for optimization"""
        sql = """
            SELECT
                NUM_ROWS,
                BLOCKS,
                AVG_ROW_LEN,
                LAST_ANALYZED,
                STALE_STATS
            FROM ALL_TAB_STATISTICS
            WHERE OWNER = :schema AND TABLE_NAME = :table
        """
        # Implementation
        pass

    def get_index_usage(self, schema: str, table: str) -> list:
        """Analyze index usage statistics"""
        sql = """
            SELECT
                i.INDEX_NAME,
                u.TOTAL_ACCESS_COUNT,
                u.TOTAL_EXEC_COUNT,
                u.TOTAL_ROWS_RETURNED
            FROM ALL_INDEXES i
            LEFT JOIN V$INDEX_USAGE_INFO u
                ON i.INDEX_NAME = u.INDEX_NAME AND i.OWNER = u.OWNER
            WHERE i.OWNER = :schema AND i.TABLE_NAME = :table
        """
        # Implementation
        pass

    def suggest_indexes(self, sql: str) -> list:
        """Suggest missing indexes based on query"""
        # Analyze WHERE clauses, JOIN conditions
        # Return index recommendations
        pass

    def get_session_statistics(self) -> dict:
        """Get current session performance metrics"""
        sql = """
            SELECT
                s.SID,
                s.SERIAL#,
                s.USERNAME,
                s.STATUS,
                s.LOGON_TIME,
                ss.NAME,
                ss.VALUE
            FROM V$SESSION s
            JOIN V$SESSTAT ss ON s.SID = ss.SID
            JOIN V$STATNAME sn ON ss.STATISTIC# = sn.STATISTIC#
            WHERE s.SID = SYS_CONTEXT('USERENV', 'SID')
            AND sn.NAME IN ('CPU used by this session',
                           'physical reads',
                           'db block gets',
                           'consistent gets')
        """
        # Implementation
        pass
```

---

## Phase 4: Enterprise Features

**Timeline:** 10-12 weeks
**Goal:** Add collaboration, administration, and enterprise-grade features

### 4.1 User Management & Authentication

```python
# backend/models/user.py

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))

    # Profile
    full_name = db.Column(db.String(200))
    avatar_url = db.Column(db.String(255))

    # Settings
    preferences = db.Column(db.JSON, default={})
    theme = db.Column(db.String(20), default='dark')
    default_connection_id = db.Column(db.Integer)

    # Role-based access
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'viewer'
    is_active = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Team(db.Model):
    """Teams for collaboration"""
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Shared resources
    members = db.relationship('TeamMember', backref='team')
    shared_connections = db.relationship('SharedConnection', backref='team')
    shared_queries = db.relationship('SharedQuery', backref='team')

class TeamMember(db.Model):
    __tablename__ = 'team_members'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    role = db.Column(db.String(20))  # 'owner', 'admin', 'member', 'viewer'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 4.2 Query Sharing & Collaboration

```python
# backend/models/shared_resources.py

class SharedQuery(db.Model):
    """Shared queries within teams"""
    __tablename__ = 'shared_queries'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    name = db.Column(db.String(200))
    description = db.Column(db.Text)
    sql_text = db.Column(db.Text, nullable=False)

    category = db.Column(db.String(50))
    tags = db.Column(db.JSON)

    is_public = db.Column(db.Boolean, default=False)
    version = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Versioning
    versions = db.relationship('QueryVersion', backref='query')

class QueryVersion(db.Model):
    """Query version history"""
    __tablename__ = 'query_versions'

    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('shared_queries.id'))

    version_number = db.Column(db.Integer)
    sql_text = db.Column(db.Text)
    change_description = db.Column(db.Text)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 4.3 Scheduled Queries & Reporting

```python
# backend/services/scheduler.py

from celery import Celery
from datetime import datetime, timedelta

celery = Celery('plsql_workbench')

class ScheduledQuery(db.Model):
    """Scheduled query execution"""
    __tablename__ = 'scheduled_queries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    connection_id = db.Column(db.Integer, db.ForeignKey('oracle_connections.id'))

    name = db.Column(db.String(200))
    sql_text = db.Column(db.Text, nullable=False)

    # Schedule (cron format)
    schedule_cron = db.Column(db.String(100))
    next_run = db.Column(db.DateTime)

    # Output options
    export_format = db.Column(db.String(20))  # csv, xlsx, json
    email_recipients = db.Column(db.JSON)
    store_results = db.Column(db.Boolean, default=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Execution history
    executions = db.relationship('ScheduledQueryExecution', backref='query')

@celery.task
def execute_scheduled_query(query_id: int):
    """Execute scheduled query"""
    query = ScheduledQuery.query.get(query_id)

    # Execute query
    executor = QueryExecutor(query.connection_id)
    result = executor.execute_query(query.sql_text)

    # Export results
    if result['success']:
        exporter = DataExporter()
        export_data = exporter.export(result, query.export_format)

        # Email results
        if query.email_recipients:
            send_email(
                to=query.email_recipients,
                subject=f"Scheduled Query: {query.name}",
                body="Query results attached",
                attachments=[{
                    'filename': f'{query.name}.{query.export_format}',
                    'data': export_data
                }]
            )

        # Store execution record
        execution = ScheduledQueryExecution(
            query_id=query_id,
            executed_at=datetime.utcnow(),
            success=True,
            row_count=result['row_count'],
            execution_time_ms=result['execution_time_ms']
        )
        db.session.add(execution)
    else:
        # Log error
        execution = ScheduledQueryExecution(
            query_id=query_id,
            executed_at=datetime.utcnow(),
            success=False,
            error_message=result['error']
        )
        db.session.add(execution)

    # Update next run time
    query.next_run = calculate_next_run(query.schedule_cron)
    db.session.commit()
```

### 4.4 Audit Logging

```python
# backend/models/audit_log.py

class AuditLog(db.Model):
    """Audit trail for compliance"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    connection_id = db.Column(db.Integer, db.ForeignKey('oracle_connections.id'))

    action = db.Column(db.String(50))  # 'query', 'ddl', 'unwrap', 'export'
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.String(200))

    sql_text = db.Column(db.Text)
    success = db.Column(db.Boolean)

    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @classmethod
    def log(cls, action: str, **kwargs):
        """Create audit log entry"""
        log_entry = cls(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            **kwargs
        )
        db.session.add(log_entry)
        db.session.commit()

# Decorator for auditing
def audit_action(action: str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)

            # Log action
            AuditLog.log(
                action=action,
                connection_id=request.json.get('connection_id'),
                sql_text=request.json.get('sql'),
                success=result.get('success', False)
            )

            return result
        return decorated_function
    return decorator

# Usage
@queries_bp.route('/api/query/execute', methods=['POST'])
@login_required
@audit_action('query_execute')
def execute_query():
    # Implementation
    pass
```

### 4.5 Advanced Administration Dashboard

```python
# backend/api/admin.py

@admin_bp.route('/api/admin/stats', methods=['GET'])
@login_required
@admin_required
def get_admin_stats():
    """Get system-wide statistics"""
    stats = {
        'users': {
            'total': User.query.count(),
            'active_30d': User.query.filter(
                User.last_login >= datetime.utcnow() - timedelta(days=30)
            ).count()
        },
        'connections': {
            'total': OracleConnection.query.count(),
            'active': OracleConnection.query.filter_by(is_active=True).count()
        },
        'queries': {
            'total': QueryHistory.query.count(),
            'last_24h': QueryHistory.query.filter(
                QueryHistory.executed_at >= datetime.utcnow() - timedelta(hours=24)
            ).count(),
            'avg_execution_time': db.session.query(
                func.avg(QueryHistory.execution_time_ms)
            ).scalar()
        },
        'unwraps': {
            'total': AuditLog.query.filter_by(action='unwrap').count(),
            'last_24h': AuditLog.query.filter(
                AuditLog.action == 'unwrap',
                AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ).count()
        }
    }
    return jsonify(stats)

@admin_bp.route('/api/admin/activity', methods=['GET'])
@admin_required
def get_activity_feed():
    """Recent system activity"""
    activities = AuditLog.query.order_by(
        AuditLog.timestamp.desc()
    ).limit(100).all()

    return jsonify([a.to_dict() for a in activities])
```

---

## Technical Stack

### Backend
- **Python 3.10+**
- **Flask 2.3+** - Web framework
- **SQLAlchemy 2.0+** - ORM for app database
- **cx_Oracle 8.3+** or **python-oracledb** - Oracle connectivity
- **Celery 5.3+** - Async task queue
- **Redis 7.0+** - Caching and Celery broker
- **Flask-Login** - Authentication
- **Flask-CORS** - CORS support
- **cryptography** - Encryption
- **marshmallow** - Serialization/validation
- **openpyxl** - Excel export

### Frontend
- **Vue 3** or **React 18**
- **TypeScript**
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Monaco Editor** - SQL editor
- **Chart.js** - Visualizations
- **Axios** - HTTP client
- **Pinia** (Vue) or **Redux** (React) - State management
- **Socket.io** - Real-time updates

### Database
- **PostgreSQL 14+** or **SQLite** - App metadata
- **Oracle 11g-21c** - Target database

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy
- **Gunicorn** - WSGI server
- **Supervisor** - Process management

---

## Security Architecture

### 1. Connection Credentials
- **Encryption at rest**: AES-256 encryption using Fernet
- **Encryption in transit**: TLS/SSL for all connections
- **Key management**: Environment variables, never committed
- **Vault integration**: Optional HashiCorp Vault support

### 2. Authentication & Authorization
- **JWT tokens** for API authentication
- **Role-based access control** (RBAC)
- **Session management** with secure cookies
- **Password policies**: Min 12 chars, complexity requirements
- **2FA support**: TOTP-based two-factor authentication

### 3. SQL Injection Prevention
```python
# NEVER do this
cursor.execute(f"SELECT * FROM {table_name}")  # ❌

# Always use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = :id", {'id': user_id})  # ✅

# Validate table/column names from whitelist
ALLOWED_TABLES = ['employees', 'departments']
if table_name not in ALLOWED_TABLES:
    raise ValueError("Invalid table name")
```

### 4. Input Validation
- **Max query length**: 1MB
- **Max result rows**: 10,000 (configurable)
- **Query timeout**: 5 minutes
- **File upload limits**: 50MB
- **Rate limiting**: 100 requests/minute per user

### 5. Audit & Compliance
- Log all data access
- Track DDL/DML operations
- Export audit logs for compliance
- GDPR compliance features

---

## UI/UX Design

### Layout Structure
```
┌─────────────────────────────────────────────────────┐
│  Header: Logo | Connections Dropdown | User Menu    │
├──────────┬──────────────────────────────────────────┤
│          │  Main Content Area                       │
│  Sidebar │  ┌────────────────────────────────────┐  │
│          │  │  SQL Editor (Monaco)               │  │
│  - Home  │  │  SELECT * FROM employees           │  │
│  - Query │  │  WHERE dept_id = 10;               │  │
│  - Schema│  │                                    │  │
│  - Unwrap│  └────────────────────────────────────┘  │
│  - Tools │  [ Execute ] [ Explain ] [ Format ]     │
│  - Admin │  ┌────────────────────────────────────┐  │
│          │  │  Results Grid                      │  │
│          │  │  ID | NAME      | SALARY | ...     │  │
│          │  │  ───┼───────────┼────────┼───      │  │
│          │  │  1  | John Doe  | 50000  | ...     │  │
│          │  │  2  | Jane Smith| 60000  | ...     │  │
│          │  └────────────────────────────────────┘  │
│          │  Rows: 2 | Time: 23ms | [Export ▼]      │
└──────────┴──────────────────────────────────────────┘
```

### Key UI Components

1. **SQL Editor**
   - Syntax highlighting
   - Auto-completion
   - Line numbers
   - Error markers
   - Multiple tabs

2. **Results Grid**
   - Virtual scrolling (handle millions of rows)
   - Column sorting
   - Filtering
   - Copy cells/rows
   - Export options

3. **Schema Browser**
   - Tree view: Schemas → Tables → Columns
   - Search/filter
   - Context menus (View DDL, Query, etc.)
   - Drag-and-drop to editor

4. **Unwrapper Interface**
   - Side-by-side view (wrapped | unwrapped)
   - Syntax highlighting for both
   - Download/copy buttons
   - Batch processing queue

### Themes
- **Dark Theme** (default): #1a1b26 background
- **Light Theme**: #ffffff background
- **High Contrast**: Accessibility mode

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_unwrapper.py

def test_decode_valid_wrapped_sql():
    """Test unwrapping valid Oracle wrapped code"""
    wrapped = load_fixture('valid_wrapped_package.txt')
    service = UnwrapperService()
    result = service.unwrap(wrapped)

    assert result['success'] is True
    assert 'CREATE OR REPLACE PACKAGE' in result['unwrapped']
    assert result['format_detected'] == '11g'

def test_decode_invalid_format():
    """Test handling of invalid format"""
    service = UnwrapperService()

    with pytest.raises(InvalidFormatError):
        service.unwrap("not wrapped sql")

# tests/unit/test_query_executor.py

def test_execute_select_query(mock_connection):
    """Test SELECT query execution"""
    executor = QueryExecutor(connection_id=1)
    result = executor.execute_query("SELECT 1 FROM DUAL")

    assert result['success'] is True
    assert len(result['rows']) == 1

def test_query_timeout(mock_connection):
    """Test query timeout handling"""
    executor = QueryExecutor(connection_id=1)
    executor.QUERY_TIMEOUT = 1

    result = executor.execute_query("SELECT * FROM huge_table")
    assert result['success'] is False
    assert 'timeout' in result['error'].lower()
```

### Integration Tests
```python
# tests/integration/test_api.py

def test_unwrap_api_endpoint(client, auth_headers):
    """Test unwrap API endpoint"""
    response = client.post(
        '/api/unwrap',
        json={
            'content': load_fixture('wrapped.txt'),
            'format': 'auto'
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

def test_query_execution_flow(client, test_connection):
    """Test complete query execution flow"""
    # 1. Create connection
    # 2. Test connection
    # 3. Execute query
    # 4. Export results
    pass
```

### Load Testing
```python
# tests/load/locustfile.py

from locust import HttpUser, task, between

class WorkbenchUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def execute_query(self):
        self.client.post('/api/query/execute', json={
            'connection_id': 1,
            'sql': 'SELECT * FROM employees WHERE ROWNUM <= 100'
        })

    @task(1)
    def unwrap_code(self):
        self.client.post('/api/unwrap', json={
            'content': self.wrapped_sql,
            'format': 'auto'
        })
```

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Small Teams)

```yaml
# docker-compose.yml

version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://backend:5000

  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/plsql_workbench
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - db
      - redis
    volumes:
      - ./backend:/app

  celery:
    build: ./backend
    command: celery -A app.celery worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/plsql_workbench
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=plsql_workbench
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend

volumes:
  postgres_data:
  redis_data:
```

### Option 2: Kubernetes (Enterprise)

```yaml
# k8s/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: plsql-workbench-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: plsql-workbench-backend
  template:
    metadata:
      labels:
        app: plsql-workbench-backend
    spec:
      containers:
      - name: backend
        image: plsql-workbench/backend:latest
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
        - name: ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: encryption-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Option 3: Cloud-Native (AWS)

```
Architecture:
┌─────────────┐
│   Route 53  │  DNS
└──────┬──────┘
       │
┌──────▼──────┐
│ CloudFront  │  CDN (Frontend)
└──────┬──────┘
       │
┌──────▼──────┐
│     ALB     │  Load Balancer
└──────┬──────┘
       │
    ┌──▼───────────────┐
    │  ECS Fargate     │  Backend containers
    │  - API Service   │
    │  - Celery Worker │
    └──┬───────────────┘
       │
    ┌──▼───────────────┐
    │  RDS PostgreSQL  │  App database
    └──────────────────┘

    ┌──────────────────┐
    │  ElastiCache     │  Redis
    └──────────────────┘

    ┌──────────────────┐
    │  Secrets Manager │  Credentials
    └──────────────────┘
```

---

## Implementation Roadmap

### Months 1-2: Phase 1 (Foundation)
- [ ] Project restructuring
- [ ] Enhanced unwrapper with validation
- [ ] Security hardening
- [ ] Basic API design
- [ ] Unit tests

### Months 3-4: Phase 2 (Database Connectivity)
- [ ] Connection management
- [ ] Query executor
- [ ] Schema inspector
- [ ] Connection pooling
- [ ] Integration tests

### Months 5-6: Phase 3 (Advanced Features)
- [ ] Monaco editor integration
- [ ] Query history/favorites
- [ ] Data export (CSV, Excel, JSON)
- [ ] Performance analyzer
- [ ] Modern frontend (Vue/React)

### Months 7-8: Phase 4 (Enterprise)
- [ ] User authentication
- [ ] Team collaboration
- [ ] Scheduled queries
- [ ] Audit logging
- [ ] Admin dashboard

### Months 9-10: Polish & Production
- [ ] Load testing
- [ ] Security audit
- [ ] Documentation
- [ ] Deployment automation
- [ ] Monitoring setup

---

## Success Metrics

### Technical Metrics
- **Query execution**: < 100ms overhead
- **Unwrap speed**: < 1s for 100KB file
- **Uptime**: 99.9% availability
- **API response**: < 200ms p95
- **Concurrent users**: 100+ simultaneous

### User Metrics
- **Adoption**: 50+ active users in 6 months
- **Engagement**: 80% weekly active users
- **Satisfaction**: 4.5+ star rating
- **Query volume**: 1000+ queries/day

---

## Next Steps

1. **Review this guide** with stakeholders
2. **Prioritize features** based on user needs
3. **Set up development environment**
4. **Create detailed tickets** for Phase 1
5. **Begin implementation** following the roadmap

---

**Document Version**: 1.0
**Last Updated**: 2025-11-20
**Maintained By**: Development Team
