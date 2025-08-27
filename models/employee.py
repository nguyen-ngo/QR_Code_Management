"""
Employee Model for QR Attendance Management System
=================================================

Employee model to manage employee data from the external employee table.
This model interfaces with the existing employee table structure.
"""

from datetime import datetime
from . import base

class Employee(base.db.Model):
    """
    Employee model to manage employee records
    Maps to existing employee table structure
    """
    __tablename__ = 'employee'
    
    # Map to existing table structure from employee.sql
    index = base.db.Column('index', base.db.BigInteger, primary_key=True, autoincrement=True)
    id = base.db.Column('id', base.db.BigInteger, nullable=False, unique=True)
    firstName = base.db.Column('firstName', base.db.String(50), nullable=False)
    lastName = base.db.Column('lastName', base.db.String(50), nullable=False)
    title = base.db.Column('title', base.db.String(20), nullable=True)
    contractId = base.db.Column('contractId', base.db.BigInteger, nullable=False, default=1)
    
    def __repr__(self):
        return f'<Employee {self.firstName} {self.lastName} (ID: {self.id})>'
    
    @property
    def full_name(self):
        """Get employee's full name"""
        return f"{self.firstName} {self.lastName}"
    
    @property
    def display_title(self):
        """Get formatted title for display"""
        return self.title if self.title else "No Title"
    
    @classmethod
    def get_by_employee_id(cls, employee_id):
        """Get employee by their ID (not primary key index)"""
        return cls.query.filter_by(id=employee_id).first()
    
    @classmethod
    def search_employees(cls, search_term):
        """Search employees by name, ID, or title"""
        if not search_term:
            return cls.query.all()
        
        search_pattern = f"%{search_term}%"
        return cls.query.filter(
            base.db.or_(
                cls.firstName.like(search_pattern),
                cls.lastName.like(search_pattern),
                cls.title.like(search_pattern),
                cls.id.like(search_pattern)
            )
        ).all()
    
    def to_dict(self):
        """Convert employee to dictionary for JSON serialization"""
        return {
            'index': self.index,
            'id': self.id,
            'firstName': self.firstName,
            'lastName': self.lastName,
            'full_name': self.full_name,
            'title': self.title,
            'display_title': self.display_title,
            'contractId': self.contractId
        }