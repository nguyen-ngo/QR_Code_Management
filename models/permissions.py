"""
Permission Models for QR Attendance Management System
====================================================

Permission models to manage Project Manager access control.
These models define which projects and locations a Project Manager can access.
"""

from datetime import datetime
from . import base

class UserProjectPermission(base.db.Model):
    """
    UserProjectPermission model to manage project access for Project Managers
    Links users to specific projects they are allowed to view
    """
    __tablename__ = 'user_project_permissions'
    
    id = base.db.Column(base.db.Integer, primary_key=True)
    user_id = base.db.Column(base.db.Integer, base.db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    project_id = base.db.Column(base.db.Integer, base.db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    created_date = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = base.db.relationship('User', backref=base.db.backref('project_permissions', lazy='dynamic', cascade='all, delete-orphan'))
    project = base.db.relationship('Project', backref=base.db.backref('user_permissions', lazy='dynamic'))
    
    def __repr__(self):
        return f'<UserProjectPermission user_id={self.user_id} project_id={self.project_id}>'


class UserLocationPermission(base.db.Model):
    """
    UserLocationPermission model to manage location access for Project Managers
    Links users to specific locations they are allowed to view
    """
    __tablename__ = 'user_location_permissions'
    
    id = base.db.Column(base.db.Integer, primary_key=True)
    user_id = base.db.Column(base.db.Integer, base.db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    location_name = base.db.Column(base.db.String(200), nullable=False)
    created_date = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = base.db.relationship('User', backref=base.db.backref('location_permissions', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<UserLocationPermission user_id={self.user_id} location={self.location_name}>'