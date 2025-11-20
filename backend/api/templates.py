"""
Query Templates API endpoints
Provides pre-built SQL templates and snippets
"""

from flask import Blueprint, jsonify
import json
import os
import logging


logger = logging.getLogger(__name__)

# Create blueprint
templates_bp = Blueprint('templates', __name__)

# Load templates from JSON file
TEMPLATES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'data',
    'query_templates.json'
)


def load_templates():
    """Load templates from JSON file"""
    try:
        with open(TEMPLATES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Templates file not found: {TEMPLATES_FILE}")
        return {"categories": []}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in templates file: {str(e)}")
        return {"categories": []}


@templates_bp.route('/templates', methods=['GET'])
def list_templates():
    """
    List all query templates organized by category

    GET /api/templates

    Response:
    {
        "success": true,
        "categories": [
            {
                "name": "DDL - Tables",
                "description": "...",
                "templates": [...]
            }
        ]
    }
    """
    try:
        templates_data = load_templates()

        return jsonify({
            'success': True,
            'categories': templates_data.get('categories', [])
        }), 200

    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list templates',
            'message': str(e)
        }), 500


@templates_bp.route('/templates/categories', methods=['GET'])
def list_categories():
    """
    List all template categories

    GET /api/templates/categories

    Response:
    {
        "success": true,
        "categories": ["DDL - Tables", "DML - Queries", ...]
    }
    """
    try:
        templates_data = load_templates()
        categories = [cat['name'] for cat in templates_data.get('categories', [])]

        return jsonify({
            'success': True,
            'categories': categories
        }), 200

    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list categories',
            'message': str(e)
        }), 500


@templates_bp.route('/templates/category/<category_name>', methods=['GET'])
def get_category_templates(category_name):
    """
    Get templates for specific category

    GET /api/templates/category/<category_name>

    Response:
    {
        "success": true,
        "category": {
            "name": "...",
            "description": "...",
            "templates": [...]
        }
    }
    """
    try:
        templates_data = load_templates()

        # Find category
        category = None
        for cat in templates_data.get('categories', []):
            if cat['name'] == category_name:
                category = cat
                break

        if not category:
            return jsonify({
                'success': False,
                'error': 'Category not found'
            }), 404

        return jsonify({
            'success': True,
            'category': category
        }), 200

    except Exception as e:
        logger.error(f"Error getting category templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get category templates',
            'message': str(e)
        }), 500


@templates_bp.route('/templates/search', methods=['GET'])
def search_templates():
    """
    Search templates by keyword

    GET /api/templates/search?q=select

    Query Parameters:
        q: Search query (searches name, description, tags, and SQL)

    Response:
    {
        "success": true,
        "results": [
            {
                "category": "DML - Queries",
                "template": {...}
            }
        ],
        "total": 5
    }
    """
    try:
        from flask import request

        query = request.args.get('q', '').lower()

        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query required'
            }), 400

        templates_data = load_templates()
        results = []

        # Search through all templates
        for category in templates_data.get('categories', []):
            for template in category.get('templates', []):
                # Search in name, description, tags, and SQL
                searchable_text = ' '.join([
                    template.get('name', ''),
                    template.get('description', ''),
                    ' '.join(template.get('tags', [])),
                    template.get('sql', '')
                ]).lower()

                if query in searchable_text:
                    results.append({
                        'category': category['name'],
                        'template': template
                    })

        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        logger.error(f"Error searching templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to search templates',
            'message': str(e)
        }), 500


@templates_bp.route('/templates/tags', methods=['GET'])
def list_tags():
    """
    List all unique tags from templates

    GET /api/templates/tags

    Response:
    {
        "success": true,
        "tags": ["ddl", "dml", "plsql", ...]
    }
    """
    try:
        templates_data = load_templates()
        tags = set()

        # Collect all unique tags
        for category in templates_data.get('categories', []):
            for template in category.get('templates', []):
                tags.update(template.get('tags', []))

        return jsonify({
            'success': True,
            'tags': sorted(list(tags))
        }), 200

    except Exception as e:
        logger.error(f"Error listing tags: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list tags',
            'message': str(e)
        }), 500


@templates_bp.route('/templates/by-tag/<tag>', methods=['GET'])
def get_templates_by_tag(tag):
    """
    Get templates with specific tag

    GET /api/templates/by-tag/<tag>

    Response:
    {
        "success": true,
        "tag": "ddl",
        "templates": [
            {
                "category": "DDL - Tables",
                "template": {...}
            }
        ],
        "total": 4
    }
    """
    try:
        templates_data = load_templates()
        results = []

        # Find templates with this tag
        for category in templates_data.get('categories', []):
            for template in category.get('templates', []):
                if tag.lower() in [t.lower() for t in template.get('tags', [])]:
                    results.append({
                        'category': category['name'],
                        'template': template
                    })

        return jsonify({
            'success': True,
            'tag': tag,
            'templates': results,
            'total': len(results)
        }), 200

    except Exception as e:
        logger.error(f"Error getting templates by tag: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get templates by tag',
            'message': str(e)
        }), 500
