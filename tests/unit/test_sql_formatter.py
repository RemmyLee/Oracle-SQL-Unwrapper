"""
Unit tests for SQL Formatter
"""

import pytest
from backend.utils.sql_formatter import SQLFormatter, format_sql, minify_sql, validate_sql


class TestSQLFormatter:
    """Test cases for SQLFormatter"""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance"""
        return SQLFormatter()

    def test_capitalize_keywords(self, formatter):
        """Test keyword capitalization"""
        sql = "select * from users where id = 1"
        formatted = formatter.format(sql)

        assert 'SELECT' in formatted
        assert 'FROM' in formatted
        assert 'WHERE' in formatted

    def test_add_line_breaks(self, formatter):
        """Test line break insertion"""
        sql = "SELECT * FROM users WHERE id = 1 ORDER BY name"
        formatted = formatter.format(sql)

        lines = formatted.split('\n')
        assert len(lines) > 1
        assert any('SELECT' in line for line in lines)
        assert any('FROM' in line for line in lines)

    def test_preserve_strings(self, formatter):
        """Test string literal preservation"""
        sql = "SELECT 'select from where' FROM users"
        formatted = formatter.format(sql)

        assert "'select from where'" in formatted

    def test_preserve_comments(self, formatter):
        """Test comment preservation"""
        sql = "SELECT * FROM users -- This is a comment\nWHERE id = 1"
        formatted = formatter.format(sql)

        assert '-- This is a comment' in formatted

    def test_multiline_comments(self, formatter):
        """Test multi-line comment preservation"""
        sql = "SELECT * /* This is a\nmulti-line comment */ FROM users"
        formatted = formatter.format(sql)

        assert '/* This is a\nmulti-line comment */' in formatted

    def test_indentation_begin_end(self, formatter):
        """Test indentation for BEGIN/END blocks"""
        sql = "BEGIN SELECT * FROM users; END;"
        formatted = formatter.format(sql)

        lines = formatted.split('\n')
        # Content between BEGIN and END should be indented
        assert len(lines) >= 3

    def test_minify(self, formatter):
        """Test SQL minification"""
        sql = """
        SELECT
            column1,
            column2
        FROM
            table_name
        WHERE
            condition = 'value'
        """
        minified = formatter.minify(sql)

        # Should remove extra whitespace
        assert '\n' not in minified
        assert '  ' not in minified

    def test_validate_balanced_parentheses(self, formatter):
        """Test validation of balanced parentheses"""
        sql = "SELECT * FROM users WHERE id IN (1, 2, 3)"
        result = formatter.validate_syntax(sql)

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_unbalanced_parentheses(self, formatter):
        """Test validation catches unbalanced parentheses"""
        sql = "SELECT * FROM users WHERE id IN (1, 2, 3"
        result = formatter.validate_syntax(sql)

        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert 'parentheses' in result['errors'][0].lower()

    def test_validate_unbalanced_quotes(self, formatter):
        """Test validation catches unbalanced quotes"""
        sql = "SELECT * FROM users WHERE name = 'John"
        result = formatter.validate_syntax(sql)

        assert result['valid'] is False
        assert 'quotes' in result['errors'][0].lower()

    def test_validate_select_star_warning(self, formatter):
        """Test validation warns about SELECT *"""
        sql = "SELECT * FROM users"
        result = formatter.validate_syntax(sql)

        assert len(result['warnings']) > 0
        assert any('SELECT *' in w for w in result['warnings'])

    def test_format_complex_query(self, formatter):
        """Test formatting complex query"""
        sql = """
        select u.id, u.name, o.total from users u
        inner join orders o on u.id = o.user_id
        where u.status = 'active' and o.total > 100
        order by o.total desc
        """
        formatted = formatter.format(sql)

        assert 'SELECT' in formatted
        assert 'INNER JOIN' in formatted
        assert '\n' in formatted

    def test_format_plsql_block(self, formatter):
        """Test formatting PL/SQL block"""
        sql = """
        begin
        select count(*) into v_count from users;
        if v_count > 0 then
        dbms_output.put_line('Users found');
        end if;
        end;
        """
        formatted = formatter.format(sql)

        assert 'BEGIN' in formatted
        assert 'END' in formatted
        assert 'IF' in formatted

    def test_convenience_functions(self):
        """Test convenience wrapper functions"""
        sql = "select * from users"

        # Test format_sql
        formatted = format_sql(sql)
        assert 'SELECT' in formatted

        # Test minify_sql
        minified = minify_sql(sql)
        assert '\n' not in minified

        # Test validate_sql
        result = validate_sql(sql)
        assert 'valid' in result
        assert 'errors' in result

    def test_custom_indent_size(self):
        """Test custom indentation size"""
        formatter = SQLFormatter(indent_size=4)
        sql = "BEGIN SELECT * FROM users; END;"
        formatted = formatter.format(sql)

        # Check that indentation is applied
        lines = formatted.split('\n')
        assert len(lines) >= 3

    def test_format_options(self, formatter):
        """Test format with custom options"""
        sql = "select * from users"

        # Test with capitalize_keywords=False
        formatted = formatter.format(sql, {'capitalize_keywords': False})
        assert 'select' in formatted.lower()

    def test_escaped_quotes(self, formatter):
        """Test handling of escaped quotes in Oracle style"""
        sql = "SELECT 'It''s Oracle' FROM dual"
        formatted = formatter.format(sql)

        assert "It''s Oracle" in formatted

    def test_case_when_indentation(self, formatter):
        """Test CASE WHEN statement indentation"""
        sql = """
        SELECT
            CASE
                WHEN status = 'A' THEN 'Active'
                WHEN status = 'I' THEN 'Inactive'
                ELSE 'Unknown'
            END AS status_desc
        FROM users
        """
        formatted = formatter.format(sql)

        assert 'CASE' in formatted
        assert 'WHEN' in formatted
        assert 'ELSE' in formatted
        assert 'END' in formatted


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
