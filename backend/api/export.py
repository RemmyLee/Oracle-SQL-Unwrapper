"""
Export API endpoints
Export query results to various formats
"""

from flask import Blueprint, request, jsonify, send_file
from backend.services.data_exporter import DataExporter
from io import BytesIO
import logging


logger = logging.getLogger(__name__)

# Create blueprint
export_bp = Blueprint('export', __name__)


@export_bp.route('/export', methods=['POST'])
def export_data():
    """
    Export data to specified format

    POST /api/export

    Request:
    {
        "data": {
            "columns": ["ID", "NAME", "SALARY"],
            "rows": [[1, "John", 50000], [2, "Jane", 60000]]
        },
        "format": "xlsx",
        "options": {
            "sheet_name": "Employees",
            "freeze_header": true
        },
        "filename": "employees_export"
    }

    Response:
        File download with appropriate MIME type
    """
    try:
        data_input = request.get_json()

        if not data_input:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate required fields
        if 'data' not in data_input or 'format' not in data_input:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: data, format'
            }), 400

        data = data_input['data']
        format_type = data_input['format']
        options = data_input.get('options', {})
        base_filename = data_input.get('filename', 'export')

        # Validate data structure
        if 'columns' not in data or 'rows' not in data:
            return jsonify({
                'success': False,
                'error': 'Data must contain "columns" and "rows"'
            }), 400

        # Export data
        exporter = DataExporter()

        try:
            exported_data = exporter.export(data, format_type, options)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'Export failed',
                'message': str(e)
            }), 400
        except ImportError as e:
            return jsonify({
                'success': False,
                'error': 'Missing dependency',
                'message': str(e)
            }), 400

        # Get filename and MIME type
        filename = exporter.get_filename(format_type, base_filename)
        mimetype = exporter.get_mimetype(format_type)

        # Send file
        return send_file(
            BytesIO(exported_data),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Export failed',
            'message': str(e)
        }), 500


@export_bp.route('/export/formats', methods=['GET'])
def get_supported_formats():
    """
    Get list of supported export formats

    GET /api/export/formats

    Response:
    {
        "success": true,
        "formats": [
            {
                "format": "csv",
                "name": "CSV (Comma-Separated Values)",
                "extension": "csv",
                "mimetype": "text/csv",
                "options": [...]
            },
            ...
        ]
    }
    """
    try:
        exporter = DataExporter()

        formats_info = [
            {
                'format': 'csv',
                'name': 'CSV (Comma-Separated Values)',
                'extension': 'csv',
                'mimetype': 'text/csv',
                'description': 'Plain text format with comma-separated values',
                'options': [
                    {'name': 'delimiter', 'type': 'string', 'default': ',', 'description': 'Column delimiter'},
                    {'name': 'quote_char', 'type': 'string', 'default': '"', 'description': 'Quote character'},
                    {'name': 'include_header', 'type': 'boolean', 'default': True, 'description': 'Include header row'}
                ]
            },
            {
                'format': 'json',
                'name': 'JSON',
                'extension': 'json',
                'mimetype': 'application/json',
                'description': 'JavaScript Object Notation format',
                'options': [
                    {'name': 'format', 'type': 'string', 'default': 'array', 'description': 'Output format (array or objects)'},
                    {'name': 'pretty', 'type': 'boolean', 'default': True, 'description': 'Pretty print with indentation'}
                ]
            },
            {
                'format': 'xlsx',
                'name': 'Excel (XLSX)',
                'extension': 'xlsx',
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'description': 'Microsoft Excel format',
                'requires': 'openpyxl',
                'options': [
                    {'name': 'sheet_name', 'type': 'string', 'default': 'Query Results', 'description': 'Sheet name'},
                    {'name': 'freeze_header', 'type': 'boolean', 'default': True, 'description': 'Freeze header row'},
                    {'name': 'auto_width', 'type': 'boolean', 'default': True, 'description': 'Auto-size columns'},
                    {'name': 'header_style', 'type': 'boolean', 'default': True, 'description': 'Style header row'}
                ]
            },
            {
                'format': 'sql',
                'name': 'SQL INSERT Statements',
                'extension': 'sql',
                'mimetype': 'application/sql',
                'description': 'SQL INSERT statements for importing data',
                'options': [
                    {'name': 'table_name', 'type': 'string', 'default': 'exported_data', 'description': 'Target table name'},
                    {'name': 'include_drop', 'type': 'boolean', 'default': False, 'description': 'Include DROP TABLE statement'},
                    {'name': 'include_create', 'type': 'boolean', 'default': False, 'description': 'Include CREATE TABLE statement'},
                    {'name': 'batch_size', 'type': 'number', 'default': 100, 'description': 'Number of rows per batch'}
                ]
            },
            {
                'format': 'markdown',
                'name': 'Markdown Table',
                'extension': 'md',
                'mimetype': 'text/markdown',
                'description': 'Markdown-formatted table',
                'options': [
                    {'name': 'alignment', 'type': 'string', 'default': 'left', 'description': 'Column alignment (left, center, right)'}
                ]
            },
            {
                'format': 'html',
                'name': 'HTML Table',
                'extension': 'html',
                'mimetype': 'text/html',
                'description': 'HTML table with styling',
                'options': [
                    {'name': 'style', 'type': 'string', 'default': 'styled', 'description': 'Table style (basic or styled)'},
                    {'name': 'title', 'type': 'string', 'default': 'Query Results', 'description': 'Page title'}
                ]
            }
        ]

        return jsonify({
            'success': True,
            'formats': formats_info
        }), 200

    except Exception as e:
        logger.error(f"Error getting formats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get formats',
            'message': str(e)
        }), 500


@export_bp.route('/export/preview', methods=['POST'])
def preview_export():
    """
    Preview export without downloading (returns first few rows)

    POST /api/export/preview

    Request:
    {
        "data": {...},
        "format": "csv",
        "preview_rows": 5
    }

    Response:
    {
        "success": true,
        "preview": "preview content as string",
        "total_rows": 100,
        "preview_rows": 5
    }
    """
    try:
        data_input = request.get_json()

        if not data_input:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        data = data_input['data']
        format_type = data_input['format']
        preview_rows = data_input.get('preview_rows', 5)
        options = data_input.get('options', {})

        # Limit data to preview rows
        preview_data = {
            'columns': data['columns'],
            'rows': data['rows'][:preview_rows]
        }

        # Export preview
        exporter = DataExporter()
        exported_data = exporter.export(preview_data, format_type, options)

        # Decode to string for preview
        preview_text = exported_data.decode('utf-8')

        # Limit preview length
        max_preview_length = 5000
        if len(preview_text) > max_preview_length:
            preview_text = preview_text[:max_preview_length] + '\n\n... (truncated)'

        return jsonify({
            'success': True,
            'preview': preview_text,
            'total_rows': len(data['rows']),
            'preview_rows': len(preview_data['rows']),
            'format': format_type
        }), 200

    except Exception as e:
        logger.error(f"Preview error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Preview failed',
            'message': str(e)
        }), 500
