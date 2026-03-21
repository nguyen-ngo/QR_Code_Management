"""
utils/template_helpers.py
=========================
Template utility functions injected into Jinja2 via context processors.

Extracted from create_app() in app.py so they can be independently
imported, tested, and reused.
"""

from datetime import datetime
from sqlalchemy import text as sa_text

from extensions import db, logger_handler


def get_employee_name(employee_id):
    """Return 'Lastname, Firstname' for a given employee ID.
    Falls back to 'Employee <id>' if not found or on error.
    """
    try:
        result = db.session.execute(sa_text("""
            SELECT CONCAT(firstName, ' ', lastName) as full_name
            FROM employee
            WHERE id = :employee_id
        """), {'employee_id': employee_id})
        row = result.fetchone()
        return row[0] if row else f"Employee {employee_id}"
    except Exception as e:
        print(f"⚠️ Error getting employee name for ID {employee_id}: {e}")
        return f"Employee {employee_id}"


def get_qr_code_checkin_count(qr_code_id):
    """Return total number of check-ins for a given QR code ID."""
    from models.attendance import AttendanceData
    try:
        return AttendanceData.query.filter_by(qr_code_id=qr_code_id).count()
    except Exception as e:
        logger_handler.logger.error(
            f"Error getting check-ins count for QR {qr_code_id}: {e}"
        )
        return 0


def format_hours(hours):
    """Format a decimal hours value to 2 decimal places."""
    return f"{hours:.2f}" if hours else "0.00"


def register_template_helpers(app):
    """
    Register all template helper context processors on the given Flask app.
    Call this once inside create_app() after the app is configured.
    """
    from working_hours_calculator import (
        convert_minutes_to_base100, round_base100_hours
    )

    @app.context_processor
    def inject_payroll_utils():
        """Inject payroll utility functions into all templates."""
        return {
            'convert_minutes_to_base100': convert_minutes_to_base100,
            'round_base100_hours':        round_base100_hours,
            'get_employee_name':          get_employee_name,
            'format_hours':               format_hours,
        }

    @app.context_processor
    def inject_dashboard_utils():
        """Inject dashboard utility functions into all templates."""
        return {
            'now':                      datetime.utcnow,
            'get_qr_code_checkin_count': get_qr_code_checkin_count,
        }
