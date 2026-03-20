"""
app.py
======
Application entry point and factory.

This file is intentionally lean (~130 lines).  All route logic lives in
the Blueprint modules under routes/.  All shared utilities live in utils/.
The db and logger_handler singletons live in extensions.py.

Blueprint registration order matches the original route-definition order
so that url_for() resolution is identical to the original monolithic app.py.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import time as _time

# Load .env BEFORE importing anything that reads env vars
load_dotenv()

from extensions import db, init_logger
from logger_handler import log_database_operations
from models import set_db
from turnstile_utils import turnstile_utils
from db_performance_optimization import initialize_performance_optimizations
from app_performance_middleware import PerformanceMonitor
from utils.helpers import has_admin_privileges


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
from location_logging import *  # noqa: F401,F403 — registers location hooks at module level




def create_app() -> Flask:
    app = Flask(__name__)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')
    app.config['TEMPLATES_AUTO_RELOAD'] = os.environ.get('TEMPLATES_AUTO_RELOAD')

    # Session / cookie configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    app.config['SESSION_COOKIE_HTTPONLY'] = os.environ.get('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
    app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('SESSION_COOKIE_SAMESITE')

    # Photo verification
    app.config['PHOTO_VERIFICATION_ENABLED'] = os.environ.get('ENABLE_PHOTO_VERIFICATION', 'true').lower() == 'true'
    app.config['DISTANCE_THRESHOLD_FOR_VERIFICATION'] = float(os.environ.get('PHOTO_VERIFICATION_DISTANCE_THRESHOLD', '0.3'))
    app.config['VERIFICATION_PHOTO_MAX_SIZE'] = int(os.environ.get('VERIFICATION_PHOTO_MAX_SIZE', str(5 * 1024 * 1024)))

    # ------------------------------------------------------------------
    # Database initialization
    # ------------------------------------------------------------------
    db.init_app(app)

    with app.app_context():
        # Unpack model classes and store on app for shared access
        (User, QRCode, QRCodeStyle, Project, AttendanceData,
         Employee, TimeAttendance, UserProjectPermission,
         UserLocationPermission) = set_db(db)

        app.config['_models'] = {
            'User': User, 'QRCode': QRCode, 'QRCodeStyle': QRCodeStyle,
            'Project': Project, 'AttendanceData': AttendanceData,
            'Employee': Employee, 'TimeAttendance': TimeAttendance,
            'UserProjectPermission': UserProjectPermission,
            'UserLocationPermission': UserLocationPermission,
        }

    # ------------------------------------------------------------------
    # Logger initialization
    # ------------------------------------------------------------------
    init_logger(app, db)

    # ------------------------------------------------------------------
    # Blueprint registration  (url_prefix='' preserves all original URLs)
    # ------------------------------------------------------------------
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.users import bp as users_bp
    from routes.admin import bp as admin_bp
    from routes.projects import bp as projects_bp
    from routes.qr_codes import bp as qr_codes_bp
    from routes.attendance import bp as attendance_bp
    from routes.payroll import bp as payroll_bp
    from routes.statistics import bp as statistics_bp
    from routes.employees import bp as employees_bp
    from routes.time_attendance import bp as time_attendance_bp

    for bp in (auth_bp, dashboard_bp, users_bp, admin_bp, projects_bp,
               qr_codes_bp, attendance_bp, payroll_bp, statistics_bp,
               employees_bp, time_attendance_bp):
        app.register_blueprint(bp)

    # Register location-logging routes (from location_logging.py)
    # Must be called after app is created; uses app, db, logger_handler directly.
    from extensions import logger_handler as _lh
    create_location_logging_routes(app, db, _lh)

    # Patch Jinja2's url_for global so templates also use the compatibility shim
    from utils.helpers import url_for as _compat_url_for
    app.jinja_env.globals['url_for'] = _compat_url_for

    # ------------------------------------------------------------------
    # Template filters (global — must be on app, not blueprints)
    # ------------------------------------------------------------------

    @app.context_processor
    def inject_company_name():
        """Make COMPANY_NAME available to all templates"""
        return {'COMPANY_NAME': os.environ.get('COMPANY_NAME', 'QR Code Management System')}

    @app.context_processor
    def inject_logging_status():
        """Inject logging status into all templates"""
        return {
            'logging_enabled': True,
            'is_admin': has_admin_privileges(session.get('role', ''))
        }

    @app.context_processor
    def inject_turnstile():
        """Inject Turnstile settings into all templates"""
        return {
            'turnstile_enabled': turnstile_utils.is_enabled(),
            'turnstile_site_key': turnstile_utils.get_site_key()
        }

    # Helper functions for context processors
    def get_employee_name(employee_id):
        """Helper function to get employee full name by ID"""
        from sqlalchemy import text as sa_text
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
        """Helper function to get total check-ins count for a QR code"""
        from flask import current_app
        try:
            AttendanceData = current_app.config['_models']['AttendanceData']
            count = AttendanceData.query.filter_by(qr_code_id=qr_code_id).count()
            return count
        except Exception as e:
            from extensions import logger_handler as _lh
            _lh.logger.error(f"Error getting check-ins count for QR {qr_code_id}: {e}")
            return 0

    @app.context_processor
    def inject_payroll_utils():
        """Inject payroll utility functions into templates"""
        from working_hours_calculator import convert_minutes_to_base100, round_base100_hours
        return {
            'convert_minutes_to_base100': convert_minutes_to_base100,
            'round_base100_hours': round_base100_hours,
            'get_employee_name': get_employee_name,
            'format_hours': lambda hours: f"{hours:.2f}" if hours else "0.00"
        }

    @app.context_processor
    def inject_dashboard_utils():
        """Inject dashboard utility functions into templates"""
        return {
            'now': datetime.utcnow,
            'get_qr_code_checkin_count': get_qr_code_checkin_count
        }

    @app.template_filter('strftime')
    def strftime_filter(value, format='%m/%d/%Y'):
        """Format datetime/date/string as strftime"""
        if isinstance(value, str):
            if value.lower() == 'now':
                return datetime.now().strftime(format)
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime(format)
            except (ValueError, TypeError):
                return value
        if hasattr(value, 'strftime'):
            return value.strftime(format)
        return str(value)

    @app.template_filter('days_since')
    def days_since_filter(value):
        """Calculate days since a given date"""
        if not value:
            return 0
        now = datetime.utcnow()
        return (now - value).days

    @app.template_filter('time_ago')
    def time_ago_filter(value):
        """Human readable time ago"""
        if not value:
            return 'Never'
        now = datetime.utcnow()
        diff = now - value
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"

    # ------------------------------------------------------------------
    # Request / response hooks
    # ------------------------------------------------------------------

    @app.before_request
    def log_request_info():
        """Log request information for security monitoring"""
        if (request.endpoint and
                (request.endpoint.startswith('static') or
                 request.path.startswith('/api/logs'))):
            return

        from extensions import logger_handler as lh
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        suspicious_patterns = [
            'sqlmap', 'nikto', 'nmap', 'dirb', 'dirbuster',
            'wget', 'curl.*bot', 'scanner', 'exploit'
        ]
        if any(pattern in user_agent.lower() for pattern in suspicious_patterns):
            lh.log_security_event(
                event_type="suspicious_user_agent",
                description=f"Suspicious user agent detected: {user_agent[:200]}",
                severity="HIGH",
                additional_data={'user_agent': user_agent, 'ip_address': ip_address}
            )

    @app.after_request
    def log_response_info(response):
        """Log response information for performance monitoring"""
        from extensions import logger_handler as lh
        if request.endpoint and request.endpoint.startswith('static'):
            return response
        if hasattr(request, 'start_time'):
            duration = _time.time() - request.start_time
            if duration > 5.0:
                lh.logger.warning(f"Slow request: {request.path} took {duration:.2f} seconds")
        if response.status_code >= 400:
            lh.logger.warning(
                f"Error response: {response.status_code} for {request.path} "
                f"by user {session.get('username', 'anonymous')}"
            )
        return response

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------

    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors with user-friendly page"""
        if app.debug:
            return None
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Server Error</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 100px;">
            <h1>🔧 Something went wrong</h1>
            <p>We're working to fix this issue. Please try again later.</p>
            <a href="/" style="color: #2563eb;">← Back to Home</a>
        </body>
        </html>
        ''', 500

    @app.errorhandler(404)
    def not_found(error):
        """Handle page not found errors"""
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Page Not Found</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 100px;">
            <h1>🔍 Page Not Found</h1>
            <p>The page you're looking for doesn't exist.</p>
            <a href="/" style="color: #2563eb;">← Back to Home</a>
        </body>
        </html>
        ''', 404

    return app


