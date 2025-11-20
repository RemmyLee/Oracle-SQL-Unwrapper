"""
Dashboard model (stub for Phase 4, full implementation in Phase 5)
Placeholder to support user relationships
"""

from datetime import datetime
from backend.extensions import db


class Dashboard(db.Model):
    """
    Dashboard model (basic structure)
    Full implementation will be added in Phase 5
    """

    __tablename__ = 'dashboards'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Basic fields
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    slug = db.Column(db.String(200), unique=True, nullable=True, index=True)

    # Access control
    access_level = db.Column(db.String(20), default='private', nullable=False)  # private, authenticated, public
    is_published = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = db.relationship('User', back_populates='owned_dashboards', foreign_keys=[owner_id])

    def __repr__(self):
        return f'<Dashboard {self.title}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'title': self.title,
            'description': self.description,
            'slug': self.slug,
            'access_level': self.access_level,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
