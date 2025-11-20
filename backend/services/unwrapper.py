"""
Oracle PL/SQL Unwrapper Service
Decodes wrapped/obfuscated PL/SQL code from Oracle databases (11g-20c+)
"""

import re
import base64
import zlib
import logging
from typing import Dict, Tuple, List
from functools import wraps
import signal


logger = logging.getLogger(__name__)


# Oracle's proprietary character substitution map
# DO NOT MODIFY - This is Oracle's exact substitution cipher
CHARMAP = [
    0x3D, 0x65, 0x85, 0xB3, 0x18, 0xDB, 0xE2, 0x87,
    0xF1, 0x52, 0xAB, 0x63, 0x4B, 0xB5, 0xA0, 0x5F,
    0x7D, 0x68, 0x7B, 0x9B, 0x24, 0xC2, 0x28, 0x67,
    0x8A, 0xDE, 0xA4, 0x26, 0x1E, 0x03, 0xEB, 0x17,
    0x6F, 0x34, 0x3E, 0x7A, 0x3F, 0xD2, 0xA9, 0x6A,
    0x0F, 0xE9, 0x35, 0x56, 0x1F, 0xB1, 0x4D, 0x10,
    0x78, 0xD9, 0x75, 0xF6, 0xBC, 0x41, 0x04, 0x81,
    0x61, 0x06, 0xF9, 0xAD, 0xD6, 0xD5, 0x29, 0x7E,
    0x86, 0x9E, 0x79, 0xE5, 0x05, 0xBA, 0x84, 0xCC,
    0x6E, 0x27, 0x8E, 0xB0, 0x5D, 0xA8, 0xF3, 0x9F,
    0xD0, 0xA2, 0x71, 0xB8, 0x58, 0xDD, 0x2C, 0x38,
    0x99, 0x4C, 0x48, 0x07, 0x55, 0xE4, 0x53, 0x8C,
    0x46, 0xB6, 0x2D, 0xA5, 0xAF, 0x32, 0x22, 0x40,
    0xDC, 0x50, 0xC3, 0xA1, 0x25, 0x8B, 0x9C, 0x16,
    0x60, 0x5C, 0xCF, 0xFD, 0x0C, 0x98, 0x1C, 0xD4,
    0x37, 0x6D, 0x3C, 0x3A, 0x30, 0xE8, 0x6C, 0x31,
    0x47, 0xF5, 0x33, 0xDA, 0x43, 0xC8, 0xE3, 0x5E,
    0x19, 0x94, 0xEC, 0xE6, 0xA3, 0x95, 0x14, 0xE0,
    0x9D, 0x64, 0xFA, 0x59, 0x15, 0xC5, 0x2F, 0xCA,
    0xBB, 0x0B, 0xDF, 0xF2, 0x97, 0xBF, 0x0A, 0x76,
    0xB4, 0x49, 0x44, 0x5A, 0x1D, 0xF0, 0x00, 0x96,
    0x21, 0x80, 0x7F, 0x1A, 0x82, 0x39, 0x4F, 0xC1,
    0xA7, 0xD7, 0x0D, 0xD1, 0xD8, 0xFF, 0x13, 0x93,
    0x70, 0xEE, 0x5B, 0xEF, 0xBE, 0x09, 0xB9, 0x77,
    0x72, 0xE7, 0xB2, 0x54, 0xB7, 0x2A, 0xC7, 0x73,
    0x90, 0x66, 0x20, 0x0E, 0x51, 0xED, 0xF8, 0x7C,
    0x8F, 0x2E, 0xF4, 0x12, 0xC6, 0x2B, 0x83, 0xCD,
    0xAC, 0xCB, 0x3B, 0xC4, 0x4E, 0xC0, 0x69, 0x36,
    0x62, 0x02, 0xAE, 0x88, 0xFC, 0xAA, 0x42, 0x08,
    0xA6, 0x45, 0x57, 0xD3, 0x9A, 0xBD, 0xE1, 0x23,
    0x8D, 0x92, 0x4A, 0x11, 0x89, 0x74, 0x6B, 0x91,
    0xFB, 0xFE, 0xC9, 0x01, 0xEA, 0x1B, 0xF7, 0xCE,
]


