"""
routes/admin.py
===============
Admin panel and log management routes.

Routes: /admin/logs, /admin/health/google-maps, /api/logs/*
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify
from datetime import datetime, timedelta
import json, math

from extensions import db, logger_handler
from sqlalchemy import text
from utils.geocoding import gmaps_client
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import url_for, admin_required, login_required

bp = Blueprint('admin', __name__)

def _get_models():
    """Return model classes from the current app context."""
    from flask import current_app
    return current_app.config['_models']


@bp.route('/admin/logs', endpoint='admin_logs')
@admin_required
def admin_logs():
    """Admin logging dashboard"""
    try:
        # Get log statistics for the last 7 days
        stats = logger_handler.get_log_statistics(days=7)
        return render_template('admin_logs.html', log_stats=stats)
    except Exception as e:
        logger_handler.log_database_error('admin_logs_load', e)
        flash('Error loading log statistics.', 'error')
        return redirect(url_for('dashboard'))

def check_google_maps_health():
    """Check if Google Maps services are working properly"""
    try:
        if not gmaps_client:
            return False, "Google Maps client not initialized"
        
        # Test with a known address
        test_result = gmaps_client.geocode("1600 Amphitheatre Parkway, Mountain View, CA")
        
        if test_result:
            return True, "Google Maps services are operational"
        else:
            return False, "Google Maps API not returning results"
            
    except Exception as e:
        return False, f"Google Maps health check failed: {str(e)}"

# Optional: Add health check route
@bp.route('/admin/health/google-maps', endpoint='google_maps_health')
@admin_required
def google_maps_health():
    """Admin route to check Google Maps service health"""
    is_healthy, message = check_google_maps_health()
    
    return jsonify({
        'healthy': is_healthy,
        'message': message,
        'service': 'Google Maps',
        'fallback_available': True,
        'timestamp': datetime.now().isoformat()
    })

# API endpoints for logging data (admin only)
@bp.route('/api/logs/recent', endpoint='api_recent_logs')
@admin_required
def api_recent_logs():
    """API endpoint to get recent log entries with full details and pagination support"""
    try:
        days = request.args.get('days', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        category = request.args.get('category', '')
        severity = request.args.get('severity', '')
        search = request.args.get('search', '')

        print(f"📊 API request - Days: {days}, Limit: {limit}, Page: {page}")
        print(f"📊 Filters - Category: {category}, Severity: {severity}, Search: {search}")

        cutoff_date = datetime.now() - timedelta(days=days)

        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Build the base SQL query with filters
        base_sql = """
        SELECT 
            event_id,
            event_type, 
            event_category, 
            event_description, 
            event_data,
            severity_level, 
            created_timestamp, 
            username, 
            user_id,
            ip_address
        FROM log_events 
        WHERE created_timestamp >= :cutoff_date
        """

        count_sql = """
        SELECT COUNT(*) as total_count
        FROM log_events 
        WHERE created_timestamp >= :cutoff_date
        """

        params = {'cutoff_date': cutoff_date}

        # Add category filter
        if category:
            base_sql += " AND event_category = :category"
            count_sql += " AND event_category = :category"
            params['category'] = category

        # Add severity filter
        if severity:
            base_sql += " AND severity_level = :severity"
            count_sql += " AND severity_level = :severity"
            params['severity'] = severity

        # Add search filter
        if search:
            search_condition = " AND (event_type LIKE :search OR event_description LIKE :search OR username LIKE :search)"
            base_sql += search_condition
            count_sql += search_condition
            params['search'] = f'%{search}%'

        # Get total count first
        count_result = db.session.execute(text(count_sql), params).fetchone()
        total_count = count_result.total_count if count_result else 0

        # Add ordering, limit and offset to main query
        base_sql += " ORDER BY created_timestamp DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset

        # Execute main query
        result = db.session.execute(text(base_sql), params).fetchall()

        logs = []
        for row in result:
            # Parse event_data if it's JSON
            event_data = None
            if row.event_data:
                try:
                    event_data = json.loads(row.event_data) if isinstance(row.event_data, str) else row.event_data
                except (json.JSONDecodeError, TypeError):
                    event_data = row.event_data

            logs.append({
                'event_id': row.event_id,
                'event_type': row.event_type,
                'event_category': row.event_category,
                'description': row.event_description,
                'event_data': event_data,
                'severity': row.severity_level,
                'timestamp': row.created_timestamp.isoformat(),
                'username': row.username or 'System',
                'user_id': row.user_id,
                'ip_address': row.ip_address or '-'
            })

        print(f"📊 Returning {len(logs)} logs out of {total_count} total")

        return jsonify({
            'success': True,
            'logs': logs,
            'total': total_count,
            'page': page,
            'limit': limit,
            'total_pages': math.ceil(total_count / limit) if total_count > 0 else 0,
            'has_next': offset + limit < total_count,
            'has_prev': page > 1
        })

    except Exception as e:
        logger_handler.log_database_error('api_recent_logs', e)
        print(f"Error in api_recent_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch recent logs: {str(e)}'
        }), 500

@bp.route('/api/logs/stats', endpoint='api_log_stats')
@admin_required
def api_log_stats():
    """API endpoint to get logging statistics"""
    try:
        days = request.args.get('days', 7, type=int)
        print(f"📊 Getting log statistics for last {days} days")

        # Get statistics from logger handler
        stats = logger_handler.get_log_statistics(days=days)
        print(f"📈 Retrieved stats: {stats}")

        # Ensure all expected keys exist with updated categories
        expected_stats = {
            'total_events': stats.get('total_events', 0),
            'security_events': stats.get('security_events', 0),
            'authentication_events': stats.get('authentication_events', 0),
            'qr_management_events': stats.get('qr_management_events', 0),
            'database_errors': stats.get('database_errors', 0),
            'application_events': stats.get('application_events', 0),
            'system_events': stats.get('system_events', 0)
        }

        return jsonify({
            'success': True,
            'stats': expected_stats,
            'days': days,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger_handler.log_database_error('api_log_stats', e)
        print(f"❌ Error in api_log_stats: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch log statistics: {str(e)}',
            'stats': {
                'total_events': 0,
                'security_events': 0,
                'authentication_events': 0,
                'qr_management_events': 0,
                'database_errors': 0,
                'application_events': 0,
                'system_events': 0
            }
        }), 500

@bp.route('/api/logs/cleanup', methods=['POST'], endpoint='api_cleanup_logs')
@admin_required
def api_cleanup_logs():
    """API endpoint to cleanup old log entries"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            print("❌ No JSON data provided")
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400

        days_to_keep = data.get('days_to_keep', 90)
        print(f"🧹 Cleanup request: keep last {days_to_keep} days")

        # Validate input
        if not isinstance(days_to_keep, int) or days_to_keep < 7:
            print(f"❌ Invalid days_to_keep: {days_to_keep}")
            return jsonify({
                'success': False,
                'error': 'days_to_keep must be an integer >= 7'
            }), 400

        if days_to_keep > 365:
            print(f"❌ days_to_keep too large: {days_to_keep}")
            return jsonify({
                'success': False,
                'error': 'days_to_keep cannot exceed 365 days'
            }), 400

        # Perform cleanup using logger handler
        deleted_count = logger_handler.cleanup_old_logs(days_to_keep=days_to_keep)

        admin_username = session.get('username', 'unknown')
        print(f"✅ Cleanup completed by {admin_username}: {deleted_count} records deleted")

        # Log the admin action
        logger_handler.log_security_event(
            event_type="admin_log_cleanup",
            description=f"Admin {admin_username} performed log cleanup: {deleted_count} entries removed (keeping last {days_to_keep} days)",
            severity="HIGH",
            additional_data={
                'admin_user': admin_username,
                'days_to_keep': days_to_keep,
                'deleted_count': deleted_count,
                'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            }
        )

        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'days_to_keep': days_to_keep,
            'message': f'Successfully cleaned up {deleted_count} old log entries (keeping last {days_to_keep} days)',
            'performed_by': admin_username,
            'performed_at': datetime.now().isoformat()
        })

    except Exception as e:
        logger_handler.log_database_error('api_cleanup_logs', e)
        print(f"❌ Error in api_cleanup_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to cleanup old logs: {str(e)}'
        }), 500

