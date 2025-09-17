"""
Models package for QR Attendance Management System
==================================================

This package contains all SQLAlchemy models split from app.py for better organization.
All models maintain backward compatibility and existing functionality.
"""

from . import base

def set_db(database):
    """Set the database instance for all models"""
    base.db = database
    
    # Now import all models (they will use base.db)
    from .user import User
    from .qrcode import QRCode, QRCodeStyle
    from .project import Project
    from .attendance import AttendanceData
    from .employee import Employee
    from .time_attendance import TimeAttendance

    return User, QRCode, QRCodeStyle, Project, AttendanceData, Employee, TimeAttendance