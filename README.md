# 🗄️ PL/SQL Workbench - Oracle Database Toolkit

A comprehensive Oracle database management tool with PL/SQL unwrapping, query execution, data export, and advanced features for DBAs and developers.

**Original unwrapper live demo:** https://faice.me/sql

---

## ✨ Features

### 🔓 PL/SQL Unwrapper (Core Feature)
- **Unwrap Oracle PL/SQL** code (versions 11g through 20c+)
- Support for packages, procedures, functions, triggers, and types
- **Unwrap from text** - Paste wrapped code directly
- **Unwrap from database** - Connect and unwrap directly from Oracle DB
- Download unwrapped code as .sql files
- Supports all wrapped object types

### 🔌 Database Connectivity
- **Multiple connection management** - Save and manage Oracle connections
- Connection types: Service Name, SID, TNS
- **Encrypted password storage** - AES-256 encryption with Fernet
- **Test connections** - Verify connectivity before use
- **Active/inactive** status tracking

### 📊 Query Editor & Execution
- **Execute SQL queries** with full result display
- **Real-time execution metrics** - Row counts, execution time
- **Query history tracking** - Review past queries
- **Saved queries** with folders and tags
- **Query templates** - 40+ pre-built SQL templates
- **Schema browsing** - Explore tables, views, procedures, packages

### 💾 Data Export
Export query results to multiple formats:
- **CSV** - Customizable delimiter and headers
- **Excel (XLSX)** - Formatted spreadsheets with styling
- **JSON** - Structured data with pretty-print option
- **SQL** - INSERT statements for data migration
- **Markdown** - GitHub-flavored tables
- **HTML** - Styled tables for reports

### 🎨 SQL Formatting
- **Auto-format SQL** - Beautify messy queries
- **Keyword capitalization** - Consistent style
- **Smart indentation** - Context-aware formatting
- **PL/SQL support** - BEGIN/END blocks, packages, procedures
- **Comment preservation** - Keeps your documentation
- **Syntax validation** - Basic error checking
- **Minification** - Remove unnecessary whitespace

### 📚 Query Templates
Pre-built templates organized by category:
- **DDL** - CREATE TABLE, ALTER TABLE, indexes
- **DML** - SELECT, INSERT, UPDATE, DELETE, JOINs
- **PL/SQL** - Procedures, functions, packages, blocks
- **Admin** - Metadata queries, object lists
- **Performance** - Execution plans, statistics
- **Snippets** - Date formatting, string operations, NULL handling

### 🎯 Modern Web Interface
- **Single-page application** - No page reloads
- **Tabbed interface** - Organized by function
- **Dark theme** - Easy on the eyes (VS Code-inspired)
- **Responsive design** - Works on desktop, tablet, mobile
- **Real-time feedback** - Loading states, alerts, status updates

---

## 📸 Screenshots

