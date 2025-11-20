"""
APEX Compatibility Service
Handles import/export of Oracle APEX dashboards and conversion to PL/SQL Workbench format
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class APEXTableMapper:
    """Maps APEX-specific table and view names to generic equivalents"""

    # APEX system views to standard Oracle views
    APEX_TO_STANDARD = {
        # APEX Application views
        'APEX_APPLICATIONS': 'USER_OBJECTS',
        'APEX_APPLICATION_PAGES': 'USER_TAB_COLUMNS',
        'APEX_APPLICATION_PAGE_ITEMS': 'USER_TAB_COLUMNS',
        'APEX_APPLICATION_PAGE_REGIONS': 'USER_TABLES',

        # APEX Workspace views
        'APEX_WORKSPACES': 'DBA_USERS',
        'APEX_WORKSPACE_SCHEMAS': 'ALL_USERS',
        'APEX_WORKSPACE_APPLICATIONS': 'USER_OBJECTS',

        # APEX User views
        'APEX_WORKSPACE_USERS': 'ALL_USERS',
        'APEX_WORKSPACE_USER_ROLES': 'DBA_ROLE_PRIVS',

        # APEX Collection views
        'APEX_COLLECTIONS': 'USER_TABLES',
        'APEX_COLLECTION_MEMBERS': 'USER_TAB_COLUMNS',

        # APEX Session State
        'APEX_APPLICATION_ITEMS': 'V$SESSION',
        'APEX_APPLICATION_TEMP_FILES': 'USER_OBJECTS',

        # APEX Authorization
        'APEX_APPL_ACL_USERS': 'DBA_USERS',
        'APEX_APPL_ACL_ROLES': 'DBA_ROLES',

        # APEX Interactive Reports
        'APEX_APPLICATION_PAGE_IR': 'USER_TABLES',
        'APEX_APPLICATION_PAGE_IR_COL': 'USER_TAB_COLUMNS',

        # APEX Charts
        'APEX_APPLICATION_PAGE_CHART': 'USER_TABLES',
        'APEX_APPLICATION_PAGE_CHART_S': 'USER_TAB_COLUMNS'
    }

    # APEX functions to standard SQL
    APEX_FUNCTIONS = {
        'APEX_UTIL.GET_SESSION_STATE': 'SYS_CONTEXT',
        'APEX_UTIL.SET_SESSION_STATE': 'NULL',
        'APEX_UTIL.GET_CURRENT_USER_ID': 'USER',
        'APEX_UTIL.GET_USERNAME': 'USER',
        'APEX_ITEM.TEXT': 'NULL',
        'APEX_ITEM.SELECT_LIST': 'NULL',
        'APEX_ITEM.DATE_POPUP': 'SYSDATE',
        'APEX_STRING.SPLIT': 'REGEXP_SUBSTR',
        'APEX_JSON.PARSE': 'JSON_TABLE',
        'APEX_WEB_SERVICE.MAKE_REST_REQUEST': 'NULL',
    }

    @classmethod
    def convert_query(cls, sql: str) -> Tuple[str, List[str]]:
        """
        Convert APEX-specific SQL to standard Oracle SQL

        Args:
            sql: Original SQL with APEX references

        Returns:
            Tuple of (converted SQL, list of warnings)
        """
        warnings = []
        converted_sql = sql

        # Replace APEX table/view references
        for apex_view, standard_view in cls.APEX_TO_STANDARD.items():
            if apex_view in converted_sql.upper():
                converted_sql = re.sub(
                    rf'\b{apex_view}\b',
                    standard_view,
                    converted_sql,
                    flags=re.IGNORECASE
                )
                warnings.append(f"Converted {apex_view} to {standard_view}")

        # Replace APEX function calls
        for apex_func, standard_func in cls.APEX_FUNCTIONS.items():
            if apex_func in converted_sql.upper():
                # Extract function parameters
                pattern = rf'{apex_func}\s*\([^)]*\)'
                matches = re.finditer(pattern, converted_sql, re.IGNORECASE)
                for match in matches:
                    if standard_func == 'NULL':
                        converted_sql = converted_sql.replace(match.group(), 'NULL')
                        warnings.append(f"Replaced {apex_func}() with NULL - manual review needed")
                    elif standard_func == 'USER':
                        converted_sql = converted_sql.replace(match.group(), 'USER')
                        warnings.append(f"Converted {apex_func}() to USER")
                    else:
                        warnings.append(f"Found {apex_func}() - manual conversion to {standard_func} may be needed")

        # Remove APEX session state binds
        apex_binds = re.findall(r':P\d+_\w+|:APP_\w+|:G_\w+', converted_sql)
        if apex_binds:
            warnings.append(f"Found APEX bind variables: {', '.join(apex_binds)} - need to map to parameters")

        # Remove APEX_IR filters
        if 'APEX_IR' in converted_sql.upper():
            warnings.append("Interactive Report filters detected - may need manual adjustment")

        return converted_sql, warnings


class APEXComponentMapper:
    """Maps APEX component types to PL/SQL Workbench component types"""

    COMPONENT_TYPE_MAP = {
        # APEX Region types to our component types
        'CLASSIC_REPORT': 'table',
        'INTERACTIVE_REPORT': 'table',
        'INTERACTIVE_GRID': 'table',
        'CHART': 'chart',
        'PIE_CHART': 'chart',
        'BAR_CHART': 'chart',
        'LINE_CHART': 'chart',
        'STATIC_CONTENT': 'text',
        'HTML': 'text',
        'PLUGIN': 'custom',
        'BREADCRUMB': 'text',
        'LIST': 'table',
        'CALENDAR': 'table',
        'TREE': 'table',
        'MAP': 'chart',
        'FORM': 'filter'
    }

    CHART_TYPE_MAP = {
        'PIE': 'pie',
        'BAR': 'bar',
        'COLUMN': 'bar',
        'LINE': 'line',
        'AREA': 'area',
        'SCATTER': 'scatter',
        'COMBO': 'line',
        'BUBBLE': 'scatter'
    }

    @classmethod
    def map_component_type(cls, apex_type: str) -> str:
        """Map APEX region type to our component type"""
        return cls.COMPONENT_TYPE_MAP.get(apex_type.upper(), 'text')

    @classmethod
    def map_chart_type(cls, apex_chart_type: str) -> str:
        """Map APEX chart type to our chart type"""
        return cls.CHART_TYPE_MAP.get(apex_chart_type.upper(), 'line')


class APEXDashboardImporter:
    """Import APEX dashboard definitions"""

    def __init__(self):
        self.table_mapper = APEXTableMapper()
        self.component_mapper = APEXComponentMapper()

    def import_apex_page(self, apex_page_export: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import an APEX page export and convert to our dashboard format

        Args:
            apex_page_export: APEX page export JSON

        Returns:
            Dashboard dictionary ready for creation
        """
        dashboard = {
            'title': apex_page_export.get('page_name', 'Imported APEX Page'),
            'description': f"Imported from APEX Page {apex_page_export.get('page_id', '')}",
            'category': apex_page_export.get('page_group', 'apex_import'),
            'tags': ['apex', 'imported'],
            'layout_config': self._convert_layout(apex_page_export),
            'components': [],
            'data_sources': [],
            'conversion_warnings': []
        }

        # Process regions (APEX regions become our components)
        regions = apex_page_export.get('regions', [])
        for idx, region in enumerate(regions):
            component, data_source, warnings = self._convert_region(region, idx)
            if component:
                dashboard['components'].append(component)
            if data_source:
                dashboard['data_sources'].append(data_source)
            dashboard['conversion_warnings'].extend(warnings)

        # Process page items (APEX items become filters)
        items = apex_page_export.get('items', [])
        for idx, item in enumerate(items):
            filter_component = self._convert_item_to_filter(item, idx + len(regions))
            if filter_component:
                dashboard['components'].append(filter_component)

        return dashboard

    def _convert_layout(self, apex_page: Dict[str, Any]) -> Dict[str, Any]:
        """Convert APEX page layout to our grid layout"""
        # APEX uses position-based layout, we use grid
        return {
            'columns': 12,
            'row_height': 80,
            'is_draggable': True,
            'is_resizable': True,
            'responsive': True,
            'breakpoints': {
                'lg': 1200,
                'md': 996,
                'sm': 768,
                'xs': 480
            }
        }

    def _convert_region(self, region: Dict[str, Any], index: int) -> Tuple[Optional[Dict], Optional[Dict], List[str]]:
        """Convert APEX region to component and data source"""
        warnings = []

        region_type = region.get('type', 'STATIC_CONTENT')
        component_type = self.component_mapper.map_component_type(region_type)

        # Create component
        component = {
            'component_type': component_type,
            'title': region.get('title', f'Component {index + 1}'),
            'description': region.get('static_id', ''),
            'grid_position': self._calculate_grid_position(region, index),
            'config': {},
            'order_index': index
        }

        # Create data source if region has SQL
        data_source = None
        if region.get('source_type') == 'SQL' and region.get('source'):
            sql = region['source']
            converted_sql, sql_warnings = self.table_mapper.convert_query(sql)
            warnings.extend(sql_warnings)

            data_source = {
                'name': f"{region.get('title', 'Data')} Source",
                'source_type': 'sql_query',
                'query': converted_sql,
                'config': {
                    'original_apex_sql': sql,
                    'conversion_warnings': sql_warnings
                },
                'cache_ttl': 300
            }

        # Configure component based on type
        if component_type == 'chart':
            component['config'] = self._convert_chart_config(region)
        elif component_type == 'table':
            component['config'] = self._convert_table_config(region)
        elif component_type == 'text':
            component['config'] = {
                'content': region.get('source', ''),
                'format': 'html'
            }

        return component, data_source, warnings

    def _calculate_grid_position(self, region: Dict[str, Any], index: int) -> Dict[str, int]:
        """Calculate grid position from APEX region position"""
        # APEX uses display_sequence and column position
        # We'll create a simple stacked layout
        row = index * 4  # Each component gets 4 rows by default
        col = 0

        # Try to determine width based on template
        width = 12  # Full width by default
        if region.get('template'):
            if 'SIDEBAR' in region['template'].upper():
                width = 3
            elif 'CONTENT' in region['template'].upper():
                width = 9

        return {
            'x': col,
            'y': row,
            'w': width,
            'h': 4
        }

    def _convert_chart_config(self, region: Dict[str, Any]) -> Dict[str, Any]:
        """Convert APEX chart configuration"""
        chart_type = region.get('chart_type', 'BAR')

        config = {
            'chart_type': self.component_mapper.map_chart_type(chart_type),
            'x_axis': region.get('label_column', 'category'),
            'y_axis': region.get('value_column', 'value'),
            'show_legend': region.get('show_legend', True),
            'show_grid': True,
            'colors': ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
        }

        # Add series configuration if multiple series
        if region.get('series'):
            config['series'] = region['series']

        return config

    def _convert_table_config(self, region: Dict[str, Any]) -> Dict[str, Any]:
        """Convert APEX report/grid configuration"""
        config = {
            'columns': [],
            'page_size': region.get('rows_per_page', 10),
            'enable_search': region.get('enable_search', True),
            'enable_export': True,
            'sortable': True,
            'filterable': region.get('type') == 'INTERACTIVE_REPORT'
        }

        # Extract columns from region attributes
        if region.get('columns'):
            for col in region['columns']:
                config['columns'].append({
                    'field': col.get('name', ''),
                    'header': col.get('heading', col.get('name', '')),
                    'sortable': col.get('sortable', True),
                    'format': col.get('format_mask', '')
                })

        return config

    def _convert_item_to_filter(self, item: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """Convert APEX page item to filter component"""
        item_type = item.get('type', 'TEXT')

        # Only convert items that make sense as filters
        if item_type not in ['SELECT_LIST', 'DATE_PICKER', 'TEXT', 'NUMBER', 'CHECKBOX']:
            return None

        return {
            'component_type': 'filter',
            'title': item.get('label', item.get('name', '')),
            'description': item.get('help_text', ''),
            'grid_position': {
                'x': 0,
                'y': 0,  # Filters typically at top
                'w': 3,
                'h': 1
            },
            'config': {
                'filter_type': self._map_item_type(item_type),
                'parameter_name': item.get('name', ''),
                'default_value': item.get('default_value', ''),
                'lov_query': item.get('lov_definition', '') if item_type == 'SELECT_LIST' else None
            },
            'order_index': index
        }

    def _map_item_type(self, apex_type: str) -> str:
        """Map APEX item type to filter type"""
        mapping = {
            'SELECT_LIST': 'dropdown',
            'DATE_PICKER': 'date_range',
            'TEXT': 'text_search',
            'NUMBER': 'number_range',
            'CHECKBOX': 'multi_select'
        }
        return mapping.get(apex_type, 'text_search')


class APEXDashboardExporter:
    """Export dashboards to APEX-compatible format"""

    def __init__(self):
        self.table_mapper = APEXTableMapper()

    def export_to_apex(self, dashboard: Dict[str, Any], app_id: int = 100) -> Dict[str, Any]:
        """
        Export dashboard to APEX page definition format

        Args:
            dashboard: Dashboard dictionary
            app_id: APEX application ID

        Returns:
            APEX-compatible page export
        """
        page_id = dashboard.get('id', 1000)

        apex_export = {
            'application_id': app_id,
            'page_id': page_id,
            'page_name': dashboard.get('title', 'Exported Dashboard'),
            'page_title': dashboard.get('title', 'Exported Dashboard'),
            'page_group': dashboard.get('category', 'Dashboards'),
            'page_mode': 'NORMAL',
            'page_template': 'Theme Standard',
            'regions': [],
            'items': []
        }

        # Convert components to APEX regions
        for component in dashboard.get('components', []):
            region = self._convert_component_to_region(component, dashboard)
            if region:
                apex_export['regions'].append(region)

        return apex_export

    def _convert_component_to_region(self, component: Dict[str, Any], dashboard: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert our component to APEX region"""
        component_type = component.get('component_type')

        # Map our component type back to APEX
        apex_type = {
            'chart': 'CHART',
            'table': 'INTERACTIVE_REPORT',
            'metric': 'STATIC_CONTENT',
            'text': 'STATIC_CONTENT',
            'filter': 'FORM'
        }.get(component_type, 'STATIC_CONTENT')

        region = {
            'name': component.get('title', 'Region'),
            'type': apex_type,
            'template': 'Standard',
            'display_sequence': component.get('order_index', 0) * 10,
            'static_id': component.get('description', ''),
            'source_type': 'SQL' if self._get_data_source(component, dashboard) else 'STATIC',
            'source': ''
        }

        # Get data source SQL
        data_source = self._get_data_source(component, dashboard)
        if data_source:
            region['source'] = data_source.get('query', '')

        # Add component-specific configuration
        if component_type == 'chart':
            region.update(self._convert_chart_to_apex(component))
        elif component_type == 'table':
            region.update(self._convert_table_to_apex(component))

        return region

    def _get_data_source(self, component: Dict[str, Any], dashboard: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find data source for component"""
        config = component.get('config', {})
        data_source_id = config.get('data_source_id')

        if data_source_id:
            for ds in dashboard.get('data_sources', []):
                if ds.get('id') == data_source_id:
                    return ds
        return None

    def _convert_chart_to_apex(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Convert chart component to APEX chart region"""
        config = component.get('config', {})

        return {
            'type': 'CHART',
            'chart_type': config.get('chart_type', 'bar').upper(),
            'label_column': config.get('x_axis', 'LABEL'),
            'value_column': config.get('y_axis', 'VALUE'),
            'show_legend': config.get('show_legend', True)
        }

    def _convert_table_to_apex(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Convert table component to APEX report region"""
        config = component.get('config', {})

        return {
            'type': 'INTERACTIVE_REPORT',
            'rows_per_page': config.get('page_size', 10),
            'enable_search': config.get('enable_search', True)
        }


# Utility functions for APEX compatibility

def convert_apex_sql_to_standard(sql: str) -> Tuple[str, List[str]]:
    """
    Convert APEX SQL to standard Oracle SQL

    Args:
        sql: APEX SQL query

    Returns:
        Tuple of (converted SQL, warnings)
    """
    return APEXTableMapper.convert_query(sql)


def import_apex_dashboard(apex_export: Dict[str, Any]) -> Dict[str, Any]:
    """
    Import APEX dashboard export

    Args:
        apex_export: APEX page export JSON

    Returns:
        Dashboard ready for creation
    """
    importer = APEXDashboardImporter()
    return importer.import_apex_page(apex_export)


def export_to_apex_format(dashboard: Dict[str, Any], app_id: int = 100) -> Dict[str, Any]:
    """
    Export dashboard to APEX format

    Args:
        dashboard: Dashboard dictionary
        app_id: APEX application ID

    Returns:
        APEX-compatible export
    """
    exporter = APEXDashboardExporter()
    return exporter.export_to_apex(dashboard, app_id)
