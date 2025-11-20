"""
Unit tests for SimpleOracleConnector

Note: These tests mock cx_Oracle since we don't have a real Oracle database in test environment
For integration tests with a real database, see tests/integration/
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.services.oracle_connector import SimpleOracleConnector, OracleConnectionError


class TestSimpleOracleConnector:
    """Test cases for SimpleOracleConnector"""

    def test_init_without_cx_oracle(self):
        """Test initialization fails gracefully without cx_Oracle"""
        with patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', False):
            with pytest.raises(ImportError) as exc_info:
                SimpleOracleConnector(connection_id=1)

            assert "cx_Oracle is not installed" in str(exc_info.value)

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    def test_init_success(self):
        """Test successful initialization"""
        connector = SimpleOracleConnector(connection_id=1)

        assert connector.connection_id == 1
        assert connector.connection is None
        assert connector.config is None

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    @patch('backend.services.oracle_connector.cx_Oracle')
    @patch('backend.models.connection.OracleConnection')
    def test_connect_success(self, mock_connection_model, mock_cx_oracle):
        """Test successful database connection"""
        # Mock the connection config
        mock_config = Mock()
        mock_config.connection_id = 1
        mock_config.is_active = True
        mock_config.connection_type = 'service_name'
        mock_config.host = 'localhost'
        mock_config.port = 1521
        mock_config.service_name = 'ORCL'
        mock_config.username = 'testuser'
        mock_config.name = 'Test DB'
        mock_config.get_password = Mock(return_value='testpass')

        mock_connection_model.query.get.return_value = mock_config

        # Mock cx_Oracle
        mock_cx_oracle.makedsn.return_value = 'localhost:1521/ORCL'
        mock_cx_oracle.connect.return_value = Mock()

        # Test connect
        connector = SimpleOracleConnector(connection_id=1)
        connection = connector.connect()

        assert connection is not None
        assert connector.is_connected()
        mock_cx_oracle.connect.assert_called_once()

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    @patch('backend.models.connection.OracleConnection')
    def test_connect_connection_not_found(self, mock_connection_model):
        """Test connection fails when config not found"""
        mock_connection_model.query.get.return_value = None

        connector = SimpleOracleConnector(connection_id=999)

        with pytest.raises(OracleConnectionError) as exc_info:
            connector.connect()

        assert "not found" in str(exc_info.value)

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    @patch('backend.models.connection.OracleConnection')
    def test_connect_inactive_connection(self, mock_connection_model):
        """Test connection fails when config is inactive"""
        mock_config = Mock()
        mock_config.is_active = False

        mock_connection_model.query.get.return_value = mock_config

        connector = SimpleOracleConnector(connection_id=1)

        with pytest.raises(OracleConnectionError) as exc_info:
            connector.connect()

        assert "inactive" in str(exc_info.value)

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    def test_disconnect(self):
        """Test disconnection"""
        connector = SimpleOracleConnector(connection_id=1)

        # Mock an active connection
        mock_conn = Mock()
        connector.connection = mock_conn
        connector.config = Mock(name='Test DB')

        # Disconnect
        connector.disconnect()

        assert connector.connection is None
        mock_conn.close.assert_called_once()

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    def test_is_connected(self):
        """Test connection status check"""
        connector = SimpleOracleConnector(connection_id=1)

        assert not connector.is_connected()

        connector.connection = Mock()
        assert connector.is_connected()

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    @patch('backend.services.oracle_connector.cx_Oracle')
    @patch('backend.models.connection.OracleConnection')
    @patch('backend.extensions.db')
    def test_test_connection_success(self, mock_db, mock_connection_model, mock_cx_oracle):
        """Test connection testing"""
        # Setup mocks
        mock_config = Mock()
        mock_config.connection_id = 1
        mock_config.is_active = True
        mock_config.connection_type = 'service_name'
        mock_config.host = 'localhost'
        mock_config.port = 1521
        mock_config.service_name = 'ORCL'
        mock_config.username = 'testuser'
        mock_config.name = 'Test DB'
        mock_config.get_password = Mock(return_value='testpass')

        mock_connection_model.query.get.return_value = mock_config

        # Mock connection and cursor
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            (1,),  # Test query result
            ("Oracle Database 19c Enterprise Edition",),  # Version query
            None  # Edition query (no result)
        ]

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cx_oracle.makedsn.return_value = 'localhost:1521/ORCL'
        mock_cx_oracle.connect.return_value = mock_conn

        # Test
        connector = SimpleOracleConnector(connection_id=1)
        result = connector.test_connection()

        assert result['success'] is True
        assert 'oracle_version' in result
        assert 'Connection successful' in result['message']

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    def test_context_manager(self):
        """Test context manager usage"""
        connector = SimpleOracleConnector(connection_id=1)

        # Mock connect and disconnect
        connector.connect = Mock(return_value=Mock())
        connector.disconnect = Mock()

        # Use context manager
        with connector as conn:
            pass

        connector.connect.assert_called_once()
        connector.disconnect.assert_called_once()

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    def test_repr(self):
        """Test string representation"""
        connector = SimpleOracleConnector(connection_id=1)

        repr_str = repr(connector)

        assert 'SimpleOracleConnector' in repr_str
        assert 'connection_id=1' in repr_str
        assert 'disconnected' in repr_str

        # When connected
        connector.connection = Mock()
        repr_str = repr(connector)
        assert 'connected' in repr_str


class TestOracleConnectorQueryExecution:
    """Test query execution functionality"""

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    @patch('backend.services.oracle_connector.cx_Oracle')
    @patch('backend.models.connection.OracleConnection')
    def test_execute_query_success(self, mock_connection_model, mock_cx_oracle):
        """Test successful query execution"""
        # Setup mocks
        mock_config = Mock()
        mock_config.connection_id = 1
        mock_config.is_active = True
        mock_config.connection_type = 'service_name'
        mock_config.host = 'localhost'
        mock_config.port = 1521
        mock_config.service_name = 'ORCL'
        mock_config.username = 'testuser'
        mock_config.name = 'Test DB'
        mock_config.get_password = Mock(return_value='testpass')

        mock_connection_model.query.get.return_value = mock_config

        # Mock cursor with results
        mock_cursor = Mock()
        mock_cursor.description = [('ID',), ('NAME',)]
        mock_cursor.fetchmany.return_value = [[1, 'John'], [2, 'Jane']]

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cx_oracle.makedsn.return_value = 'localhost:1521/ORCL'
        mock_cx_oracle.connect.return_value = mock_conn

        # Test
        connector = SimpleOracleConnector(connection_id=1)
        result = connector.execute_query("SELECT * FROM employees")

        assert result['success'] is True
        assert result['columns'] == ['ID', 'NAME']
        assert len(result['rows']) == 2
        assert result['row_count'] == 2
        assert 'execution_time_ms' in result

    @patch('backend.services.oracle_connector.CX_ORACLE_AVAILABLE', True)
    def test_is_wrapped(self):
        """Test wrapped source code detection"""
        connector = SimpleOracleConnector(connection_id=1)

        # Wrapped code (has hex marker)
        wrapped = "a7 100\nYWJjZGVmZ2hp..."
        assert connector.is_wrapped(wrapped) is True

        # Normal code
        normal = "CREATE OR REPLACE PACKAGE pkg AS\nEND;"
        assert connector.is_wrapped(normal) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