@bp.route('/api/logs/clear', methods=['POST'], endpoint='api_clear_logs')
@admin_required
def api_clear_logs():
    """API endpoint to clear ALL log entries"""
    try:
        admin_username = session.get('username', 'unknown')
        print(f"🧹 Clear logs request by admin: {admin_username}")

        # Count existing logs before deletion
        try:
            count_sql = "SELECT COUNT(*) as total_logs FROM log_events"
            count_result = db.session.execute(text(count_sql)).fetchone()
            total_logs = count_result.total_logs if count_result else 0

            print(f"📊 Total logs to be cleared: {total_logs}")

            if total_logs == 0:
                print("✅ No logs found to clear")
                return jsonify({
                    'success': True,
                    'deleted_count': 0,
                    'message': 'No logs found to clear'
                })

        except Exception as count_error:
            print(f"⚠️ Error counting logs: {count_error}")
            total_logs = 0

        # Perform the clear operation
        try:
            clear_sql = "DELETE FROM log_events"
            result = db.session.execute(text(clear_sql))
            deleted_count = result.rowcount
            db.session.commit()

            print(f"🗑️ Successfully cleared {deleted_count} log entries")

            # Log the clear operation (this will be the first entry in the new log)
            logger_handler.log_security_event(
                event_type="admin_log_clear",
                description=f"Admin {admin_username} cleared all log entries: {deleted_count} records deleted",
                severity="HIGH",
                additional_data={
                    'admin_user': admin_username,
                    'deleted_count': deleted_count,
                    'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                }
            )

            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Successfully cleared {deleted_count} log entries',
                'performed_by': admin_username,
                'performed_at': datetime.now().isoformat()
            })

        except Exception as delete_error:
            print(f"❌ Error during log clearing: {delete_error}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Failed to clear logs: {str(delete_error)}'
            }), 500

    except Exception as e:
        logger_handler.log_database_error('api_clear_logs', e)
        print(f"❌ Error in api_clear_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear logs: {str(e)}'
        }), 500

