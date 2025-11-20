"""
Input validation utilities
Provides comprehensive validation for user inputs
"""

import re
from typing import Tuple, Any


class UnwrapValidator:
    """Validator for unwrap operations"""

    MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_LINE_LENGTH = 32768

    @staticmethod
    def validate_wrapped_input(content: str) -> Tuple[bool, str]:
        """
        Comprehensive input validation for wrapped SQL

        Args:
            content: Input content to validate

        Returns:
            (is_valid, error_message)
        """
        if not content or not content.strip():
            return False, "Input cannot be empty"

        if len(content) > UnwrapValidator.MAX_INPUT_SIZE:
            return False, f"Input exceeds maximum size of {UnwrapValidator.MAX_INPUT_SIZE / (1024*1024)}MB"

        # Check for wrapped format
        if not re.match(r'^[0-9a-f]+\s+[0-9a-f]+', content, re.MULTILINE):
            return False, "Invalid wrapped format - missing format marker"

        # Check for dangerous patterns
        dangerous_patterns = [
            (r'<script', 'Potentially malicious script tag'),
            (r'javascript:', 'JavaScript protocol'),
            (r'onclick\s*=', 'Inline event handler'),
            (r'onerror\s*=', 'Error event handler'),
            (r'eval\s*\(', 'Eval function call'),
        ]

        for pattern, description in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Potentially malicious content detected: {description}"

        return True, "Valid"


class QueryValidator:
    """Validator for SQL queries"""

    MAX_QUERY_LENGTH = 1024 * 1024  # 1MB
    DANGEROUS_KEYWORDS = [
        'DROP DATABASE',
        'TRUNCATE DATABASE',
        'DROP TABLESPACE',
    ]

    @staticmethod
    def validate_query(sql: str, allow_ddl: bool = False) -> Tuple[bool, str]:
        """
        Validate SQL query

        Args:
            sql: SQL query to validate
            allow_ddl: Whether to allow DDL statements

        Returns:
            (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Query cannot be empty"

        if len(sql) > QueryValidator.MAX_QUERY_LENGTH:
            return False, f"Query exceeds maximum length of {QueryValidator.MAX_QUERY_LENGTH / 1024}KB"

        # Check for dangerous operations
        for keyword in QueryValidator.DANGEROUS_KEYWORDS:
            if keyword in sql.upper():
                return False, f"Dangerous operation detected: {keyword}"

        # Check DDL if not allowed
        if not allow_ddl:
            ddl_keywords = ['CREATE', 'ALTER', 'DROP', 'TRUNCATE']
            first_word = sql.strip().split()[0].upper()
            if first_word in ddl_keywords:
                return False, f"DDL operations not allowed: {first_word}"

        return True, "Valid"


class ConnectionValidator:
    """Validator for database connections"""

    @staticmethod
    def validate_connection_params(host: str, port: int, username: str) -> Tuple[bool, str]:
        """
        Validate database connection parameters

        Args:
            host: Database host
            port: Database port
            username: Database username

        Returns:
            (is_valid, error_message)
        """
        # Validate host
        if not host or not host.strip():
            return False, "Host cannot be empty"

        # Validate port
        if not isinstance(port, int) or port < 1 or port > 65535:
            return False, "Port must be between 1 and 65535"

        # Validate username
        if not username or not username.strip():
            return False, "Username cannot be empty"

        # Check for SQL injection in host
        if re.search(r'[;\'"\\]', host):
            return False, "Invalid characters in host"

        # Check for SQL injection in username
        if re.search(r'[;\'"\\]', username):
            return False, "Invalid characters in username"

        return True, "Valid"


def sanitize_html(text: str) -> str:
    """
    Sanitize HTML to prevent XSS

    Args:
        text: Input text

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Replace dangerous HTML characters
    replacements = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def validate_email(email: str) -> bool:
    """
    Validate email address format

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
