"""
Integration tests for Oracle database connectivity

These tests require a real Oracle database to be available.
Set the following environment variables to run these tests:

    TEST_ORACLE_HOST=localhost
    TEST_ORACLE_PORT=1521
    TEST_ORACLE_SERVICE=ORCL
    TEST_ORACLE_USER=testuser
    TEST_ORACLE_PASSWORD=testpass

Run with: pytest tests/integration/ -v
Skip with: pytest tests/unit/ -v (runs only unit tests)
"""

import pytest
import os
from backend.services.oracle_connector import SimpleOracleConnector
from backend.models.connection import OracleConnection
from backend.extensions import db


# Skip all integration tests if Oracle environment is not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get('TEST_ORACLE_HOST'),
    reason="Oracle database not configured (set TEST_ORACLE_HOST, etc.)"
)


@pytest.fixture(scope='module')
def oracle_connection(app):
    """Create a test Oracle connection"""
    with app.app_context():
        connection = OracleConnection(
            user_id=1,
            name='Integration Test DB',
            host=os.environ.get('TEST_ORACLE_HOST', 'localhost'),
            port=int(os.environ.get('TEST_ORACLE_PORT', 1521)),
            service_name=os.environ.get('TEST_ORACLE_SERVICE', 'ORCL'),
            username=os.environ.get('TEST_ORACLE_USER', 'testuser'),
            connection_type='service_name'
        )

        connection.set_password(os.environ.get('TEST_ORACLE_PASSWORD', 'testpass'))

        db.session.add(connection)
        db.session.commit()

        yield connection

        # Cleanup
        db.session.delete(connection)
        db.session.commit()


class TestOracleConnectionIntegration:
    """Integration tests for Oracle connections"""

    def test_connection_test(self, oracle_connection):
        """Test connecting to real Oracle database"""
        connector = SimpleOracleConnector(oracle_connection.id)

        try:
            result = connector.test_connection()

            assert result['success'] is True
            assert 'oracle_version' in result
            assert len(result['oracle_version']) > 0

        finally:
            connector.disconnect()

    def test_simple_query(self, oracle_connection):
        """Test executing a simple query"""
        with SimpleOracleConnector(oracle_connection.id) as connector:
            result = connector.execute_query("SELECT 1 AS num, 'test' AS str FROM DUAL")

            assert result['success'] is True
            assert result['columns'] == ['NUM', 'STR']
            assert len(result['rows']) == 1
            assert result['rows'][0] == [1, 'test']

    def test_get_schemas(self, oracle_connection):
        """Test retrieving schemas"""
        with SimpleOracleConnector(oracle_connection.id) as connector:
            schemas = connector.get_schemas()

            assert isinstance(schemas, list)
            assert len(schemas) > 0
            # Should at least have the connected user's schema

    def test_wrapped_code_detection(self, oracle_connection):
        """Test detecting wrapped vs normal code"""
        connector = SimpleOracleConnector(oracle_connection.id)

        wrapped = "a7 100\nYWJjZGVmZ2hp..."
        normal = "CREATE OR REPLACE PACKAGE pkg AS\nEND;"

        assert connector.is_wrapped(wrapped) is True
        assert connector.is_wrapped(normal) is False


class TestQueryExecutionIntegration:
    """Integration tests for query execution"""

    def test_parameterized_query(self, oracle_connection):
        """Test query with bind parameters"""
        with SimpleOracleConnector(oracle_connection.id) as connector:
            result = connector.execute_query(
                "SELECT :val AS result FROM DUAL",
                params={'val': 42}
            )

            assert result['success'] is True
            assert result['rows'][0][0] == 42

    def test_max_rows_limit(self, oracle_connection):
        """Test max rows limiting"""
        with SimpleOracleConnector(oracle_connection.id) as connector:
            # Query that would return many rows
            result = connector.execute_query(
                "SELECT LEVEL AS num FROM DUAL CONNECT BY LEVEL <= 100",
                max_rows=10
            )

            assert result['success'] is True
            assert len(result['rows']) == 10
            assert result['has_more'] is True


@pytest.mark.skipif(True, reason="Requires wrapped PL/SQL object in test database")
class TestUnwrapFromDatabase:
    """Integration tests for unwrapping from database"""

    def test_unwrap_wrapped_package(self, oracle_connection):
        """
        Test unwrapping a wrapped package from database

        Note: This requires a wrapped PL/SQL object to exist in your test database
        Create one with: WRAP INAME=package.sql ONAME=package.plb
        """
        with SimpleOracleConnector(oracle_connection.id) as connector:
            # Replace with actual wrapped object in your test DB
            source = connector.get_source_code(
                schema='TEST_SCHEMA',
                object_name='WRAPPED_PACKAGE',
                object_type='PACKAGE BODY'
            )

            assert len(source) > 0
            assert connector.is_wrapped(source) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
