# PL/SQL Workbench - Oracle Database Toolkit

A comprehensive web-based Oracle database management tool featuring PL/SQL unwrapping, query execution, schema exploration, and advanced development features.

**Version:** 2.0.0
**Live Demo:** https://faice.me/sql

## Features

### Phase 1: Foundation (✅ Completed)

- **Enhanced PL/SQL Unwrapper**
  - Support for Oracle 11g through 20c+
  - Batch unwrapping multiple files
  - Format auto-detection
  - Comprehensive error handling
  - Input validation and security checks

- **Modern Architecture**
  - Modular backend structure
  - RESTful API design
  - Comprehensive test suite
  - Secure credential storage

### Phase 2-4: Coming Soon

- Database connectivity and query execution
- Monaco-based SQL editor with IntelliSense
- Performance analysis and optimization tools
- Team collaboration features
- And much more! (See IMPLEMENTATION_GUIDE.md)

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/RemmyLee/Oracle-SQL-Unwrapper.git
cd Oracle-SQL-Unwrapper
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and update SECRET_KEY and ENCRYPTION_KEY
```

5. Run the application:
```bash
python run.py
```

6. Open your browser to: http://localhost:3117

## Project Structure

```
Oracle-SQL-Unwrapper/
├── backend/                 # Backend application
│   ├── api/                # REST API endpoints
│   │   └── unwrap.py       # Unwrapper API
│   ├── models/             # Database models
│   │   ├── user.py
│   │   ├── connection.py
│   │   └── query_history.py
│   ├── services/           # Business logic
│   │   └── unwrapper.py    # Core unwrapping service
│   ├── utils/              # Utilities
│   │   ├── validators.py
│   │   └── formatters.py
│   ├── app.py              # App factory
│   ├── config.py           # Configuration
│   └── extensions.py       # Flask extensions
├── frontend/               # Frontend application (future)
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── templates/              # HTML templates
├── docs/                   # Documentation
├── run.py                  # Application entry point
├── requirements.txt        # Python dependencies
├── CLAUDE.md              # AI assistant guide
└── IMPLEMENTATION_GUIDE.md # Full implementation roadmap
```

## API Documentation

### Unwrap PL/SQL Code

**Endpoint:** `POST /api/unwrap`

**Request:**
```json
{
  "content": "a7 100\nYWJjZGVmZ2hp...",
  "format": "auto"
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "unwrapped": "CREATE OR REPLACE PACKAGE...",
    "format_detected": "11g",
    "statistics": {
      "original_size": 1024,
      "unwrapped_size": 2048,
      "compression_ratio": 0.5
    }
  },
  "warnings": []
}
```

### Batch Unwrap

**Endpoint:** `POST /api/unwrap/batch`

**Request:**
```json
{
  "files": [
    {"name": "package1.sql", "content": "wrapped content..."},
    {"name": "package2.sql", "content": "wrapped content..."}
  ]
}
```

### Validate Wrapped Content

**Endpoint:** `POST /api/unwrap/validate`

**Request:**
```json
{
  "content": "a7 100\nYWJjZGVmZ2hp..."
}
```

### Health Check

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest tests/unit/test_unwrapper.py -v
```

## Development

### Code Style

This project uses Black for code formatting and Flake8 for linting:

```bash
# Format code
black backend/ tests/

# Check code style
flake8 backend/ tests/
```

### Environment Variables

See `.env.example` for all available configuration options.

**Important:** Always change `SECRET_KEY` and `ENCRYPTION_KEY` in production!

## Security Considerations

- All database connection passwords are encrypted using Fernet (AES-256)
- Input validation prevents malicious content
- SQL injection protection via parameterized queries (Phase 2+)
- CORS configuration for API security
- Rate limiting available (Phase 4)

## Documentation

- **CLAUDE.md** - Comprehensive guide for AI assistants and developers
- **IMPLEMENTATION_GUIDE.md** - Full roadmap for expanding to complete Oracle toolkit
- **API Documentation** - See `/docs` directory (coming soon)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Roadmap

- [x] Phase 1: Foundation & Core Features
- [ ] Phase 2: Database Connectivity (6-8 weeks)
- [ ] Phase 3: Advanced Features (8-10 weeks)
- [ ] Phase 4: Enterprise Features (10-12 weeks)

See **IMPLEMENTATION_GUIDE.md** for detailed roadmap.

## License

This project is licensed under the MIT License.

## Acknowledgments

- Oracle's character substitution map for PL/SQL wrapping
- Flask and the Python community
- All contributors and users

## Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check the documentation in `/docs`
- Review CLAUDE.md for technical details

---

**Made with ❤️ for Oracle developers everywhere**
