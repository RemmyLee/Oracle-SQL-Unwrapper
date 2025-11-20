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
  - GET  /                    Main application page
  - POST /api/unwrap          Unwrap Oracle PL/SQL code
  - POST /api/unwrap/batch    Batch unwrap multiple files
  - POST /api/unwrap/validate Validate wrapped content
  - GET  /api/health          Health check

Press CTRL+C to quit
""")

    # Run server
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug
    )
