"""
Formatting utilities for SQL and other outputs
"""

import re
from typing import List, Dict


def format_sql(sql: str, indent: int = 2) -> str:
    """
    Basic SQL formatting

    Args:
        sql: SQL code to format
        indent: Number of spaces for indentation

    Returns:
        Formatted SQL
    """
    if not sql:
        return ""

    # Keywords that should start on a new line
    keywords = [
        'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY',
        'HAVING', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN',
        'UNION', 'INTERSECT', 'MINUS', 'INSERT', 'UPDATE', 'DELETE',
        'CREATE', 'ALTER', 'DROP'
    ]

    formatted = sql

    # Add newlines before major keywords
    for keyword in keywords:
        pattern = r'\b' + keyword + r'\b'
        formatted = re.sub(pattern, '\n' + keyword, formatted, flags=re.IGNORECASE)

    # Clean up extra whitespace
    lines = [line.strip() for line in formatted.split('\n')]
    formatted = '\n'.join(line for line in lines if line)

    return formatted


def format_bytes(bytes_size: int) -> str:
    """
    Format bytes to human-readable format

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def format_duration(milliseconds: float) -> str:
    """
    Format duration in milliseconds to human-readable format

    Args:
        milliseconds: Duration in milliseconds

    Returns:
        Formatted string (e.g., "1.5s", "250ms")
    """
    if milliseconds < 1000:
        return f"{milliseconds:.0f}ms"
    elif milliseconds < 60000:
        return f"{milliseconds / 1000:.2f}s"
    else:
        minutes = int(milliseconds / 60000)
        seconds = (milliseconds % 60000) / 1000
        return f"{minutes}m {seconds:.0f}s"


def format_table_results(columns: List[str], rows: List[List], max_width: int = 50) -> str:
    """
    Format query results as ASCII table

    Args:
        columns: Column names
        rows: Data rows
        max_width: Maximum column width

    Returns:
        Formatted table string
    """
    if not columns or not rows:
        return "No results"

    # Calculate column widths
    widths = [len(col) for col in columns]

    for row in rows[:100]:  # Sample first 100 rows for width calculation
        for i, val in enumerate(row):
            val_len = len(str(val))
            if val_len > widths[i]:
                widths[i] = min(val_len, max_width)

    # Create separator
    separator = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'

    # Create header
    header = '|' + '|'.join(f" {col:{widths[i]}} " for i, col in enumerate(columns)) + '|'

    # Create rows
    result_lines = [separator, header, separator]

    for row in rows:
        row_str = '|'
        for i, val in enumerate(row):
            val_str = str(val) if val is not None else 'NULL'
            if len(val_str) > max_width:
                val_str = val_str[:max_width - 3] + '...'
            row_str += f" {val_str:{widths[i]}} |"
        result_lines.append(row_str)

    result_lines.append(separator)

    return '\n'.join(result_lines)


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to maximum length

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def highlight_sql_errors(sql: str, error_offset: int = None) -> str:
    """
    Highlight error position in SQL

    Args:
        sql: SQL code
        error_offset: Character offset of error

    Returns:
        SQL with error marker
    """
    if error_offset is None:
        return sql

    lines = sql.split('\n')
    current_offset = 0

    for i, line in enumerate(lines):
        if current_offset + len(line) >= error_offset:
            # Error is in this line
            line_offset = error_offset - current_offset
            marker = ' ' * line_offset + '^--- ERROR HERE'
            lines.insert(i + 1, marker)
            break
        current_offset += len(line) + 1  # +1 for newline

    return '\n'.join(lines)
