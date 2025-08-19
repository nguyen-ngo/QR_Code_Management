"""
Attendance Model for QR Attendance Management System
===================================================

AttendanceData model for tracking attendance records with location support.
Extracted from app.py for better code organization.
"""

from datetime import datetime
from . import base

class AttendanceData(base.db.Model):
    """Enhanced attendance tracking model with location support"""
    __tablename__ = 'attendance_data'
    
    # Existing fields
    id = base.db.Column(base.db.Integer, primary_key=True)
    qr_code_id = base.db.Column(base.db.Integer, base.db.ForeignKey('qr_codes.id', ondelete='CASCADE'), nullable=False)
    employee_id = base.db.Column(base.db.String(50), nullable=False)
    check_in_date = base.db.Column(base.db.Date, nullable=False, default=datetime.today)
    check_in_time = base.db.Column(base.db.Time, nullable=False, default=datetime.now().time)
    device_info = base.db.Column(base.db.String(200))
    user_agent = base.db.Column(base.db.Text)
    ip_address = base.db.Column(base.db.String(45))
    location_name = base.db.Column(base.db.String(100), nullable=False)
    status = base.db.Column(base.db.String(20), default='present')
    created_timestamp = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    updated_timestamp = base.db.Column(base.db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    latitude = base.db.Column(base.db.Float, nullable=True)
    longitude = base.db.Column(base.db.Float, nullable=True)
    accuracy = base.db.Column(base.db.Float, nullable=True)
    location_accuracy = base.db.Column(base.db.Float, nullable=True)
    altitude = base.db.Column(base.db.Float, nullable=True)
    location_source = base.db.Column(base.db.String(50), default='manual')
    address = base.db.Column(base.db.String(500), nullable=True)
    
    # Relationships
    qr_code = base.db.relationship('QRCode', backref=base.db.backref('attendance_records', lazy='dynamic'))
    
    def __repr__(self):
        return f'<AttendanceData {self.employee_id} at {self.location_name} on {self.check_in_date}>'
    
    @property
    def has_location_data(self):
        """Check if this record has GPS coordinates"""
        return self.latitude is not None and self.longitude is not None
    
    @property
    def location_accuracy_level(self):
        """Get human-readable accuracy level"""
        if not self.accuracy:
            return 'unknown'
        elif self.accuracy <= 5:
            return 'high'
        elif self.accuracy <= 20:
            return 'medium'
        else:
            return 'low'