### Unwrap SQL Interface
![Unwrap Example 1](https://user-images.githubusercontent.com/2806556/195683178-aa78c48b-981b-45ef-8a0b-0cca38c5fbc8.png)

### Unwrap Results
![Unwrap Example 2](https://user-images.githubusercontent.com/2806556/195683326-96ea33d7-e1fc-4bab-8724-e7ba11cbcf96.png)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Oracle Instant Client (for database connectivity)
- Oracle Database 11g or higher (for unwrap-from-db feature)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/RemmyLee/Oracle-SQL-Unwrapper.git
cd Oracle-SQL-Unwrapper
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration:
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
# - ENCRYPTION_KEY (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
# - FLASK_ENV=development
```

5. **Initialize database:**
```bash
python -c "from backend.app import create_app; app = create_app(); app.app_context().push(); from backend.extensions import db; db.create_all()"
```

6. **Run the application:**
```bash
python run.py
```

7. **Open browser:**
```
http://localhost:3117
```

---

## 📖 Usage Guide

### Unwrapping PL/SQL

#### From Text:
1. Go to **Unwrap SQL** tab
2. Select **Paste Text** mode
3. Paste your wrapped PL/SQL code
4. Click **Unwrap**
5. Copy, format, or download the result

#### From Database:
1. Go to **Connections** tab and create a connection
2. Go to **Unwrap SQL** tab
3. Select **From Database** mode
4. Choose connection and object details
5. Click **Unwrap from Database**

### Managing Connections

1. Go to **Connections** tab
2. Click **+ New Connection**
3. Enter connection details:
   - Connection name (e.g., "Production DB")
   - Connection type (Service Name, SID, or TNS)
   - Host and port
   - Service name or SID
   - Username and password
4. Click **Test Connection** to verify
5. Click **Save**

### Executing Queries

1. Go to **Query Editor** tab
2. Select a connection
3. Enter your SQL query
4. Click **Execute**
5. View results in table format
6. Export results using CSV/Excel/JSON buttons

### Using Query Templates

1. Go to **Query Editor** tab
2. Browse templates in the sidebar
3. Click a template to load it
4. Customize as needed
5. Execute or save for later

### Saving Queries

1. Write a query in **Query Editor**
2. Click **Save**
3. Enter name, description, folder, and tags
4. Access from **Saved Queries** tab later

### Exporting Data

After executing a query:
1. Click **Export CSV**, **Export Excel**, or **Export JSON**
2. Choose export options (if applicable)
3. File downloads automatically

---

## 🏗️ Architecture

```
Oracle-SQL-Unwrapper/
├── backend/
│   ├── api/              # REST API endpoints
│   │   ├── unwrap.py              # Unwrap endpoints
│   │   ├── connections.py         # Connection management
│   │   ├── queries.py             # Query execution
│   │   ├── export.py              # Data export
│   │   ├── saved_queries.py       # Saved queries
│   │   └── templates.py           # Query templates
│   ├── services/         # Business logic
│   │   ├── unwrapper.py           # Core unwrapping
│   │   ├── oracle_connector.py    # DB connectivity
│   │   └── data_exporter.py       # Export functionality
│   ├── models/           # Database models
│   │   ├── connection.py          # Connection model
│   │   └── query_history.py       # Query history & saved queries
│   ├── utils/            # Utilities
│   │   ├── sql_formatter.py       # SQL formatting
│   │   ├── validators.py          # Input validation
│   │   └── formatters.py          # Output formatting
│   ├── data/             # Static data
│   │   └── query_templates.json   # SQL templates
│   ├── config.py         # Configuration
│   ├── extensions.py     # Flask extensions
│   └── app.py            # Application factory
├── templates/            # HTML templates
│   └── index.html                 # Main UI
├── tests/                # Test suite
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
├── run.py                # Application entry point
└── README.md             # This file
```

---

## 🛠️ Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_unwrapper.py -v

# Run with coverage
pytest --cov=backend --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
black backend/ tests/

# Lint code
flake8 backend/ tests/
```

### Adding New Templates

Edit `backend/data/query_templates.json`:

```json
{
  "categories": [
    {
      "name": "My Category",
      "description": "Description here",
      "templates": [
        {
          "name": "Template Name",
          "description": "What it does",
          "sql": "SELECT * FROM...",
          "tags": ["tag1", "tag2"]
        }
      ]
    }
  ]
}
```

---

## 📦 Dependencies

### Core:
- **Flask** 2.3.3 - Web framework
- **SQLAlchemy** 2.0.20 - ORM for app metadata
- **cx_Oracle** 8.3.0 - Oracle database driver
- **cryptography** 41.0.4 - Password encryption

### Optional:
- **openpyxl** 3.1.2 - Excel export (recommended)

### Development:
- **pytest** 7.4.2 - Testing framework
- **black** 23.9.1 - Code formatting
- **flake8** 6.1.0 - Linting

---

## 🔐 Security

### Password Storage
- Passwords encrypted with **Fernet (AES-256)**
- Encryption key stored in environment variable
- Never stored in plain text

### Input Validation
- SQL injection prevention
- Input size limits
- Type validation
- Sanitization of user inputs

### Best Practices
- Use strong `SECRET_KEY` and `ENCRYPTION_KEY`
- Never commit `.env` file
- Use HTTPS in production
- Implement rate limiting (Phase 4)

---

## 🌍 Deployment

### Production Setup

1. **Set environment to production:**
```bash
export FLASK_ENV=production
```

2. **Use production WSGI server:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:3117 'backend.app:create_app()'
```

3. **Set up reverse proxy (nginx example):**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3117;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. **Configure Oracle Instant Client:**
```bash
# Install Oracle Instant Client
# Set environment variables:
export LD_LIBRARY_PATH=/path/to/instantclient
export ORACLE_HOME=/path/to/instantclient
```

---

## 📊 Project Status

### Completed Phases:
- ✅ **Phase 1** - Foundation & Core Features
- ✅ **Phase 2** - Database Connectivity
- ✅ **Phase 3** - Advanced Features (Data Export, Templates, Formatting)

### Phase 4 (Planned):
- 🔜 User authentication & authorization
- 🔜 Multi-user support
- 🔜 Role-based access control
- 🔜 Query scheduling
- 🔜 Email notifications
- 🔜 Production monitoring

---

## 📝 API Documentation

### Unwrap Endpoints

#### POST /api/unwrap
Unwrap PL/SQL from text input.

```bash
curl -X POST http://localhost:3117/api/unwrap \
  -H "Content-Type: application/json" \
  -d '{"content": "a7 100\nYWJj..."}'
```

#### POST /api/unwrap-from-db
Unwrap PL/SQL directly from database.

```bash
curl -X POST http://localhost:3117/api/unwrap-from-db \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": 1,
    "object_type": "PACKAGE BODY",
    "object_name": "MY_PACKAGE"
  }'
```

### Connection Endpoints

#### GET /api/connections
List all connections.

#### POST /api/connections
Create new connection.

#### POST /api/connections/{id}/test
Test connection.

### Query Endpoints

#### POST /api/execute
Execute SQL query.

```bash
curl -X POST http://localhost:3117/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": 1,
    "sql": "SELECT * FROM employees"
  }'
