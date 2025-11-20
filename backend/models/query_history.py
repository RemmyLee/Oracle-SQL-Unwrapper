"""
Query history and saved queries models
"""

from datetime import datetime
from backend.extensions import db


class QueryHistory(db.Model):
    """History of executed queries"""

    __tablename__ = 'query_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    connection_id = db.Column(db.Integer, db.ForeignKey('oracle_connections.id'))

    # Query details
    sql_text = db.Column(db.Text, nullable=False)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Execution results
    execution_time_ms = db.Column(db.Float)
    row_count = db.Column(db.Integer)
    success = db.Column(db.Boolean)
    error_message = db.Column(db.Text)

    # Metadata
    is_favorite = db.Column(db.Boolean, default=False)
    tags = db.Column(db.JSON)

    # Relationships
    connection = db.relationship('OracleConnection', backref='query_history')

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'sql_text': self.sql_text,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_time_ms': self.execution_time_ms,
            'row_count': self.row_count,
            'success': self.success,
            'error_message': self.error_message,
            'is_favorite': self.is_favorite,
            'tags': self.tags,
            'connection_id': self.connection_id
        }

    def __repr__(self):
        return f'<QueryHistory {self.id}>'


class SavedQuery(db.Model):
    """User's saved/favorite queries"""

    __tablename__ = 'saved_queries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Query metadata
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sql_text = db.Column(db.Text, nullable=False)

    # Organization
    folder = db.Column(db.String(100))  # Organize in folders
    tags = db.Column(db.JSON)
    color = db.Column(db.String(7))  # Hex color for UI

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Usage statistics
    execution_count = db.Column(db.Integer, default=0)
    last_executed = db.Column(db.DateTime)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'sql_text': self.sql_text,
            'folder': self.folder,
            'tags': self.tags,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'execution_count': self.execution_count,
            'last_executed': self.last_executed.isoformat() if self.last_executed else None
        }

    def __repr__(self):
        return f'<SavedQuery {self.name}>'
