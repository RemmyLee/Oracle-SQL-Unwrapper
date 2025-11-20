# CLAUDE.md - AI Assistant Guide for Oracle SQL Unwrapper

## Project Overview

This is a **Oracle PL/SQL Unwrapper** tool that decodes wrapped/obfuscated PL/SQL code from Oracle databases (versions 11g through 20c+). The tool is implemented as a Flask web application that provides a simple interface for unwrapping Oracle's proprietary code obfuscation format.

**Live Demo**: https://faice.me/sql

### Purpose

Oracle Database allows developers to wrap (obfuscate) PL/SQL source code to protect intellectual property. This tool reverses that process by:
1. Parsing the wrapped format structure
2. Base64 decoding the content
3. Applying character substitution (using Oracle's known character map)
4. Decompressing with zlib to reveal the original SQL

## Repository Structure

```
Oracle-SQL-Unwrapper/
├── sql_unwrapper.py          # Main Flask application (core logic)
├── templates/
│   └── index.html            # Web UI template with dark theme
├── requirements.txt          # Python dependencies (Flask only)
├── README.md                 # Basic documentation with screenshots
└── tortoise_tts.ipynb        # ⚠️ Unrelated notebook (TTS experiments - appears to be artifact)
```

### File Purposes

- **`sql_unwrapper.py`** (310 lines): Contains all application logic
  - Character map for Oracle's substitution cipher (lines 9-266)
  - `decode_base64_package()` function (lines 269-274): Core unwrapping algorithm
  - Flask routes: `/` (index) and `/unwrap` (POST handler)

- **`templates/index.html`**: Single-page web interface
  - Dark theme UI (#202325 background)
  - Textarea for wrapped SQL input
  - Results display with syntax formatting
  - Usage instructions

- **`tortoise_tts.ipynb`**: NOT part of the SQL unwrapper - appears to be a misplaced Google Colab notebook about text-to-speech. Should likely be removed.

## Technical Architecture

### Core Algorithm (sql_unwrapper.py:269-274)

```python
def decode_base64_package(base64str):
    base64dec = base64.decodebytes(bytearray(base64str.encode("latin-1")))[20:]  # Skip 20-byte header
    decoded = ""
    for byte in range(0, len(base64dec)):
        decoded += chr(charmap[ord(chr(base64dec[byte]))])  # Character substitution
    return zlib.decompress(bytearray(decoded.encode("latin-1")))  # Decompress
```

### Wrapped SQL Format

Oracle's wrapped format follows this pattern (detected via regex at line 290):
```
<hex_marker> <hex_length>
<base64_encoded_data>
<base64_encoded_data>
...
```

Example pattern: `^[0-9a-f]+ ([0-9a-f]+)$`

### Dependencies

- **Flask**: Web framework (only dependency)
- **Standard Library**: `re`, `base64`, `zlib`, `sys`

### Configuration

- **Default Port**: 3117
- **Host**: 0.0.0.0 (all interfaces)
- **Debug Mode**: Enabled (should be disabled in production)

## Development Workflows

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python sql_unwrapper.py

# Access at http://localhost:3117
```

### Testing the Unwrapper

1. Obtain wrapped PL/SQL from Oracle database:
   ```sql
   SELECT TEXT FROM USER_SOURCE WHERE TYPE = 'PACKAGE BODY' AND NAME = 'YOUR_PACKAGE';
   ```

2. Paste wrapped content into web form
3. Submit to see unwrapped SQL

### Key Conventions for AI Assistants

#### Code Style

1. **Encoding**: All string operations use `latin-1` encoding (critical for Oracle's format)
2. **Character Map**: The 256-byte character map at lines 9-266 is Oracle's proprietary substitution cipher - DO NOT MODIFY
3. **Regex Pattern**: Line 290 pattern matches Oracle's wrapped format structure
4. **HTML Escaping**: Output uses `<br>` and `&nbsp;` for formatting (lines 300-302)

#### Security Considerations

⚠️ **Important Security Notes**:

1. **No Input Validation**: Current implementation has NO validation of uploaded content
   - Potential for malicious base64 payloads
   - No size limits on input
   - Consider adding: max length checks, timeout limits, sanitization

2. **Debug Mode in Production**: Line 310 has `debug=True` - MUST be disabled for production deployment

3. **Hard-coded URLs**: HTML template has hard-coded `127.0.0.1:3117` URLs (lines 69, 75)
   - Should use Flask's `url_for()` function
   - Breaks when deployed on different host/port

4. **XSS Risk**: Uses `|safe` filter in Jinja2 (line 66) without sanitization
   - Unwrapped SQL is rendered as raw HTML
   - Could expose XSS if malicious SQL contains JavaScript

#### Common Development Tasks

**Adding Error Handling**:
- Current implementation returns generic "Error" on GET requests (line 306)
- Add try/except around `decode_base64_package()` for malformed input
- Handle invalid base64, decompression errors, encoding issues

**Improving the UI**:
- Template is at `templates/index.html`
- Uses inline CSS (lines 3-57)
- Consider extracting to separate CSS file
- Add copy-to-clipboard functionality
- Add syntax highlighting for SQL output

**Production Deployment**:
- Remove `debug=True` from line 310
- Use production WSGI server (gunicorn, uwsgi)
- Add proper logging instead of Flask debug output
- Set up reverse proxy (nginx, Apache)
- Add rate limiting to prevent abuse

**Testing**:
- No test suite currently exists
- Should add unit tests for `decode_base64_package()`
- Integration tests for Flask routes
- Sample wrapped SQL fixtures

## Git Workflow

### Branch Strategy

- **Main Branch**: Production-ready code (not explicitly named in repo)
- **Feature Branches**: Use `claude/` prefix for AI assistant work
- Current branch: `claude/claude-md-mi6xt59n69o23ftr-019b7MdiY6csqqyQuQcrGzqX`

### Commit History Patterns

Recent commits focus on documentation updates:
- `316a9d8`: Created using Colaboratory (the TTS notebook)
- `090f1b8`: Cosmetic Changes
- Multiple README.md updates

**Commit Message Style**:
- Descriptive but concise
- Focus on "what" changed (e.g., "Update README.md", "Cosmetic Changes")
- Consider adding more detail about "why" changes were made

## Common Pitfalls & Gotchas

1. **Character Map Integrity**: The 256-element `charmap` array is critical. If even one byte is wrong, unwrapping fails completely.

2. **20-Byte Header**: Line 270 skips first 20 bytes of decoded base64 - this is Oracle's metadata header. Don't remove this.

3. **Latin-1 Encoding**: Must use `latin-1` throughout, not UTF-8. Oracle's format predates modern Unicode usage.

4. **Regex Line Matching**: The unwrapper expects specific hex format on first line, then continuation lines of base64. Whitespace matters.

5. **Zlib Decompression**: Final step uses zlib. If decompression fails, the input wasn't valid wrapped SQL.

6. **tortoise_tts.ipynb**: This file is unrelated to the project. It's a Google Colab notebook about text-to-speech generation that was likely committed by mistake.

## Enhancement Opportunities

### High Priority

1. **Add Input Validation**:
   - Max input size (prevent DoS)
   - Format validation before processing
   - Proper error messages for users

2. **Security Hardening**:
   - Disable debug mode
   - Add request timeouts
   - Sanitize HTML output
   - Add CSRF protection

3. **Better Error Handling**:
   - Try/except blocks around decoding
   - User-friendly error messages
   - Logging for debugging

### Medium Priority

4. **API Endpoint**: Add `/api/unwrap` for programmatic access with JSON response

5. **CLI Tool**: Add command-line interface for batch processing

6. **Testing**: Unit tests, integration tests, sample fixtures

7. **Code Organization**: Consider splitting into modules if adding features:
   ```
   app/
   ├── __init__.py
   ├── unwrapper.py      # Core algorithm
   ├── routes.py         # Flask routes
   └── utils.py          # Helper functions
   ```

### Low Priority

8. **Documentation**: Add docstrings to functions

9. **Syntax Highlighting**: Add SQL syntax highlighting to output

10. **Download Feature**: Allow downloading unwrapped SQL as .sql file

## Questions to Ask Users

When receiving requests for this project, clarify:

1. **Deployment Context**: Local development vs. production deployment?
2. **Input Source**: Where is the wrapped SQL coming from? (Direct DB query, file upload, etc.)
3. **Security Requirements**: Is this internal tool or public-facing?
4. **Oracle Version**: Which Oracle version(s) need to be supported?
5. **Scale**: Expected volume of unwrapping requests?

## Resources & References

- **Oracle Wrap Utility**: Official Oracle documentation on PL/SQL wrapping
- **Live Tool**: https://faice.me/sql (reference implementation)
- **Flask Documentation**: https://flask.palletsprojects.com/

## AI Assistant Guidelines

### DO:
- ✅ Preserve the character map exactly as-is
- ✅ Test changes with sample wrapped SQL
- ✅ Add input validation for security
- ✅ Improve error messages for users
- ✅ Follow existing code style (minimal, functional)
- ✅ Ask about deployment context before suggesting major changes

### DON'T:
- ❌ Modify the character map values
- ❌ Change encoding from latin-1 to UTF-8
- ❌ Remove the 20-byte header skip
- ❌ Commit changes with debug=True for production
- ❌ Assume the tortoise_tts.ipynb file is relevant to SQL unwrapping
- ❌ Add heavy dependencies without discussion

### When Modifying:
1. Read existing code first to understand the flow
2. Test with valid wrapped SQL samples
3. Consider backward compatibility
4. Add comments for non-obvious logic
5. Update this CLAUDE.md if architecture changes

---

**Last Updated**: 2025-11-20
**Repository**: https://github.com/RemmyLee/Oracle-SQL-Unwrapper