# ---------------------------------------------------------------------------
# Database initialization helpers (called at startup)
# ---------------------------------------------------------------------------

@log_database_operations('database_initialization')
def create_tables():
    """Create database tables and default admin user with logging"""
    from extensions import db as _db, logger_handler as lh
    try:
        _db.create_all()
        from flask import current_app
        User = current_app.config['_models']['User']
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
            admin = User(
                full_name='System Administrator',
                email='admin@example.com',
                username='admin',
                role='admin'
            )
            admin.set_password(default_password)
            _db.session.add(admin)
            _db.session.commit()
            if default_password == 'admin123':
                print("⚠️  WARNING: Default admin password 'admin123' is in use. "
                      "Set DEFAULT_ADMIN_PASSWORD in your .env file before going to production.")
                lh.logger.warning(
                    "Default admin user created with insecure default password. "
                    "Set DEFAULT_ADMIN_PASSWORD environment variable."
                )
            else:
                lh.logger.info("Default admin user created during initialization")
        lh._create_log_table()
    except Exception as e:
        lh.log_database_error('database_initialization', e)
        raise


def update_existing_qr_codes():
    """Update existing QR codes with URLs and regenerate QR images with logging"""
    from extensions import db as _db, logger_handler as lh
    from utils.helpers import generate_qr_code, get_qr_styling, generate_qr_url
    from flask import current_app, request
    try:
        QRCode = current_app.config['_models']['QRCode']
        qr_codes = QRCode.query.filter_by(active_status=True).all()
        updated_count = 0
        for qr_code in qr_codes:
            if not qr_code.qr_url or not qr_code.qr_code_image:
                try:
                    if not qr_code.qr_url:
                        qr_code.qr_url = generate_qr_url(qr_code.name, qr_code.id)
                    if not qr_code.qr_code_image:
                        qr_data = f"{request.url_root}qr/{qr_code.qr_url}"
                        styling = get_qr_styling(qr_code)
                        qr_code.qr_code_image = generate_qr_code(
                            data=qr_data,
                            fill_color=styling['fill_color'],
                            back_color=styling['back_color'],
                            box_size=styling['box_size'],
                            border=styling['border'],
                            error_correction=styling['error_correction']
                        )
                    updated_count += 1
                except Exception as e:
                    lh.log_flask_error('qr_code_update_error', f"Failed to update QR code {qr_code.id}: {str(e)}")
                    continue
        if updated_count > 0:
            _db.session.commit()
            lh.logger.info(f"Updated {updated_count} existing QR codes with missing URLs/images")
    except Exception as e:
        lh.log_database_error('update_existing_qr_codes', e)
        print(f"Error updating existing QR codes: {e}")


