"""
Unit tests for UnwrapperService
"""

import pytest
from backend.services.unwrapper import (
    UnwrapperService,
    InvalidFormatError,
    DecompressionError
)


class TestUnwrapperService:
    """Test cases for UnwrapperService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = UnwrapperService()

    def test_validate_input_empty(self):
        """Test validation of empty input"""
        is_valid, error_msg = self.service.validate_input("")
        assert is_valid is False
        assert "empty" in error_msg.lower()

    def test_validate_input_too_large(self):
        """Test validation of oversized input"""
        large_input = "a" * (11 * 1024 * 1024)  # 11MB
        is_valid, error_msg = self.service.validate_input(large_input)
        assert is_valid is False
        assert "maximum size" in error_msg.lower()

    def test_validate_input_missing_marker(self):
        """Test validation of input without wrapped format marker"""
        invalid_input = "This is not wrapped SQL"
        is_valid, error_msg = self.service.validate_input(invalid_input)
        assert is_valid is False
        assert "format marker" in error_msg.lower()

    def test_validate_input_malicious_script(self):
        """Test validation detects malicious script tags"""
        malicious_input = "a7 100\n<script>alert('xss')</script>"
        is_valid, error_msg = self.service.validate_input(malicious_input)
        assert is_valid is False
        assert "script tag" in error_msg.lower()

    def test_validate_input_valid_format(self):
        """Test validation of properly formatted wrapped content"""
        valid_input = """a7 100
YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo="""
        is_valid, error_msg = self.service.validate_input(valid_input)
        assert is_valid is True
        assert error_msg == "Valid"

    def test_detect_format_11g(self):
        """Test format detection for Oracle 11g"""
        content = "a7 100\nbase64content"
        format_detected = self.service.detect_format(content)
        assert format_detected == "11g"

    def test_detect_format_12c(self):
        """Test format detection for Oracle 12c"""
        content = "b8 200\nbase64content"
        format_detected = self.service.detect_format(content)
        assert format_detected == "12c"

    def test_detect_format_unknown(self):
        """Test format detection for unknown/invalid format"""
        content = "invalid content"
        format_detected = self.service.detect_format(content)
        assert format_detected == "unknown"

    def test_get_statistics(self):
        """Test statistics gathering for wrapped content"""
        content = """a7 100
YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo=
another line"""
        stats = self.service.get_statistics(content)

        assert 'size_bytes' in stats
        assert 'line_count' in stats
        assert 'is_valid' in stats
        assert 'format' in stats
        assert stats['line_count'] == 3
        assert stats['is_valid'] is True

    def test_unwrap_invalid_input(self):
        """Test unwrapping with invalid input"""
        result = self.service.unwrap("invalid input")

        assert result['success'] is False
        assert 'error' in result
        assert 'Invalid format' in result['error']

    def test_unwrap_empty_input(self):
        """Test unwrapping with empty input"""
        result = self.service.unwrap("")

        assert result['success'] is False
        assert 'error' in result

    def test_unwrap_batch_empty_list(self):
        """Test batch unwrapping with empty list"""
        results = self.service.unwrap_batch([])
        assert results == []

    def test_unwrap_batch_multiple_files(self):
        """Test batch unwrapping with multiple files"""
        files = [
            {'name': 'file1.sql', 'content': 'invalid1'},
            {'name': 'file2.sql', 'content': 'invalid2'}
        ]

        results = self.service.unwrap_batch(files)

        assert len(results) == 2
        assert results[0]['filename'] == 'file1.sql'
        assert results[1]['filename'] == 'file2.sql'
        # Both should fail since content is invalid
        assert results[0]['success'] is False
        assert results[1]['success'] is False


class TestUnwrapValidator:
    """Test cases for validation utilities"""

    def test_validate_sql_injection_attempt(self):
        """Test detection of SQL injection attempts"""
        from backend.utils.validators import UnwrapValidator

        # Test with SQL injection pattern in content
        malicious = "a7 100'; DROP TABLE users; --"
        is_valid, msg = UnwrapValidator.validate_wrapped_input(malicious)
        # Should still be valid as wrapped format (SQL injection protection is for queries)
        assert is_valid is True

    def test_sanitize_html(self):
        """Test HTML sanitization"""
        from backend.utils.validators import sanitize_html

        dirty = "<script>alert('xss')</script>"
        clean = sanitize_html(dirty)

        assert '<script>' not in clean
        assert '&lt;script&gt;' in clean

    def test_validate_email_valid(self):
        """Test email validation with valid email"""
        from backend.utils.validators import validate_email

        assert validate_email('user@example.com') is True
        assert validate_email('test.user@company.co.uk') is True

    def test_validate_email_invalid(self):
        """Test email validation with invalid emails"""
        from backend.utils.validators import validate_email

        assert validate_email('invalid') is False
        assert validate_email('@example.com') is False
        assert validate_email('user@') is False
        assert validate_email('') is False


class TestFormatters:
    """Test cases for formatting utilities"""

    def test_format_bytes(self):
        """Test byte formatting"""
        from backend.utils.formatters import format_bytes

        assert 'B' in format_bytes(500)
        assert 'KB' in format_bytes(2048)
        assert 'MB' in format_bytes(5 * 1024 * 1024)

    def test_format_duration(self):
        """Test duration formatting"""
        from backend.utils.formatters import format_duration

        assert 'ms' in format_duration(500)
        assert 's' in format_duration(2500)
        assert 'm' in format_duration(125000)

    def test_truncate_text(self):
        """Test text truncation"""
        from backend.utils.formatters import truncate_text

        long_text = "This is a very long text that needs to be truncated"
        truncated = truncate_text(long_text, max_length=20)

        assert len(truncated) <= 20
        assert '...' in truncated

    def test_truncate_short_text(self):
        """Test truncation of short text (should not truncate)"""
        from backend.utils.formatters import truncate_text

        short_text = "Short"
        result = truncate_text(short_text, max_length=20)

        assert result == short_text
        assert '...' not in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
