"""
QRCode and QRCodeStyle Models for QR Attendance Management System
================================================================

QRCode models to manage QR code records and metadata with customization options.
Extracted from app.py for better code organization.
"""

from datetime import datetime
from . import base

class QRCode(base.db.Model):
    """
    Enhanced QR Code model to manage QR code records and metadata with address coordinates
    """
    __tablename__ = 'qr_codes'
    
    id = base.db.Column(base.db.Integer, primary_key=True)
    name = base.db.Column(base.db.String(100), nullable=False)
    location = base.db.Column(base.db.String(100), nullable=False)
    location_address = base.db.Column(base.db.Text, nullable=False)
    location_event = base.db.Column(base.db.String(200), nullable=False)
    qr_code_image = base.db.Column(base.db.Text, nullable=False)  # Base64 encoded image
    created_by = base.db.Column(base.db.Integer, base.db.ForeignKey('users.id'), nullable=True)
    created_date = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    active_status = base.db.Column(base.db.Boolean, default=True)
    qr_url = base.db.Column(base.db.String(255), unique=True, nullable=True)
    # Address Coordinates Fields
    address_latitude = base.db.Column(base.db.Float, nullable=True)
    address_longitude = base.db.Column(base.db.Float, nullable=True)
    coordinate_accuracy = base.db.Column(base.db.String(50), nullable=True, default='geocoded')
    coordinates_updated_date = base.db.Column(base.db.DateTime, nullable=True)
    project_id = base.db.Column(base.db.Integer, base.db.ForeignKey('projects.id'), nullable=True)
    # QR Code Customization fields
    fill_color = base.db.Column(base.db.String(7), default="#000000")  # Hex color
    back_color = base.db.Column(base.db.String(7), default="#FFFFFF")  # Background color
    box_size = base.db.Column(base.db.Integer, default=10)
    border = base.db.Column(base.db.Integer, default=4)
    error_correction = base.db.Column(base.db.String(1), default='L')
    style_id = base.db.Column(base.db.Integer, base.db.ForeignKey('qr_code_styles.id'), nullable=True)
    
    # Relationship to style
    style = base.db.relationship('QRCodeStyle', backref='qr_codes')

    @property
    def has_coordinates(self):
        """Check if this QR code has address coordinates"""
        return self.address_latitude is not None and self.address_longitude is not None
    
    @property
    def coordinates_display(self):
        """Get formatted coordinates for display"""
        if self.has_coordinates:
            return f"{self.address_latitude:.10f}, {self.address_longitude:.10f}"
        return "Coordinates not available"

    def update_coordinates(self, latitude, longitude, accuracy='geocoded'):
        """Update the address coordinates for this QR code"""
        self.address_latitude = latitude
        self.address_longitude = longitude
        self.coordinate_accuracy = accuracy
        self.coordinates_updated_date = datetime.utcnow()


class QRCodeStyle(base.db.Model):
    """QR Code customization styles"""
    __tablename__ = 'qr_code_styles'
    
    id = base.db.Column(base.db.Integer, primary_key=True)
    name = base.db.Column(base.db.String(100), nullable=False)  # Style name
    fill_color = base.db.Column(base.db.String(7), default="#000000")  # Hex color for QR modules
    back_color = base.db.Column(base.db.String(7), default="#FFFFFF")  # Hex color for background
    box_size = base.db.Column(base.db.Integer, default=10)  # Size of each QR module
    border = base.db.Column(base.db.Integer, default=4)  # Border size
    error_correction = base.db.Column(base.db.String(1), default='L')  # L, M, Q, H
    is_default = base.db.Column(base.db.Boolean, default=False)
    created_at = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    created_by = base.db.Column(base.db.Integer, base.db.ForeignKey('users.id'))
    
    def __repr__(self):
        return f'<QRCodeStyle {self.name}>'