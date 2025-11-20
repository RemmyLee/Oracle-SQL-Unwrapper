"""
Unit tests for Templates API
"""

import pytest
import json
from backend.api.templates import templates_bp, load_templates


@pytest.fixture
def client(app):
    """Test client fixture"""
    return app.test_client()


class TestTemplatesAPI:
    """Test cases for Templates API endpoints"""

    def test_load_templates(self):
        """Test loading templates from JSON file"""
        templates_data = load_templates()

        assert 'categories' in templates_data
        assert isinstance(templates_data['categories'], list)
        assert len(templates_data['categories']) > 0

    def test_list_templates(self, client):
        """Test GET /api/templates"""
        response = client.get('/api/templates')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['success'] is True
        assert 'categories' in data
        assert len(data['categories']) > 0

        # Check category structure
        category = data['categories'][0]
        assert 'name' in category
        assert 'description' in category
        assert 'templates' in category

    def test_list_categories(self, client):
        """Test GET /api/templates/categories"""
        response = client.get('/api/templates/categories')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['success'] is True
        assert 'categories' in data
        assert isinstance(data['categories'], list)
        assert len(data['categories']) > 0

    def test_get_category_templates(self, client):
        """Test GET /api/templates/category/<name>"""
        # First get available categories
        response = client.get('/api/templates/categories')
        categories = json.loads(response.data)['categories']

        # Get templates for first category
        if categories:
            category_name = categories[0]
            response = client.get(f'/api/templates/category/{category_name}')
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data['success'] is True
            assert 'category' in data
            assert data['category']['name'] == category_name
            assert 'templates' in data['category']

    def test_get_category_templates_not_found(self, client):
        """Test GET /api/templates/category/<name> with non-existent category"""
        response = client.get('/api/templates/category/NonExistentCategory')
        data = json.loads(response.data)

        assert response.status_code == 404
        assert data['success'] is False

    def test_search_templates(self, client):
        """Test GET /api/templates/search?q=select"""
        response = client.get('/api/templates/search?q=select')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['success'] is True
        assert 'results' in data
        assert 'total' in data
        assert isinstance(data['results'], list)

        # Should find some SELECT templates
        assert data['total'] > 0

    def test_search_templates_no_query(self, client):
        """Test search without query parameter"""
        response = client.get('/api/templates/search')
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data['success'] is False

    def test_search_templates_case_insensitive(self, client):
        """Test case-insensitive search"""
        response1 = client.get('/api/templates/search?q=SELECT')
        response2 = client.get('/api/templates/search?q=select')

        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)

        assert data1['total'] == data2['total']

    def test_list_tags(self, client):
        """Test GET /api/templates/tags"""
        response = client.get('/api/templates/tags')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['success'] is True
        assert 'tags' in data
        assert isinstance(data['tags'], list)
        assert len(data['tags']) > 0

        # Tags should be sorted
        tags = data['tags']
        assert tags == sorted(tags)

    def test_get_templates_by_tag(self, client):
        """Test GET /api/templates/by-tag/<tag>"""
        # First get available tags
        response = client.get('/api/templates/tags')
        tags = json.loads(response.data)['tags']

        # Get templates for first tag
        if tags:
            tag = tags[0]
            response = client.get(f'/api/templates/by-tag/{tag}')
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data['success'] is True
            assert 'tag' in data
            assert 'templates' in data
            assert 'total' in data
            assert data['total'] > 0

            # Verify all templates have the tag
            for item in data['templates']:
                template_tags = [t.lower() for t in item['template']['tags']]
                assert tag.lower() in template_tags

    def test_template_structure(self, client):
        """Test that templates have required fields"""
        response = client.get('/api/templates')
        data = json.loads(response.data)

        categories = data['categories']
        assert len(categories) > 0

        # Check first template has required fields
        templates = categories[0]['templates']
        assert len(templates) > 0

        template = templates[0]
        assert 'name' in template
        assert 'description' in template
        assert 'sql' in template
        assert 'tags' in template

        # SQL should not be empty
        assert len(template['sql']) > 0

    def test_search_in_sql_content(self, client):
        """Test search finds matches in SQL content"""
        response = client.get('/api/templates/search?q=BEGIN')
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['total'] > 0

        # At least one result should have BEGIN in SQL
        has_begin = any(
            'BEGIN' in result['template']['sql'].upper()
            for result in data['results']
        )
        assert has_begin

    def test_search_in_tags(self, client):
        """Test search finds matches in tags"""
        response = client.get('/api/templates/search?q=ddl')
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['total'] > 0

        # Results should include templates with 'ddl' tag
        has_ddl_tag = any(
            'ddl' in [t.lower() for t in result['template']['tags']]
            for result in data['results']
        )
        assert has_ddl_tag


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
