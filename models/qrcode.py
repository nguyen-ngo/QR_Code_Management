"""
QRCode, QRCodeStyle, and QRCodeLocation Models for QR Attendance Management System
===================================================================================

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
    # nullable=True for dynamic QR codes which have no single fixed location/address
    location = base.db.Column(base.db.String(100), nullable=True)
    location_address = base.db.Column(base.db.Text, nullable=True)
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
    # --- ADDED: QR Code Type ---
    # 'standard' = fixed single location (existing behavior, default)
    # 'dynamic'  = employee selects location from a list at scan time
    qr_type = base.db.Column(base.db.String(20), nullable=False, default='standard')

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


# --- ADDED: QRCodeLocation model ---
class QRCodeLocation(base.db.Model):
    """
    Selectable locations for dynamic QR codes.
    Each record represents one location option displayed to the employee at scan time.
    Only relevant when the parent QRCode.qr_type == 'dynamic'.
    """
    __tablename__ = 'qr_code_locations'

    id = base.db.Column(base.db.Integer, primary_key=True)
    qr_code_id = base.db.Column(
        base.db.Integer,
        base.db.ForeignKey('qr_codes.id', ondelete='CASCADE'),
        nullable=False
    )
    location_name = base.db.Column(base.db.String(100), nullable=False)
    location_address = base.db.Column(base.db.Text, nullable=True)
    address_latitude = base.db.Column(base.db.Float, nullable=True)
    address_longitude = base.db.Column(base.db.Float, nullable=True)
    sort_order = base.db.Column(base.db.Integer, default=0, nullable=False)
    active_status = base.db.Column(base.db.Boolean, default=True, nullable=False)
    created_date = base.db.Column(base.db.DateTime, default=datetime.utcnow)

    # Back-reference: qr_code_instance.locations → list of QRCodeLocation rows
    qr_code = base.db.relationship('QRCode', backref='locations')

    def __repr__(self):
        return f'<QRCodeLocation "{self.location_name}" (QR #{self.qr_code_id})>'
