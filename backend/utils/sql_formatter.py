"""
SQL Formatting Utilities
Provides SQL code formatting and beautification for Oracle SQL/PL-SQL
"""

import re
from typing import Optional


class SQLFormatter:
    """
    SQL code formatter with support for Oracle SQL and PL/SQL

    Features:
    - Keyword capitalization
    - Proper indentation
    - Line breaks for major clauses
    - Comment preservation
    - Oracle-specific syntax support
    """

    # SQL keywords that should be capitalized
    KEYWORDS = {
        # DDL
        'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME',
        'TABLE', 'INDEX', 'VIEW', 'SEQUENCE', 'SYNONYM',
        'TRIGGER', 'PROCEDURE', 'FUNCTION', 'PACKAGE', 'TYPE',
        'CONSTRAINT', 'PRIMARY', 'FOREIGN', 'KEY', 'UNIQUE',
        'CHECK', 'DEFAULT', 'NOT', 'NULL', 'REFERENCES',

        # DML
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE',
        'FROM', 'WHERE', 'GROUP', 'HAVING', 'ORDER', 'BY',
        'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER', 'CROSS',
        'ON', 'USING', 'INTO', 'VALUES', 'SET',

        # TCL
        'COMMIT', 'ROLLBACK', 'SAVEPOINT',

        # DCL
        'GRANT', 'REVOKE',

        # Operators and Functions
        'AND', 'OR', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS',
        'AS', 'DISTINCT', 'ALL', 'ANY', 'SOME',
        'UNION', 'INTERSECT', 'MINUS',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END',

        # PL/SQL Keywords
        'BEGIN', 'END', 'DECLARE', 'EXCEPTION',
        'IF', 'ELSIF', 'ELSE', 'LOOP', 'WHILE', 'FOR', 'EXIT',
        'RETURN', 'RETURNING', 'CURSOR', 'OPEN', 'FETCH', 'CLOSE',
        'RAISE', 'PRAGMA', 'TYPE', 'RECORD', 'VARRAY',
        'CONSTANT', 'VARIABLE',

        # Oracle-Specific
        'REPLACE', 'FORCE', 'COMPILE', 'BODY',
        'WRAPPED', 'AUTHID', 'CURRENT_USER', 'DEFINER',
        'DETERMINISTIC', 'PARALLEL_ENABLE', 'PIPELINED',
        'AGGREGATE', 'SQLDATA', 'ACCESSIBLE', 'BY',
    }

    # Major clauses that should start on new lines
    MAJOR_CLAUSES = {
        'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING',
        'ORDER BY', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN',
        'INNER JOIN', 'OUTER JOIN', 'CROSS JOIN',
        'UNION', 'UNION ALL', 'INTERSECT', 'MINUS',
        'INSERT INTO', 'UPDATE', 'DELETE FROM', 'MERGE INTO',
        'CREATE', 'ALTER', 'DROP',
        'BEGIN', 'END', 'EXCEPTION', 'DECLARE',
    }

    def __init__(self, indent_size: int = 2):
        """
        Initialize formatter

        Args:
            indent_size: Number of spaces per indentation level
        """
        self.indent_size = indent_size

    def format(self, sql: str, options: Optional[dict] = None) -> str:
        """
        Format SQL code

        Args:
            sql: SQL code to format
            options: Formatting options
                - capitalize_keywords: bool (default: True)
                - indent_size: int (default: 2)
                - preserve_newlines: bool (default: True)
                - max_line_length: int (default: 120)

        Returns:
            Formatted SQL code
        """
        if not sql or not sql.strip():
            return sql

        # Get options
        options = options or {}
        capitalize_keywords = options.get('capitalize_keywords', True)
        preserve_newlines = options.get('preserve_newlines', True)

        # Store and remove comments/strings temporarily
        sql, comments = self._extract_comments(sql)
        sql, strings = self._extract_strings(sql)

        # Capitalize keywords
        if capitalize_keywords:
            sql = self._capitalize_keywords(sql)

        # Add line breaks for major clauses
        sql = self._add_line_breaks(sql)

        # Add indentation
        sql = self._add_indentation(sql)

        # Restore strings and comments
        sql = self._restore_strings(sql, strings)
        sql = self._restore_comments(sql, comments)

        # Clean up extra whitespace
        sql = self._clean_whitespace(sql, preserve_newlines)

        return sql

    def minify(self, sql: str) -> str:
        """
        Minify SQL code (remove unnecessary whitespace)

        Args:
            sql: SQL code to minify

        Returns:
            Minified SQL code
        """
        # Store and remove comments/strings
        sql, comments = self._extract_comments(sql)
        sql, strings = self._extract_strings(sql)

        # Remove extra whitespace
        sql = re.sub(r'\s+', ' ', sql)
        sql = sql.strip()

        # Restore strings (but not comments for minification)
        sql = self._restore_strings(sql, strings)

        return sql

    def _extract_comments(self, sql: str) -> tuple:
        """Extract comments and replace with placeholders"""
        comments = []

        # Single-line comments (-- comment)
        def replace_single_comment(match):
            comments.append(match.group(0))
            return f'__COMMENT_{len(comments)-1}__'

        sql = re.sub(r'--[^\n]*', replace_single_comment, sql)

        # Multi-line comments (/* comment */)
        def replace_multi_comment(match):
            comments.append(match.group(0))
            return f'__COMMENT_{len(comments)-1}__'

        sql = re.sub(r'/\*.*?\*/', replace_multi_comment, sql, flags=re.DOTALL)

        return sql, comments

    def _restore_comments(self, sql: str, comments: list) -> str:
        """Restore comments from placeholders"""
        for i, comment in enumerate(comments):
            sql = sql.replace(f'__COMMENT_{i}__', comment)
        return sql

    def _extract_strings(self, sql: str) -> tuple:
        """Extract string literals and replace with placeholders"""
        strings = []

        def replace_string(match):
            strings.append(match.group(0))
            return f'__STRING_{len(strings)-1}__'

        # Single-quoted strings (Oracle uses '' for escaped quotes)
        sql = re.sub(r"'(?:''|[^'])*'", replace_string, sql)

        return sql, strings

    def _restore_strings(self, sql: str, strings: list) -> str:
        """Restore string literals from placeholders"""
        for i, string in enumerate(strings):
            sql = sql.replace(f'__STRING_{i}__', string)
        return sql

    def _capitalize_keywords(self, sql: str) -> str:
        """Capitalize SQL keywords"""
        # Create word boundary pattern for each keyword
        for keyword in self.KEYWORDS:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            sql = re.sub(pattern, keyword.upper(), sql, flags=re.IGNORECASE)

        return sql

    def _add_line_breaks(self, sql: str) -> str:
        """Add line breaks before major clauses"""
        # Sort by length (longest first) to handle multi-word clauses
        clauses = sorted(self.MAJOR_CLAUSES, key=len, reverse=True)

        for clause in clauses:
            # Add newline before clause (if not at start)
            pattern = r'(?<!^)\s*\b' + re.escape(clause) + r'\b'
            sql = re.sub(pattern, f'\n{clause}', sql, flags=re.IGNORECASE | re.MULTILINE)

        return sql

    def _add_indentation(self, sql: str) -> str:
        """Add proper indentation based on nesting level"""
        lines = sql.split('\n')
        indented_lines = []
        indent_level = 0

        # Keywords that increase indentation
        indent_increase = {'BEGIN', 'CASE', 'LOOP', 'IF', 'DECLARE', '('}
        # Keywords that decrease indentation
        indent_decrease = {'END', 'EXCEPTION', ')'}
        # Keywords that temporarily decrease for current line only
        indent_temp_decrease = {'WHEN', 'ELSIF', 'ELSE', 'EXCEPTION'}

        for line in lines:
            line = line.strip()
            if not line:
                indented_lines.append('')
                continue

            # Check for temporary decrease
            first_word = line.split()[0].upper() if line.split() else ''
            temp_decrease = first_word in indent_temp_decrease

            # Check for permanent decrease (before line)
            if first_word in indent_decrease:
                indent_level = max(0, indent_level - 1)

            # Apply indentation
            current_indent = indent_level
            if temp_decrease:
                current_indent = max(0, current_indent - 1)

            indented_line = (' ' * (current_indent * self.indent_size)) + line
            indented_lines.append(indented_line)

            # Check for increase (after line)
            if first_word in indent_increase:
                indent_level += 1

            # Handle parentheses
            indent_level += line.count('(') - line.count(')')
            indent_level = max(0, indent_level)

        return '\n'.join(indented_lines)

    def _clean_whitespace(self, sql: str, preserve_newlines: bool = True) -> str:
        """Clean up extra whitespace"""
        # Remove trailing whitespace from each line
        lines = sql.split('\n')
        lines = [line.rstrip() for line in lines]

        # Remove multiple consecutive blank lines
        cleaned_lines = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank and preserve_newlines:
                continue
            cleaned_lines.append(line)
            prev_blank = is_blank

        # Remove leading/trailing blank lines
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        return '\n'.join(cleaned_lines)

    def validate_syntax(self, sql: str) -> dict:
        """
        Basic SQL syntax validation

        Args:
            sql: SQL code to validate

        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'errors': list of error messages,
                'warnings': list of warning messages
            }
        """
        errors = []
        warnings = []

        # Check for balanced parentheses
        open_count = sql.count('(')
        close_count = sql.count(')')
        if open_count != close_count:
            errors.append(f'Unbalanced parentheses: {open_count} opening, {close_count} closing')

        # Check for balanced quotes
        # Remove escaped quotes first
        sql_check = sql.replace("''", "")
        quote_positions = [i for i, c in enumerate(sql_check) if c == "'"]
        if len(quote_positions) % 2 != 0:
            errors.append('Unbalanced single quotes')

        # Check for BEGIN without END
        begin_count = len(re.findall(r'\bBEGIN\b', sql, re.IGNORECASE))
        end_count = len(re.findall(r'\bEND\b', sql, re.IGNORECASE))
        if begin_count != end_count:
            warnings.append(f'Unmatched BEGIN/END blocks: {begin_count} BEGIN, {end_count} END')

        # Check for common issues
        if re.search(r'SELECT\s+\*\s+FROM', sql, re.IGNORECASE):
            warnings.append('Use of SELECT * is not recommended for production code')

        if re.search(r'--.*password|--.*pwd', sql, re.IGNORECASE):
            warnings.append('Potential sensitive information in comments')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


# Convenience functions
def format_sql(sql: str, **options) -> str:
    """
    Format SQL code (convenience function)

    Args:
        sql: SQL code to format
        **options: Formatting options (see SQLFormatter.format)

    Returns:
        Formatted SQL code
    """
    formatter = SQLFormatter()
    return formatter.format(sql, options)


def minify_sql(sql: str) -> str:
    """
    Minify SQL code (convenience function)

    Args:
        sql: SQL code to minify

    Returns:
        Minified SQL code
    """
    formatter = SQLFormatter()
    return formatter.minify(sql)


def validate_sql(sql: str) -> dict:
    """
    Validate SQL syntax (convenience function)

    Args:
        sql: SQL code to validate

    Returns:
        Validation results dictionary
    """
    formatter = SQLFormatter()
    return formatter.validate_syntax(sql)
