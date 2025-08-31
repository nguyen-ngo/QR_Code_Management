# File: app_performance_middleware.py
# Advanced performance middleware for QR Attendance System

from functools import wraps
from flask import request, g, jsonify, current_app
import time
import threading
import queue
from datetime import datetime, timedelta
from collections import defaultdict, deque
import gc
import psutil
import os

class PerformanceMonitor:
    """
    Advanced performance monitoring and optimization middleware
    """
    
    def __init__(self, app=None, db=None, logger_handler=None):
        self.app = app
        self.db = db
        self.logger_handler = logger_handler
        
        # Performance metrics storage
        self.request_times = deque(maxlen=1000)  # Keep last 1000 requests
        self.slow_queries = deque(maxlen=100)
        self.error_rates = defaultdict(int)
        self.endpoint_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'errors': 0})
        
        # Rate limiting storage
        self.rate_limit_storage = defaultdict(lambda: {'requests': deque(), 'blocked_until': None})
        
        # Background task queue
        self.task_queue = queue.Queue()
        self.background_worker = None
        
        if app:
            self.init_app(app, db, logger_handler)
    
    def init_app(self, app, db, logger_handler):
        """Initialize performance monitoring with Flask app"""
        self.app = app
        self.db = db
        self.logger_handler = logger_handler
        
        # Register before/after request handlers
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Start background worker
        self.start_background_worker()
        
        # Register performance monitoring routes
        self.register_performance_routes()
    
    def before_request(self):
        """Performance monitoring before each request"""
        g.start_time = time.time()
        g.request_id = f"{int(time.time())}-{threading.get_ident()}"
        
        # Rate limiting check
        if self.is_rate_limited():
            return jsonify({
                'error': 'Rate limit exceeded',
                'retry_after': 60
            }), 429
        
        # Memory usage monitoring
        self.monitor_memory_usage()
    
    def after_request(self, response):
        """Performance monitoring after each request"""
        if hasattr(g, 'start_time'):
            request_time = time.time() - g.start_time
            
            # Record request metrics
            self.record_request_metrics(request_time, response.status_code)
            
            # Log slow requests
            if request_time > 2.0:  # Requests taking more than 2 seconds
                self.log_slow_request(request_time)
            
            # Add performance headers
            response.headers['X-Response-Time'] = f"{request_time:.3f}s"
            response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        
        return response
    
    def record_request_metrics(self, request_time, status_code):
        """Record request performance metrics"""
        endpoint = request.endpoint or 'unknown'
        
        # Store request time
        self.request_times.append({
            'endpoint': endpoint,
            'time': request_time,
            'status': status_code,
            'timestamp': datetime.utcnow()
        })
        
        # Update endpoint statistics
        self.endpoint_stats[endpoint]['count'] += 1
        self.endpoint_stats[endpoint]['total_time'] += request_time
        
        if status_code >= 400:
            self.endpoint_stats[endpoint]['errors'] += 1
            self.error_rates[status_code] += 1
    
    def is_rate_limited(self):
        """Check if current request should be rate limited"""
        client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
        current_time = time.time()
        
        # Clean up old requests
        client_data = self.rate_limit_storage[client_ip]
        client_data['requests'] = deque([
            req_time for req_time in client_data['requests'] 
            if current_time - req_time < 60  # 1 minute window
        ], maxlen=100)
        
        # Check if currently blocked
        if client_data['blocked_until'] and current_time < client_data['blocked_until']:
            return True
        
        # Add current request
        client_data['requests'].append(current_time)
        
        # Check rate limit (100 requests per minute)
        if len(client_data['requests']) > 100:
            client_data['blocked_until'] = current_time + 300  # Block for 5 minutes
            self.logger_handler.logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return True
        
        return False
    
    def monitor_memory_usage(self):
        """Monitor application memory usage"""
        # Get memory usage every 10 requests (approximately)
        import random
        if random.randint(1, 10) == 1:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > 1000:  # More than 1GB
                self.logger_handler.logger.warning(f"High memory usage: {memory_mb:.1f}MB")
                
                # Force garbage collection
                gc.collect()
                
                # Queue background cleanup task
                self.task_queue.put({
                    'type': 'memory_cleanup',
                    'timestamp': datetime.utcnow()
                })
    
    def log_slow_request(self, request_time):
        """Log slow requests for optimization"""
        slow_request_data = {
            'endpoint': request.endpoint,
            'method': request.method,
            'time': request_time,
            'args': dict(request.args),
            'timestamp': datetime.utcnow()
        }
        
        self.slow_queries.append(slow_request_data)
        
        self.logger_handler.logger.warning(
            f"Slow request: {request.method} {request.endpoint} - {request_time:.3f}s"
        )
    
    def start_background_worker(self):
        """Start background worker for performance tasks"""
        def worker():
            while True:
                try:
                    task = self.task_queue.get(timeout=30)
                    self.process_background_task(task)
                    self.task_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    if self.logger_handler:
                        self.logger_handler.logger.error(f"Background worker error: {e}")
        
        self.background_worker = threading.Thread(target=worker, daemon=True)
        self.background_worker.start()
    
    def process_background_task(self, task):
        """Process background performance tasks"""
        task_type = task.get('type')
        
        if task_type == 'memory_cleanup':
            self.perform_memory_cleanup()
        elif task_type == 'performance_analysis':
            self.perform_performance_analysis()
        elif task_type == 'database_optimization':
            self.optimize_database_connections()
    
    def perform_memory_cleanup(self):
        """Perform memory cleanup operations"""
        try:
            # Clear old metrics
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            # Clean request times
            self.request_times = deque([
                req for req in self.request_times 
                if req['timestamp'] > cutoff_time
            ], maxlen=1000)
            
            # Clean slow queries
            self.slow_queries = deque([
                query for query in self.slow_queries 
                if query['timestamp'] > cutoff_time
            ], maxlen=100)
            
            # Clean rate limit storage
            current_time = time.time()
            for ip, data in list(self.rate_limit_storage.items()):
                if not data['requests'] and (
                    not data['blocked_until'] or current_time > data['blocked_until']
                ):
                    del self.rate_limit_storage[ip]
            
            # Force garbage collection
            gc.collect()
            
            self.logger_handler.logger.info("Memory cleanup completed")
            
        except Exception as e:
            self.logger_handler.logger.error(f"Memory cleanup failed: {e}")
    
    def register_performance_routes(self):
        """Register performance monitoring API endpoints"""
        
        @self.app.route('/api/performance/stats')
        def performance_stats():
            """Get current performance statistics"""
            try:
                # Calculate average response times
                recent_requests = [
                    req for req in self.request_times 
                    if req['timestamp'] > datetime.utcnow() - timedelta(minutes=5)
                ]
                
                avg_response_time = (
                    sum(req['time'] for req in recent_requests) / len(recent_requests)
                    if recent_requests else 0
                )
                
                # Get endpoint statistics
                endpoint_performance = {}
                for endpoint, stats in self.endpoint_stats.items():
                    endpoint_performance[endpoint] = {
                        'avg_response_time': stats['total_time'] / stats['count'] if stats['count'] > 0 else 0,
                        'total_requests': stats['count'],
                        'error_rate': stats['errors'] / stats['count'] if stats['count'] > 0 else 0
                    }
                
                # Get memory info
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                
                return jsonify({
                    'avg_response_time': round(avg_response_time, 3),
                    'total_requests': len(self.request_times),
                    'slow_requests': len(self.slow_queries),
                    'memory_usage_mb': round(memory_info.rss / 1024 / 1024, 1),
                    'endpoint_performance': endpoint_performance,
                    'error_rates': dict(self.error_rates)
                })
                
            except Exception as e:
                self.logger_handler.logger.error(f"Performance stats error: {e}")
                return jsonify({'error': 'Failed to get performance stats'}), 500
        
        @self.app.route('/api/performance/slow-requests')
        def slow_requests():
            """Get recent slow requests for analysis"""
            try:
                slow_request_list = [
                    {
                        'endpoint': req['endpoint'],
                        'method': req.get('method', 'GET'),
                        'time': round(req['time'], 3),
                        'timestamp': req['timestamp'].isoformat()
                    }
                    for req in list(self.slow_queries)[-20:]  # Last 20 slow requests
                ]
                
                return jsonify({
                    'slow_requests': slow_request_list,
                    'total_slow_requests': len(self.slow_queries)
                })
                
            except Exception as e:
                self.logger_handler.logger.error(f"Slow requests API error: {e}")
                return jsonify({'error': 'Failed to get slow requests'}), 500

def performance_optimization_decorator(threshold=1.0):
    """
    Decorator to monitor and optimize specific function performance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if execution_time > threshold:
                    print(f"⚠️  Slow function: {func.__name__} took {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                print(f"❌ Function error: {func.__name__} failed after {execution_time:.3f}s - {e}")
                raise
                
        return wrapper
    return decorator

def optimize_database_queries():
    """
    Database query optimization decorator
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Enable query logging for this function
            query_start = time.time()
            
            result = func(*args, **kwargs)
            
            query_time = time.time() - query_start
            if query_time > 0.5:  # Queries taking more than 500ms
                print(f"🐌 Slow query in {func.__name__}: {query_time:.3f}s")
            
            return result
        return wrapper
    return decorator