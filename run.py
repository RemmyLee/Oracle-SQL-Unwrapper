#!/usr/bin/env python3
"""
PL/SQL Workbench - Application Entry Point
Run the Flask development server
"""

import os
import sys

# Add backend to Python path
sys.path.insert(0, os.path.dirname(__file__))

from backend.app import create_app


if __name__ == '__main__':
    # Create app
    app = create_app()

    # Get configuration
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 3117))
    debug = app.config.get('DEBUG', True)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           PL/SQL Workbench - Oracle Database Toolkit         ║
╠══════════════════════════════════════════════════════════════╣
║  Version: 2.0.0                                              ║
║  Environment: {app.config.get('ENV', 'development').upper():<47} ║
║  Running on: http://{host}:{port:<43} ║
║  Debug Mode: {str(debug):<47} ║
╚══════════════════════════════════════════════════════════════╝

Available Endpoints:

  Unwrapper:
  - POST /api/unwrap                 Unwrap Oracle PL/SQL code
  - POST /api/unwrap/batch           Batch unwrap multiple files
  - POST /api/unwrap/validate        Validate wrapped content
  - POST /api/unwrap-from-db         Unwrap directly from database

  Connections:
  - GET    /api/connections          List all connections
  - POST   /api/connections          Create new connection
  - GET    /api/connections/<id>     Get connection details
  - PUT    /api/connections/<id>     Update connection
  - DELETE /api/connections/<id>     Delete connection
  - POST   /api/connections/<id>/test Test connection

  Queries:
  - POST /api/query/execute          Execute SQL query
  - POST /api/query/execute-statement Execute DML/DDL statement
  - GET  /api/query/history          Get query history
  - GET  /api/schema/<id>/<schema>/objects Get schema objects
  - GET  /api/source/<id>/<schema>/<type>/<name> Get source code

  Health:
  - GET  /api/health                 Health check

Press CTRL+C to quit
""")

    # Run server
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug
    )