```

### Export Endpoints

#### POST /api/export
Export data to specified format.

```bash
curl -X POST http://localhost:3117/api/export \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"columns": [...], "rows": [...]},
    "format": "xlsx"
  }' --output report.xlsx
```

### Template Endpoints

#### GET /api/templates
List all query templates.

#### GET /api/templates/search?q=keyword
Search templates.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines:
- Follow PEP 8 style guide
- Write unit tests for new features
- Update documentation
- Keep commits atomic and descriptive

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Original PL/SQL unwrapping algorithm based on Oracle's wrap utility
- Inspired by the need for a free, open-source Oracle toolkit
- Built for DBAs, developers, and security researchers

---

## 📞 Support

### Issues
Report bugs and request features on [GitHub Issues](https://github.com/RemmyLee/Oracle-SQL-Unwrapper/issues)

### Documentation
- `CLAUDE.md` - AI assistant development guide
- `IMPLEMENTATION_GUIDE.md` - Full feature roadmap
- `PHASE1_COMPLETION.md` - Phase 1 summary
- `PHASE2_COMPLETION.md` - Phase 2 summary
- `PHASE3_COMPLETION.md` - Phase 3 summary

---

## 🎯 Use Cases

### For DBAs:
- Unwrap vendor-provided wrapped code for analysis
- Execute queries across multiple databases
- Export data for reporting and analysis
- Browse schema objects quickly

### For Developers:
- Understand wrapped legacy code
- Test SQL queries with real-time feedback
- Use templates for common patterns
- Format messy SQL code

### For Security Researchers:
- Analyze wrapped PL/SQL for vulnerabilities
- Reverse engineer database logic
- Audit Oracle database code

---

**Built with ❤️ for the Oracle community**

**Star ⭐ this repo if you find it useful!**
