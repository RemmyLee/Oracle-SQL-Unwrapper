"""
Unit tests for DataExporter service
"""

import pytest
import json
from io import BytesIO
from backend.services.data_exporter import DataExporter


class TestDataExporter:
    """Test cases for DataExporter"""

    @pytest.fixture
    def sample_data(self):
        """Sample query result data"""
        return {
            'columns': ['ID', 'NAME', 'EMAIL'],
            'rows': [
                [1, 'John Doe', 'john@example.com'],
                [2, 'Jane Smith', 'jane@example.com'],
                [3, 'Bob Wilson', 'bob@example.com']
            ]
        }

    @pytest.fixture
    def exporter(self):
        """Create DataExporter instance"""
        return DataExporter()

    def test_supported_formats(self, exporter):
        """Test supported formats list"""
        formats = exporter.get_supported_formats()
        assert 'csv' in formats
        assert 'json' in formats
        assert 'xlsx' in formats
        assert 'sql' in formats
        assert 'markdown' in formats
        assert 'html' in formats

    def test_export_csv(self, exporter, sample_data):
        """Test CSV export"""
        result = exporter.export(sample_data, 'csv')

        assert isinstance(result, bytes)
        csv_text = result.decode('utf-8')
        assert 'ID,NAME,EMAIL' in csv_text
        assert 'John Doe' in csv_text
        assert 'Jane Smith' in csv_text

    def test_export_json(self, exporter, sample_data):
        """Test JSON export"""
        result = exporter.export(sample_data, 'json')

        assert isinstance(result, bytes)
        json_data = json.loads(result.decode('utf-8'))
        assert json_data['columns'] == sample_data['columns']
        assert len(json_data['data']) == 3

    def test_export_sql(self, exporter, sample_data):
        """Test SQL export"""
        options = {'table_name': 'users'}
        result = exporter.export(sample_data, 'sql', options)

        assert isinstance(result, bytes)
        sql_text = result.decode('utf-8')
        assert 'INSERT INTO users' in sql_text
        assert 'John Doe' in sql_text

    def test_export_markdown(self, exporter, sample_data):
        """Test Markdown export"""
        result = exporter.export(sample_data, 'markdown')

        assert isinstance(result, bytes)
        md_text = result.decode('utf-8')
        assert '| ID | NAME | EMAIL |' in md_text
        assert 'John Doe' in md_text

    def test_export_html(self, exporter, sample_data):
        """Test HTML export"""
        result = exporter.export(sample_data, 'html')

        assert isinstance(result, bytes)
        html_text = result.decode('utf-8')
        assert '<table>' in html_text
        assert '<th>ID</th>' in html_text
        assert 'John Doe' in html_text

    @pytest.mark.skipif(
        not DataExporter.OPENPYXL_AVAILABLE,
        reason="openpyxl not installed"
    )
    def test_export_xlsx(self, exporter, sample_data):
        """Test Excel export (if openpyxl available)"""
        result = exporter.export(sample_data, 'xlsx')

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_invalid_format(self, exporter, sample_data):
        """Test export with invalid format"""
        with pytest.raises(ValueError) as exc_info:
            exporter.export(sample_data, 'invalid_format')

        assert 'Unsupported format' in str(exc_info.value)

    def test_get_mimetype(self, exporter):
        """Test MIME type retrieval"""
        assert exporter.get_mimetype('csv') == 'text/csv'
        assert exporter.get_mimetype('json') == 'application/json'
        assert exporter.get_mimetype('xlsx') == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_get_filename(self, exporter):
        """Test filename generation"""
        filename = exporter.get_filename('csv', 'test_export')
        assert filename == 'test_export.csv'

        filename = exporter.get_filename('xlsx')
        assert filename.endswith('.xlsx')
        assert 'export_' in filename

    def test_csv_custom_options(self, exporter, sample_data):
        """Test CSV export with custom options"""
        options = {
            'delimiter': ';',
            'include_header': False
        }
        result = exporter.export(sample_data, 'csv', options)

        csv_text = result.decode('utf-8')
        assert ';' in csv_text
        # Header should not be included
        assert 'ID;NAME;EMAIL' not in csv_text

    def test_json_pretty_print(self, exporter, sample_data):
        """Test JSON export with pretty printing"""
        options = {'pretty': True}
        result = exporter.export(sample_data, 'json', options)

        json_text = result.decode('utf-8')
        # Pretty printed JSON should have newlines
        assert '\n' in json_text

    def test_html_custom_title(self, exporter, sample_data):
        """Test HTML export with custom title"""
        options = {'title': 'My Custom Report'}
        result = exporter.export(sample_data, 'html', options)

        html_text = result.decode('utf-8')
        assert 'My Custom Report' in html_text

    def test_empty_data(self, exporter):
        """Test export with empty data"""
        empty_data = {
            'columns': ['ID', 'NAME'],
            'rows': []
        }

        result = exporter.export(empty_data, 'csv')
        csv_text = result.decode('utf-8')

        # Should still have header
        assert 'ID,NAME' in csv_text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
