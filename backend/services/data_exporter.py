"""
Data Export Service
Export query results to various formats (CSV, Excel, JSON, SQL, Markdown)
"""

import csv
import json
from io import StringIO, BytesIO
from typing import Dict, List, Any, Optional
import logging

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


logger = logging.getLogger(__name__)


class DataExporter:
    """
    Export query results to various formats

    Supports: CSV, JSON, Excel (XLSX), SQL INSERT statements, Markdown tables
    """

    SUPPORTED_FORMATS = ['csv', 'json', 'xlsx', 'sql', 'markdown', 'html']

    def __init__(self):
        """Initialize exporter"""
        pass

    def export(self, data: Dict, format: str, options: Optional[Dict] = None) -> bytes:
        """
        Export data to specified format

        Args:
            data: Query result dict with 'columns' and 'rows'
            format: Output format ('csv', 'json', 'xlsx', 'sql', 'markdown', 'html')
            options: Format-specific options

        Returns:
            Exported data as bytes

        Raises:
            ValueError: If format is not supported
        """
        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}. Supported: {self.SUPPORTED_FORMATS}")

        options = options or {}

        if format == 'csv':
            return self._export_csv(data, options)
        elif format == 'json':
            return self._export_json(data, options)
        elif format == 'xlsx':
            return self._export_xlsx(data, options)
        elif format == 'sql':
            return self._export_sql(data, options)
        elif format == 'markdown':
            return self._export_markdown(data, options)
        elif format == 'html':
            return self._export_html(data, options)

    def _export_csv(self, data: Dict, options: Dict) -> bytes:
        """
        Export as CSV

        Options:
            delimiter: Column delimiter (default: ',')
            quote_char: Quote character (default: '"')
            include_header: Include header row (default: True)
        """
        output = StringIO()

        delimiter = options.get('delimiter', ',')
        quote_char = options.get('quote_char', '"')
        include_header = options.get('include_header', True)

        writer = csv.writer(output, delimiter=delimiter, quotechar=quote_char)

        # Write header
        if include_header:
            writer.writerow(data['columns'])

        # Write rows
        writer.writerows(data['rows'])

        return output.getvalue().encode('utf-8')

    def _export_json(self, data: Dict, options: Dict) -> bytes:
        """
        Export as JSON

        Options:
            format: 'array' (default) or 'objects'
            pretty: Pretty print (default: True)
        """
        format_type = options.get('format', 'array')
        pretty = options.get('pretty', True)

        if format_type == 'objects':
            # Convert to array of objects
            result = []
            for row in data['rows']:
                obj = {}
                for i, col in enumerate(data['columns']):
                    obj[col] = row[i]
                result.append(obj)
        else:
            # Array format
            result = {
                'columns': data['columns'],
                'rows': data['rows'],
                'row_count': len(data['rows'])
            }

        if pretty:
            json_str = json.dumps(result, indent=2, default=str)
        else:
            json_str = json.dumps(result, default=str)

        return json_str.encode('utf-8')

    def _export_xlsx(self, data: Dict, options: Dict) -> bytes:
        """
        Export as Excel (XLSX)

        Options:
            sheet_name: Sheet name (default: 'Query Results')
            freeze_header: Freeze header row (default: True)
            auto_width: Auto-size columns (default: True)
            header_style: Style header row (default: True)
        """
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required for Excel export. Install with: pip install openpyxl")

        wb = Workbook()
        ws = wb.active
        ws.title = options.get('sheet_name', 'Query Results')

        # Write header with formatting
        ws.append(data['columns'])

        if options.get('header_style', True):
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="205AA7", end_color="205AA7", fill_type="solid")
                cell.alignment = Alignment(horizontal='center')

        # Write data
        for row in data['rows']:
            # Convert all values to strings/primitives that Excel can handle
            excel_row = []
            for val in row:
                if val is None:
                    excel_row.append('')
                else:
                    excel_row.append(val)
            ws.append(excel_row)

        # Auto-size columns
        if options.get('auto_width', True):
            for column_cells in ws.columns:
                max_length = 0
                column = column_cells[0].column_letter

                for cell in column_cells:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass

                adjusted_width = min(max_length + 2, 50)  # Max 50 chars
                ws.column_dimensions[column].width = adjusted_width

        # Freeze header row
        if options.get('freeze_header', True):
            ws.freeze_panes = 'A2'

        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    def _export_sql(self, data: Dict, options: Dict) -> bytes:
        """
        Export as SQL INSERT statements

        Options:
            table_name: Target table name (default: 'exported_data')
            include_drop: Include DROP TABLE (default: False)
            include_create: Include CREATE TABLE (default: False)
            batch_size: Insert batch size (default: 100)
        """
        table_name = options.get('table_name', 'exported_data')
        include_drop = options.get('include_drop', False)
        include_create = options.get('include_create', False)
        batch_size = options.get('batch_size', 100)

        statements = []

        # DROP TABLE
        if include_drop:
            statements.append(f"DROP TABLE IF EXISTS {table_name};")
            statements.append("")

        # CREATE TABLE (simple version)
        if include_create:
            statements.append(f"CREATE TABLE {table_name} (")
            for col in data['columns']:
                statements.append(f"    {col} VARCHAR2(4000),")
            statements[-1] = statements[-1].rstrip(',')  # Remove last comma
            statements.append(");")
            statements.append("")

        # INSERT statements
        columns_str = ', '.join(data['columns'])

        for i in range(0, len(data['rows']), batch_size):
            batch = data['rows'][i:i + batch_size]

            for row in batch:
                values = []
                for val in row:
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        # Escape single quotes
                        escaped = str(val).replace("'", "''")
                        values.append(f"'{escaped}'")

                values_str = ', '.join(values)
                statements.append(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});")

            if i + batch_size < len(data['rows']):
                statements.append("")  # Blank line between batches

        # Commit
        statements.append("")
        statements.append("COMMIT;")

        return '\n'.join(statements).encode('utf-8')

    def _export_markdown(self, data: Dict, options: Dict) -> bytes:
        """
        Export as Markdown table

        Options:
            alignment: Column alignment ('left', 'center', 'right', default: 'left')
        """
        alignment = options.get('alignment', 'left')
        lines = []

        # Header
        lines.append('| ' + ' | '.join(data['columns']) + ' |')

        # Separator with alignment
        separators = []
        for col in data['columns']:
            if alignment == 'center':
                separators.append(':---:')
            elif alignment == 'right':
                separators.append('---:')
            else:
                separators.append('---')

        lines.append('| ' + ' | '.join(separators) + ' |')

        # Rows
        for row in data['rows']:
            row_values = []
            for val in row:
                if val is None:
                    row_values.append('')
                else:
                    # Escape pipe characters
                    row_values.append(str(val).replace('|', '\\|'))

            lines.append('| ' + ' | '.join(row_values) + ' |')

        return '\n'.join(lines).encode('utf-8')

    def _export_html(self, data: Dict, options: Dict) -> bytes:
        """
        Export as HTML table

        Options:
            style: 'basic', 'styled' (default: 'styled')
            title: Table title (optional)
        """
        style_type = options.get('style', 'styled')
        title = options.get('title', 'Query Results')

        html_parts = []

        # HTML header
        html_parts.append('<!DOCTYPE html>')
        html_parts.append('<html>')
        html_parts.append('<head>')
        html_parts.append(f'    <title>{title}</title>')
        html_parts.append('    <meta charset="UTF-8">')

        if style_type == 'styled':
            html_parts.append('    <style>')
            html_parts.append('        body { font-family: Arial, sans-serif; margin: 20px; }')
            html_parts.append('        h1 { color: #333; }')
            html_parts.append('        table { border-collapse: collapse; width: 100%; margin-top: 20px; }')
            html_parts.append('        th { background-color: #205AA7; color: white; padding: 12px; text-align: left; }')
            html_parts.append('        td { border: 1px solid #ddd; padding: 8px; }')
            html_parts.append('        tr:nth-child(even) { background-color: #f2f2f2; }')
            html_parts.append('        tr:hover { background-color: #ddd; }')
            html_parts.append('    </style>')

        html_parts.append('</head>')
        html_parts.append('<body>')
        html_parts.append(f'    <h1>{title}</h1>')
        html_parts.append(f'    <p>Rows: {len(data["rows"])}</p>')
        html_parts.append('    <table>')

        # Header
        html_parts.append('        <thead>')
        html_parts.append('            <tr>')
        for col in data['columns']:
            html_parts.append(f'                <th>{col}</th>')
        html_parts.append('            </tr>')
        html_parts.append('        </thead>')

        # Body
        html_parts.append('        <tbody>')
        for row in data['rows']:
            html_parts.append('            <tr>')
            for val in row:
                display_val = '' if val is None else str(val)
                # Escape HTML
                display_val = display_val.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_parts.append(f'                <td>{display_val}</td>')
            html_parts.append('            </tr>')
        html_parts.append('        </tbody>')

        html_parts.append('    </table>')
        html_parts.append('</body>')
        html_parts.append('</html>')

        return '\n'.join(html_parts).encode('utf-8')

    def get_filename(self, format: str, base_name: str = 'export') -> str:
        """
        Get suggested filename for export

        Args:
            format: Export format
            base_name: Base filename (default: 'export')

        Returns:
            Filename with extension
        """
        extensions = {
            'csv': 'csv',
            'json': 'json',
            'xlsx': 'xlsx',
            'sql': 'sql',
            'markdown': 'md',
            'html': 'html'
        }

        ext = extensions.get(format, 'txt')
        return f'{base_name}.{ext}'

    def get_mimetype(self, format: str) -> str:
        """
        Get MIME type for format

        Args:
            format: Export format

        Returns:
            MIME type string
        """
        mimetypes = {
            'csv': 'text/csv',
            'json': 'application/json',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'sql': 'application/sql',
            'markdown': 'text/markdown',
            'html': 'text/html'
        }

        return mimetypes.get(format, 'application/octet-stream')
