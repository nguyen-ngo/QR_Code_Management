"""
Project Model for QR Attendance Management System
================================================

Project model to organize QR codes by projects.
Extracted from app.py for better code organization.
"""

from datetime import datetime
from . import base

class Project(base.db.Model):
    """
    Project model to organize QR codes by projects
    """
    __tablename__ = 'projects'
    
    id = base.db.Column(base.db.Integer, primary_key=True)
    name = base.db.Column(base.db.String(100), nullable=False)
    description = base.db.Column(base.db.Text, nullable=True)
    created_by = base.db.Column(base.db.Integer, base.db.ForeignKey('users.id'), nullable=True)
    created_date = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    active_status = base.db.Column(base.db.Boolean, default=True)
    
    # Relationships
    qr_codes = base.db.relationship('QRCode', backref='project', lazy='dynamic')
    creator = base.db.relationship('User', backref='created_projects')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    @property
    def qr_count(self):
        """Get count of QR codes in this project"""
        return self.qr_codes.filter_by(active_status=True).count()
    
    @property
    def total_qr_count(self):
        """Get total count of QR codes (including inactive) in this project"""
        return self.qr_codes.count()