def log_slow_query_performance(app_instance):
    """Register slow-query monitoring hooks on the given app instance"""
    from extensions import logger_handler as lh

    @app_instance.before_request
    def before_request():
        g.start_time = _time.time()

    @app_instance.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            duration = _time.time() - g.start_time
            if duration > 2.0:
                lh.log_system_event(
                    event_type="slow_query_detected",
                    description=f"Slow request: {request.endpoint} took {duration:.2f}s",
                    severity="WARNING",
                    additional_data={
                        'duration': duration,
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'user': session.get('username', 'anonymous')
                    }
                )
        return response


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        try:
            create_tables()
            log_slow_query_performance(app)

            print("🚀 Initializing performance optimizations...")
            from extensions import logger_handler
            cached_query = initialize_performance_optimizations(app, db, logger_handler)
            performance_monitor = PerformanceMonitor(app, db, logger_handler)

            if cached_query:
                print("✅ Performance optimizations completed successfully")
            else:
                print("⚠️ Performance optimizations completed with warnings")

            logger_handler.logger.info("QR Attendance Management System started successfully")

        except Exception as e:
            print(f"❌ Application startup failed: {e}")
            raise

    app.run(
        debug=os.environ.get('DEBUG'),
        host=os.environ.get('FLASK_HOST'),
        port=os.environ.get('FLASK_PORT'),
        threaded=os.environ.get('THREADED')
    )