@bp.route('/api/logs/clear-old', methods=['POST'], endpoint='api_clear_old_logs')
@admin_required
def api_clear_old_logs():
    """API endpoint to clear log entries older than specified days"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            print("❌ No JSON data provided")
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400

        days_threshold = data.get('days_threshold', 90)
        admin_username = session.get('username', 'unknown')
        print(f"🧹 Clear old logs request by admin: {admin_username}, threshold: {days_threshold} days")

        # Validate input
        if not isinstance(days_threshold, int) or days_threshold not in [30, 60, 90]:
            print(f"❌ Invalid days_threshold: {days_threshold}")
            return jsonify({
                'success': False,
                'error': 'days_threshold must be 30, 60, or 90'
            }), 400

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_threshold)

        # Count existing logs before deletion
        try:
            count_sql = "SELECT COUNT(*) as total_logs FROM log_events WHERE created_timestamp < :cutoff_date"
            count_result = db.session.execute(text(count_sql), {'cutoff_date': cutoff_date}).fetchone()
            total_logs = count_result.total_logs if count_result else 0

            print(f"📊 Total logs older than {days_threshold} days to be cleared: {total_logs}")

            if total_logs == 0:
                print("✅ No old logs found to clear")
                return jsonify({
                    'success': True,
                    'deleted_count': 0,
                    'message': f'No logs older than {days_threshold} days found to clear'
                })

        except Exception as count_error:
            print(f"⚠️ Error counting old logs: {count_error}")
            total_logs = 0

        # Perform the clear operation
        try:
            clear_sql = "DELETE FROM log_events WHERE created_timestamp < :cutoff_date"
            result = db.session.execute(text(clear_sql), {'cutoff_date': cutoff_date})
            deleted_count = result.rowcount
            db.session.commit()

            print(f"🗑️ Successfully cleared {deleted_count} log entries older than {days_threshold} days")

            # Log the clear operation
            logger_handler.log_security_event(
                event_type="admin_clear_old_logs",
                description=f"Admin {admin_username} cleared {deleted_count} log entries older than {days_threshold} days",
                severity="HIGH",
                additional_data={
                    'admin_user': admin_username,
                    'days_threshold': days_threshold,
                    'deleted_count': deleted_count,
                    'cutoff_date': cutoff_date.isoformat(),
                    'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                }
            )

            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'days_threshold': days_threshold,
                'message': f'Successfully cleared {deleted_count} log entries older than {days_threshold} days',
                'performed_by': admin_username,
                'performed_at': datetime.now().isoformat()
            })

        except Exception as delete_error:
            print(f"❌ Error during old log clearing: {delete_error}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Failed to clear old logs: {str(delete_error)}'
            }), 500

    except Exception as e:
        logger_handler.log_database_error('api_clear_old_logs', e)
        print(f"❌ Error in api_clear_old_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear old logs: {str(e)}'
        }), 500

@bp.route('/api/logs/export', endpoint='api_export_logs')
@admin_required
def api_export_logs():
    """API endpoint to export log entries"""
    try:
        days = request.args.get('days', 7, type=int)
        category = request.args.get('category', '')
        severity = request.args.get('severity', '')
        search = request.args.get('search', '')

        admin_username = session.get('username', 'unknown')
        print(f"📊 Export logs request by admin: {admin_username}")

        cutoff_date = datetime.now() - timedelta(days=days)

        # Build the SQL query with filters
        base_sql = """
        SELECT 
            event_id,
            event_type, 
            event_category, 
            event_description, 
            event_data,
            severity_level, 
            created_timestamp, 
            username, 
            user_id,
            ip_address
        FROM log_events 
        WHERE created_timestamp >= :cutoff_date
        """

        params = {'cutoff_date': cutoff_date}

        # Add category filter
        if category:
            base_sql += " AND event_category = :category"
            params['category'] = category

        # Add severity filter
        if severity:
            base_sql += " AND severity_level = :severity"
            params['severity'] = severity

        # Add search filter
        if search:
            base_sql += " AND (event_type LIKE :search OR event_description LIKE :search OR username LIKE :search)"
            params['search'] = f'%{search}%'

        base_sql += " ORDER BY created_timestamp DESC"

        result = db.session.execute(text(base_sql), params).fetchall()

        logs = []
        for row in result:
            # Parse event_data if it's JSON
            event_data = None
            if row.event_data:
                try:
                    event_data = json.loads(row.event_data) if isinstance(row.event_data, str) else row.event_data
                except (json.JSONDecodeError, TypeError):
                    event_data = row.event_data

            logs.append({
                'event_id': row.event_id,
                'event_type': row.event_type,
                'event_category': row.event_category,
                'description': row.event_description,
                'event_data': event_data,
                'severity': row.severity_level,
                'timestamp': row.created_timestamp.isoformat(),
                'username': row.username or 'System',
                'user_id': row.user_id,
                'ip_address': row.ip_address or '-'
            })

        # Log the export operation
        logger_handler.log_security_event(
            event_type="admin_log_export",
            description=f"Admin {admin_username} exported {len(logs)} log entries (last {days} days)",
            severity="MEDIUM",
            additional_data={
                'admin_user': admin_username,
                'exported_count': len(logs),
                'days_exported': days,
                'filters': {
                    'category': category,
                    'severity': severity,
                    'search': search
                },
                'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            }
        )

        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs),
            'filters_applied': {
                'days': days,
                'category': category,
                'severity': severity,
                'search': search
            }
        })

    except Exception as e:
        logger_handler.log_database_error('api_export_logs', e)
        print(f"❌ Error in api_export_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to export logs: {str(e)}'
        }), 500

# PROJECT MANAGEMENT ROUTES