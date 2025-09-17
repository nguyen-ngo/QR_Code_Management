"""
Time Attendance Model for QR Attendance Management System
=========================================================

TimeAttendance model to manage imported time attendance data from Excel files.
This model is designed to store attendance data imported from external sources.
"""

from datetime import datetime
from . import base

class TimeAttendance(base.db.Model):
    """
    Time Attendance model to manage imported attendance records from Excel files
    """
    __tablename__ = 'time_attendance'
    
    # Primary key
    id = base.db.Column(base.db.Integer, primary_key=True, autoincrement=True)
    
    # Employee identification
    employee_id = base.db.Column(base.db.String(50), nullable=False, index=True)
    employee_name = base.db.Column(base.db.String(200), nullable=False)
    
    # Platform and device information
    platform = base.db.Column(base.db.String(200), nullable=True)
    
    # Date and time information
    attendance_date = base.db.Column(base.db.Date, nullable=False, index=True)
    attendance_time = base.db.Column(base.db.Time, nullable=False)
    
    # Location information
    location_name = base.db.Column(base.db.String(200), nullable=False)
    
    # Action and event details
    action_description = base.db.Column(base.db.String(100), nullable=False)
    event_description = base.db.Column(base.db.Text, nullable=True)
    recorded_address = base.db.Column(base.db.Text, nullable=True)
    
    # Import tracking
    import_batch_id = base.db.Column(base.db.String(36), nullable=True, index=True)
    import_date = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    import_source = base.db.Column(base.db.String(100), nullable=True)
    
    # Audit fields
    created_by = base.db.Column(base.db.Integer, base.db.ForeignKey('users.id'), nullable=True)
    created_date = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    updated_date = base.db.Column(base.db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TimeAttendance {self.employee_id} - {self.employee_name} at {self.location_name} on {self.attendance_date}>'
    
    @property
    def full_datetime(self):
        """Get combined datetime from date and time"""
        return datetime.combine(self.attendance_date, self.attendance_time)
    
    @property
    def formatted_datetime(self):
        """Get formatted datetime string for display"""
        return self.full_datetime.strftime('%Y-%m-%d %H:%M:%S')
    
    @classmethod
    def get_by_employee_id(cls, employee_id, start_date=None, end_date=None):
        """Get attendance records by employee ID with optional date range"""
        query = cls.query.filter_by(employee_id=employee_id)
        
        if start_date:
            query = query.filter(cls.attendance_date >= start_date)
        if end_date:
            query = query.filter(cls.attendance_date <= end_date)
            
        return query.order_by(cls.attendance_date.desc(), cls.attendance_time.desc()).all()
    
    @classmethod
    def get_by_location(cls, location_name, start_date=None, end_date=None):
        """Get attendance records by location with optional date range"""
        query = cls.query.filter_by(location_name=location_name)
        
        if start_date:
            query = query.filter(cls.attendance_date >= start_date)
        if end_date:
            query = query.filter(cls.attendance_date <= end_date)
            
        return query.order_by(cls.attendance_date.desc(), cls.attendance_time.desc()).all()
    
    @classmethod
    def get_by_import_batch(cls, batch_id):
        """Get all records from a specific import batch"""
        return cls.query.filter_by(import_batch_id=batch_id).order_by(
            cls.attendance_date.desc(), cls.attendance_time.desc()
        ).all()
    
    @classmethod
    def get_unique_employees(cls):
        """Get list of unique employees from time attendance records"""
        return base.db.session.query(
            cls.employee_id, 
            cls.employee_name
        ).distinct().order_by(cls.employee_name).all()
    
    @classmethod
    def get_unique_locations(cls):
        """Get list of unique locations from time attendance records"""
        return base.db.session.query(cls.location_name).distinct().order_by(cls.location_name).all()
    
    def to_dict(self):
        """Convert record to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'platform': self.platform,
            'attendance_date': self.attendance_date.isoformat() if self.attendance_date else None,
            'attendance_time': self.attendance_time.isoformat() if self.attendance_time else None,
            'formatted_datetime': self.formatted_datetime,
            'location_name': self.location_name,
            'action_description': self.action_description,
            'event_description': self.event_description,
            'recorded_address': self.recorded_address,
            'import_batch_id': self.import_batch_id,
            'import_date': self.import_date.isoformat() if self.import_date else None,
            'import_source': self.import_source,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None
        }