class UnwrapError(Exception):
    """Base exception for unwrapping errors"""
    pass


class InvalidFormatError(UnwrapError):
    """Invalid wrapped format"""
    pass


class DecompressionError(UnwrapError):
    """Decompression failed"""
    pass


class TimeoutError(UnwrapError):
    """Operation timed out"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Operation timed out")


def with_timeout(seconds):
    """Decorator to add timeout to function execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set up the signal handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                # Disable the alarm
                signal.alarm(0)
            return result
        return wrapper
    return decorator


class UnwrapperService:
    """
    Enhanced Oracle PL/SQL unwrapper service

    Supports Oracle versions 11g through 20c+
    """

    def __init__(self, max_size: int = 10 * 1024 * 1024, timeout: int = 30):
        """
        Initialize unwrapper service

        Args:
            max_size: Maximum input size in bytes (default 10MB)
            timeout: Timeout in seconds (default 30s)
        """
        self.max_size = max_size
        self.timeout = timeout

    def unwrap(self, content: str, format_type: str = 'auto') -> Dict:
        """
        Unwrap Oracle wrapped code

        Args:
            content: Wrapped PL/SQL content
            format_type: 'auto', '10g', '11g', '12c', '19c', '20c'

        Returns:
            {
                'success': bool,
                'unwrapped': str,
                'format_detected': str,
                'metadata': dict,
                'warnings': list
            }
        """
        logger.info("Starting unwrap process")

        try:
            # Validate input
            is_valid, error_msg = self.validate_input(content)
            if not is_valid:
                raise InvalidFormatError(error_msg)

            # Detect format if auto
            if format_type == 'auto':
                format_detected = self.detect_format(content)
            else:
                format_detected = format_type

            # Parse wrapped content
            lines = content.replace('\r', '').split('\n')
            unwrapped_sql = None
            metadata = {}

            for i, line in enumerate(lines):
                # Look for wrapped format marker
                matches = re.compile(r'^([0-9a-f]+)\s+([0-9a-f]+)$').match(line.strip())

                if matches:
                    marker, base64len_hex = matches.groups()
                    base64len = int(base64len_hex, 16)
                    metadata['marker'] = marker
                    metadata['base64_length'] = base64len

                    # Collect base64 content from subsequent lines
                    base64str = ""
                    j = 0
                    while len(base64str) < base64len and (i + j + 1) < len(lines):
                        j += 1
                        base64str += lines[i + j].strip()

                    # Decode the package
                    unwrapped_sql = self._decode_base64_package(base64str)
                    metadata['original_size'] = len(base64str)
                    metadata['unwrapped_size'] = len(unwrapped_sql)
                    metadata['compression_ratio'] = round(len(base64str) / len(unwrapped_sql), 2)
                    break

            if unwrapped_sql is None:
                raise InvalidFormatError("No wrapped content found in input")

            warnings = []
            if metadata.get('compression_ratio', 0) < 0.3:
                warnings.append("Low compression ratio - verify unwrapped content")

            return {
                'success': True,
                'unwrapped': unwrapped_sql,
                'format_detected': format_detected,
                'metadata': metadata,
                'warnings': warnings
            }

        except InvalidFormatError as e:
            logger.error(f"Invalid format error: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid format',
                'message': str(e)
            }

        except DecompressionError as e:
            logger.error(f"Decompression error: {str(e)}")
            return {
                'success': False,
                'error': 'Decompression failed',
                'message': str(e)
            }

        except TimeoutError as e:
            logger.error(f"Timeout error: {str(e)}")
            return {
                'success': False,
                'error': 'Timeout',
                'message': 'Unwrapping operation timed out'
            }

        except Exception as e:
            logger.exception(f"Unexpected error during unwrap: {str(e)}")
            return {
                'success': False,
                'error': 'Unexpected error',
                'message': str(e)
            }

    @with_timeout(30)
    def _decode_base64_package(self, base64str: str) -> str:
        """
        Core decoding algorithm

        Steps:
        1. Base64 decode
        2. Skip 20-byte Oracle header
        3. Character substitution using CHARMAP
        4. Zlib decompression

        Args:
            base64str: Base64 encoded string

        Returns:
            Unwrapped SQL code

        Raises:
            DecompressionError: If decompression fails
        """
        try:
            # Step 1: Base64 decode
            base64dec = base64.decodebytes(bytearray(base64str.encode("latin-1")))

            # Step 2: Skip 20-byte Oracle metadata header
            base64dec = base64dec[20:]

            # Step 3: Character substitution
            decoded = ""
            for byte in range(0, len(base64dec)):
                decoded += chr(CHARMAP[ord(chr(base64dec[byte]))])

            # Step 4: Zlib decompression
            result = zlib.decompress(bytearray(decoded.encode("latin-1")))

            return result.decode('utf-8', errors='replace')

        except zlib.error as e:
            raise DecompressionError(f"Zlib decompression failed: {str(e)}")

        except Exception as e:
            raise DecompressionError(f"Decoding failed: {str(e)}")

    def validate_input(self, content: str) -> Tuple[bool, str]:
        """
        Validate wrapped input

        Args:
            content: Input content to validate

        Returns:
            (is_valid, error_message)
        """
        # Check size
        if len(content) > self.max_size:
            return False, f"Input exceeds maximum size of {self.max_size / (1024*1024)}MB"

        # Check for empty input
        if not content or not content.strip():
            return False, "Input is empty"

        # Check for wrapped format marker
        if not re.search(r'^[0-9a-f]+\s+[0-9a-f]+', content, re.MULTILINE):
            return False, "Input does not appear to be wrapped Oracle code (missing format marker)"

        # Check for potentially malicious patterns
        dangerous_patterns = [
            (r'<script', 'Potentially malicious script tag detected'),
            (r'javascript:', 'JavaScript protocol detected'),
            (r'onclick\s*=', 'Inline event handler detected'),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, message

        return True, "Valid"

    def detect_format(self, content: str) -> str:
        """
        Auto-detect Oracle version format

        Args:
            content: Wrapped content

        Returns:
            Detected format version ('10g', '11g', '12c', '19c', '20c', 'unknown')
        """
        # Look at the first line marker pattern
        match = re.search(r'^([0-9a-f]+)\s+([0-9a-f]+)', content, re.MULTILINE)

        if not match:
            return 'unknown'

        marker = match.group(1)

        # Oracle version markers (these are approximate based on common patterns)
        if marker.startswith('a'):
            return '11g'
        elif marker.startswith('b'):
            return '12c'
        elif marker.startswith('c'):
            return '19c'
        elif marker.startswith('d'):
            return '20c'
        else:
            return '11g'  # Default assumption

    def unwrap_batch(self, files: List[Dict]) -> List[Dict]:
        """
        Unwrap multiple files in batch

        Args:
            files: List of {'name': str, 'content': str} dicts

        Returns:
            List of unwrap results
        """
        results = []

        for file in files:
            result = self.unwrap(file['content'])
            result['filename'] = file['name']
            results.append(result)

        return results

    def get_statistics(self, content: str) -> Dict:
        """
        Get statistics about wrapped content without unwrapping

        Args:
            content: Wrapped content

        Returns:
            Statistics dictionary
        """
        stats = {
            'size_bytes': len(content),
            'line_count': len(content.split('\n')),
            'is_valid': False,
            'format': 'unknown'
        }

        is_valid, _ = self.validate_input(content)
        stats['is_valid'] = is_valid

        if is_valid:
            stats['format'] = self.detect_format(content)

        return stats
