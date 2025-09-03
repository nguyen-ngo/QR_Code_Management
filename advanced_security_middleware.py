# File: advanced_security_middleware.py
# Enhanced security middleware for QR Attendance System

from functools import wraps
from flask import request, session, jsonify, current_app, g
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
import re
from collections import defaultdict, deque
import time
import hmac
import base64
import os

# Try to import cryptography, fallback if not available
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

class SecurityManager:
    """
    Advanced security manager for QR Attendance System
    """
    
    def __init__(self, app=None, db=None, logger_handler=None):
        self.app = app
        self.db = db
        self.logger_handler = logger_handler
        
        # Security tracking
        self.failed_attempts = defaultdict(lambda: deque(maxlen=10))
        self.suspicious_ips = defaultdict(int)
        self.session_tokens = {}
        
        # Security configuration
        self.max_failed_attempts = 5
        self.lockout_duration = 900  # 15 minutes
        self.session_timeout = 3600  # 1 hour
        
        if app:
            self.init_app(app, db, logger_handler)
    
    def init_app(self, app, db, logger_handler):
        """Initialize security manager with Flask app"""
        self.app = app
        self.db = db
        self.logger_handler = logger_handler
        
        # Generate encryption key for sensitive data
        self.setup_encryption()
        
        # Register security middleware
        app.before_request(self.security_check)
        
        # Register security routes
        self.register_security_routes()
    
    def setup_encryption(self):
        """Setup encryption for sensitive data"""
        if HAS_CRYPTOGRAPHY:
            encryption_key = self.app.config.get('ENCRYPTION_KEY')
            if not encryption_key:
                # Generate a new key (should be stored securely in production)
                encryption_key = Fernet.generate_key()
                if self.logger_handler:
                    self.logger_handler.logger.warning(
                        "Generated new encryption key - store this securely!"
                    )
            
            self.cipher = Fernet(encryption_key)
        else:
            self.cipher = None
            if self.logger_handler:
                self.logger_handler.logger.warning(
                    "Cryptography not available - encryption features disabled"
                )
    
    def security_check(self):
        """Comprehensive security check before each request"""
        client_ip = self.get_client_ip()
        
        # Check for suspicious activity
        if self.is_suspicious_request():
            self.log_security_event('suspicious_request', {
                'ip': client_ip,
                'user_agent': request.headers.get('User-Agent', ''),
                'endpoint': request.endpoint,
                'method': request.method
            })
            return jsonify({'error': 'Request blocked for security reasons'}), 403
        
        # Validate session security
        if 'user_id' in session:
            if not self.validate_session_security():
                session.clear()
                return jsonify({'error': 'Session security validation failed'}), 401
        
        # Check for SQL injection attempts
        if self.detect_sql_injection():
            self.log_security_event('sql_injection_attempt', {
                'ip': client_ip,
                'query_params': dict(request.args),
                'form_data': dict(request.form) if request.form else {}
            })
            return jsonify({'error': 'Malicious request detected'}), 403
        
        # Rate limiting for authentication endpoints
        if request.endpoint in ['login', 'register', 'reset_password']:
            if self.is_auth_rate_limited():
                return jsonify({
                    'error': 'Too many attempts, please try again later'
                }), 429
    
    def get_client_ip(self):
        """Get real client IP address"""
        # Check for forwarded headers (in case behind proxy/CDN)
        forwarded_ips = request.headers.getlist('X-Forwarded-For')
        if forwarded_ips:
            return forwarded_ips[0].split(',')[0].strip()
        
        return request.headers.get('X-Real-IP') or request.remote_addr
    
    def is_suspicious_request(self):
        """Detect suspicious request patterns"""
        client_ip = self.get_client_ip()
        user_agent = request.headers.get('User-Agent', '').lower()
        
        # Check for common attack patterns
        suspicious_patterns = [
            r'<script', r'javascript:', r'vbscript:', r'onload=', r'onerror=',
            r'union\s+select', r'drop\s+table', r'insert\s+into',
            r'\.\./\.\./.*etc/passwd', r'cmd\.exe', r'/bin/bash'
        ]
        
        request_data = str(request.args) + str(request.form) + request.path
        
        for pattern in suspicious_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                self.suspicious_ips[client_ip] += 1
                return True
        
        # Check for suspicious user agents
        bot_patterns = ['bot', 'crawler', 'spider', 'scraper', 'scanner']
        if any(pattern in user_agent for pattern in bot_patterns):
            if request.endpoint not in ['static', 'favicon']:
                return True
        
        # Check request frequency (basic rate limiting)
        current_time = time.time()
        if not hasattr(g, 'request_history'):
            g.request_history = deque(maxlen=50)
        
        g.request_history.append(current_time)
        recent_requests = [t for t in g.request_history if current_time - t < 60]
        
        if len(recent_requests) > 30:  # More than 30 requests per minute
            return True
        
        return False
    
    def validate_session_security(self):
        """Validate session security and integrity"""
        try:
            user_id = session.get('user_id')
            session_token = session.get('security_token')
            
            if not user_id or not session_token:
                return False
            
            # Check if session token matches stored token
            stored_token = self.session_tokens.get(user_id)
            if not stored_token or not hmac.compare_digest(session_token, stored_token['token']):
                return False
            
            # Check session timeout
            if time.time() - stored_token['created'] > self.session_timeout:
                del self.session_tokens[user_id]
                return False
            
            # Check if session IP matches (optional security measure)
            if self.app.config.get('STRICT_SESSION_IP', False):
                if stored_token['ip'] != self.get_client_ip():
                    self.log_security_event('session_ip_mismatch', {
                        'user_id': user_id,
                        'original_ip': stored_token['ip'],
                        'current_ip': self.get_client_ip()
                    })
                    return False
            
            return True
            
        except Exception as e:
            if self.logger_handler:
                self.logger_handler.logger.error(f"Session validation error: {e}")
            return False
    
    def detect_sql_injection(self):
        """Detect potential SQL injection attempts"""
        sql_patterns = [
            r"union\s+select", r"drop\s+table", r"insert\s+into",
            r"delete\s+from", r"update\s+set", r"exec\s*\(",
            r"sp_executesql", r"xp_cmdshell", r";\s*--",
            r"'\s*or\s*'", r'"\s*or\s*"', r"1\s*=\s*1"
        ]
        
        # Check all request parameters
        check_data = []
        check_data.extend(request.args.values())
        check_data.extend(request.form.values())
        
        if request.json:
            check_data.extend(str(v) for v in request.json.values() if isinstance(v, (str, int, float)))
        
        for data in check_data:
            data_str = str(data).lower()
            for pattern in sql_patterns:
                if re.search(pattern, data_str, re.IGNORECASE):
                    return True
        
        return False
    
    def is_auth_rate_limited(self):
        """Check if authentication endpoint is rate limited"""
        client_ip = self.get_client_ip()
        current_time = time.time()
        
        # Clean old attempts
        self.failed_attempts[client_ip] = deque([
            attempt for attempt in self.failed_attempts[client_ip]
            if current_time - attempt < 900  # Keep attempts from last 15 minutes
        ], maxlen=10)
        
        return len(self.failed_attempts[client_ip]) >= self.max_failed_attempts
    
    def record_failed_attempt(self, identifier):
        """Record a failed authentication attempt"""
        client_ip = self.get_client_ip()
        current_time = time.time()
        
        self.failed_attempts[client_ip].append(current_time)
        
        self.log_security_event('authentication_failure', {
            'ip': client_ip,
            'identifier': identifier,
            'attempts': len(self.failed_attempts[client_ip])
        })
    
    def create_secure_session(self, user_id):
        """Create a secure session with additional security measures"""
        # Generate secure session token
        session_token = secrets.token_urlsafe(32)
        
        # Store session information
        self.session_tokens[user_id] = {
            'token': session_token,
            'created': time.time(),
            'ip': self.get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')[:200]
        }
        
        # Set session data
        session['security_token'] = session_token
        session['login_time'] = datetime.utcnow().isoformat()
        
        # Clear any failed attempts for this IP
        client_ip = self.get_client_ip()
        if client_ip in self.failed_attempts:
            del self.failed_attempts[client_ip]
        
        self.log_security_event('secure_session_created', {
            'user_id': user_id,
            'ip': client_ip
        })
    
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive data before storage"""
        if not self.cipher:
            return data  # Return as-is if encryption not available
        
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self.cipher.encrypt(data)
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            if self.logger_handler:
                self.logger_handler.logger.error(f"Encryption error: {e}")
            return data
    
    def decrypt_sensitive_data(self, encrypted_data):
        """Decrypt sensitive data"""
        if not self.cipher:
            return encrypted_data  # Return as-is if encryption not available
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            if self.logger_handler:
                self.logger_handler.logger.error(f"Decryption error: {e}")
            return encrypted_data
    
    def log_security_event(self, event_type, details):
        """Log security events for monitoring"""
        try:
            security_log = {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'ip': self.get_client_ip(),
                'user_agent': request.headers.get('User-Agent', ''),
                'endpoint': request.endpoint,
                'method': request.method,
                'details': details
            }
            
            if self.logger_handler:
                self.logger_handler.log_security_event(
                    event_type=event_type,
                    description=f"Security event: {event_type}",
                    additional_data=security_log
                )
            
        except Exception as e:
            if self.logger_handler:
                self.logger_handler.logger.error(f"Security logging error: {e}")
    
    def register_security_routes(self):
        """Register security monitoring API endpoints"""
        
        @self.app.route('/api/security/status')
        def security_status():
            """Get current security status"""
            try:
                # Admin only endpoint
                if not session.get('user_id') or session.get('role') != 'admin':
                    return jsonify({'error': 'Access denied'}), 403
                
                current_time = time.time()
                
                # Count active suspicious IPs
                suspicious_count = len([
                    ip for ip, count in self.suspicious_ips.items() 
                    if count > 3
                ])
                
                # Count recent failed attempts
                recent_failures = sum(
                    len([
                        attempt for attempt in attempts 
                        if current_time - attempt < 300  # Last 5 minutes
                    ])
                    for attempts in self.failed_attempts.values()
                )
                
                # Count active sessions
                active_sessions = len([
                    token for token in self.session_tokens.values()
                    if current_time - token['created'] < self.session_timeout
                ])
                
                return jsonify({
                    'suspicious_ips': suspicious_count,
                    'recent_failed_attempts': recent_failures,
                    'active_sessions': active_sessions,
                    'rate_limited_ips': len(self.failed_attempts),
                    'security_status': 'normal' if suspicious_count < 5 else 'elevated'
                })
                
            except Exception as e:
                if self.logger_handler:
                    self.logger_handler.logger.error(f"Security status error: {e}")
                return jsonify({'error': 'Failed to get security status'}), 500
        
        @self.app.route('/api/security/clear-blocks', methods=['POST'])
        def clear_security_blocks():
            """Clear security blocks (admin only)"""
            try:
                if not session.get('user_id') or session.get('role') != 'admin':
                    return jsonify({'error': 'Access denied'}), 403
                
                # Clear failed attempts
                cleared_ips = len(self.failed_attempts)
                self.failed_attempts.clear()
                
                # Clear suspicious IPs
                cleared_suspicious = len(self.suspicious_ips)
                self.suspicious_ips.clear()
                
                self.log_security_event('security_blocks_cleared', {
                    'admin_user': session.get('username'),
                    'cleared_failed_attempts': cleared_ips,
                    'cleared_suspicious_ips': cleared_suspicious
                })
                
                return jsonify({
                    'message': 'Security blocks cleared successfully',
                    'cleared_failed_attempts': cleared_ips,
                    'cleared_suspicious_ips': cleared_suspicious
                })
                
            except Exception as e:
                if self.logger_handler:
                    self.logger_handler.logger.error(f"Clear blocks error: {e}")
                return jsonify({'error': 'Failed to clear security blocks'}), 500

def enhanced_login_required(f):
    """
    Enhanced login required decorator with security checks
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Additional security validation
        if not session.get('security_token'):
            session.clear()
            return jsonify({'error': 'Session security validation failed'}), 401
        
        # Check session timeout
        login_time_str = session.get('login_time')
        if login_time_str:
            try:
                login_time = datetime.fromisoformat(login_time_str)
                if datetime.utcnow() - login_time > timedelta(hours=8):
                    session.clear()
                    return jsonify({'error': 'Session expired'}), 401
            except ValueError:
                session.clear()
                return jsonify({'error': 'Invalid session data'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def csrf_protect(f):
    """
    CSRF protection decorator
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            expected_token = session.get('csrf_token')
            
            if not token or not expected_token or not hmac.compare_digest(token, expected_token):
                return jsonify({'error': 'CSRF token validation failed'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def generate_csrf_token():
    """Generate CSRF token for forms"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']