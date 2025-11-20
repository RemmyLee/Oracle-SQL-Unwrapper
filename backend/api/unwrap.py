"""
Unwrapper API endpoints
Provides REST API for Oracle PL/SQL unwrapping
"""

from flask import Blueprint, request, jsonify, current_app
from backend.services.unwrapper import UnwrapperService
from backend.utils.validators import UnwrapValidator
import logging


logger = logging.getLogger(__name__)

# Create blueprint
unwrap_bp = Blueprint('unwrap', __name__)


@unwrap_bp.route('/unwrap', methods=['POST'])
def unwrap_code():
    """
    Unwrap Oracle PL/SQL code

    POST /api/unwrap

    Request JSON:
    {
        "content": "wrapped SQL content",
        "format": "auto",  # Optional: 'auto', '10g', '11g', '12c', '19c', '20c'
        "options": {
            "preserve_formatting": true
        }
    }

    Response JSON:
    {
        "success": true,
        "result": {
            "unwrapped": "unwrapped SQL code",
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
    try:
        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'message': 'Request body must be JSON'
            }), 400

        content = data.get('content')
        if not content:
            return jsonify({
                'success': False,
                'error': 'Missing content',
                'message': 'The "content" field is required'
            }), 400

        format_type = data.get('format', 'auto')
        options = data.get('options', {})

        # Validate input
        is_valid, error_msg = UnwrapValidator.validate_wrapped_input(content)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'message': error_msg
            }), 400

        # Get configuration
        max_size = current_app.config.get('UNWRAP_MAX_INPUT_SIZE', 10 * 1024 * 1024)
        timeout = current_app.config.get('UNWRAP_TIMEOUT_SECONDS', 30)

        # Unwrap the code
        service = UnwrapperService(max_size=max_size, timeout=timeout)
        result = service.unwrap(content, format_type)

        if not result['success']:
            return jsonify(result), 400

        # Build response
        response = {
            'success': True,
            'result': {
                'unwrapped': result['unwrapped'],
                'format_detected': result['format_detected'],
                'statistics': result['metadata']
            },
            'warnings': result.get('warnings', [])
        }

        logger.info(f"Successfully unwrapped content (format: {result['format_detected']})")

        return jsonify(response), 200

    except Exception as e:
        logger.exception(f"Error in unwrap endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@unwrap_bp.route('/unwrap/batch', methods=['POST'])
def unwrap_batch():
    """
    Unwrap multiple files in batch

    POST /api/unwrap/batch

    Request JSON:
    {
        "files": [
            {"name": "package1.sql", "content": "wrapped content 1"},
            {"name": "package2.sql", "content": "wrapped content 2"}
        ]
    }

    Response JSON:
    {
        "success": true,
        "results": [
            {
                "filename": "package1.sql",
                "success": true,
                "unwrapped": "..."
            },
            ...
        ],
        "summary": {
            "total": 2,
            "successful": 2,
            "failed": 0
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'files' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing files',
                'message': 'The "files" array is required'
            }), 400

        files = data['files']

        if not isinstance(files, list):
            return jsonify({
                'success': False,
                'error': 'Invalid format',
                'message': 'The "files" field must be an array'
            }), 400

        if len(files) > 100:
            return jsonify({
                'success': False,
                'error': 'Too many files',
                'message': 'Maximum 100 files per batch request'
            }), 400

        # Get configuration
        max_size = current_app.config.get('UNWRAP_MAX_INPUT_SIZE', 10 * 1024 * 1024)
        timeout = current_app.config.get('UNWRAP_TIMEOUT_SECONDS', 30)

        # Process batch
        service = UnwrapperService(max_size=max_size, timeout=timeout)
        results = service.unwrap_batch(files)

        # Calculate summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful

        response = {
            'success': True,
            'results': results,
            'summary': {
                'total': len(results),
                'successful': successful,
                'failed': failed
            }
        }

        logger.info(f"Batch unwrap completed: {successful}/{len(results)} successful")

        return jsonify(response), 200

    except Exception as e:
        logger.exception(f"Error in batch unwrap endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@unwrap_bp.route('/unwrap/validate', methods=['POST'])
def validate_wrapped():
    """
    Validate wrapped content without unwrapping

    POST /api/unwrap/validate

    Request JSON:
    {
        "content": "wrapped SQL content"
    }

    Response JSON:
    {
        "success": true,
        "is_valid": true,
        "format": "11g",
        "statistics": {
            "size_bytes": 1024,
            "line_count": 50
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing content',
                'message': 'The "content" field is required'
            }), 400

        content = data['content']

        # Get configuration
        max_size = current_app.config.get('UNWRAP_MAX_INPUT_SIZE', 10 * 1024 * 1024)
        timeout = current_app.config.get('UNWRAP_TIMEOUT_SECONDS', 30)

        # Get statistics
        service = UnwrapperService(max_size=max_size, timeout=timeout)
        stats = service.get_statistics(content)

        return jsonify({
            'success': True,
            'is_valid': stats['is_valid'],
            'format': stats['format'],
            'statistics': {
                'size_bytes': stats['size_bytes'],
                'line_count': stats['line_count']
            }
        }), 200

    except Exception as e:
        logger.exception(f"Error in validate endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@unwrap_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint

    GET /api/health

    Response JSON:
    {
        "status": "healthy",
        "version": "2.0.0"
    }
    """
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'service': 'PL/SQL Workbench'
    }), 200
