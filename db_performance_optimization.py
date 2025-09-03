# File: db_performance_optimization_fixed.py
# Fixed version compatible with your existing AppLogger

from sqlalchemy import text
from datetime import datetime, timedelta
import logging

def create_advanced_performance_indexes(db, logger_handler):
    """
    Create advanced performance indexes for optimal query performance
    Compatible with existing AppLogger
    """
    try:
        # Critical indexes for attendance data
        performance_indexes = [
            # Composite index for attendance queries by date range and employee
            "CREATE INDEX IF NOT EXISTS idx_attendance_employee_date ON attendance_data(employee_id, check_in_date)",
            
            # Index for location-based queries
            "CREATE INDEX IF NOT EXISTS idx_attendance_location_date ON attendance_data(location_name, check_in_date)",
            
            # Index for time-based analytics
            "CREATE INDEX IF NOT EXISTS idx_attendance_datetime ON attendance_data(check_in_date, check_in_time)",
            
            # QR Code performance indexes
            "CREATE INDEX IF NOT EXISTS idx_qrcode_project_active ON qr_codes(project_id, active_status)",
            
            # User authentication indexes
            "CREATE INDEX IF NOT EXISTS idx_users_username_active ON users(username, active_status)",
            "CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, active_status)",
            
            # Project management indexes
            "CREATE INDEX IF NOT EXISTS idx_projects_active_name ON projects(active_status, name)",
            
            # Employee search optimization
            "CREATE INDEX IF NOT EXISTS idx_employee_search ON employee(firstName, lastName, id)",
        ]
        
        indexes_created = 0
        for index_sql in performance_indexes:
            try:
                db.session.execute(text(index_sql))
                logger_handler.logger.info(f"Created index: {index_sql[:50]}...")
                indexes_created += 1
            except Exception as e:
                logger_handler.logger.warning(f"Index creation skipped: {str(e)[:100]}")
        
        db.session.commit()
        
        # Log success using compatible method
        logger_handler.logger.info(f"Performance optimization complete: {indexes_created} indexes created")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        # Use compatible logging method
        logger_handler.log_database_error('performance_optimization', e)
        return False

def optimize_database_configuration(db, logger_handler):
    """
    Optimize database configuration for better performance
    """
    try:
        optimization_queries = [
            # Query cache optimization (MySQL specific)
            "SET SESSION query_cache_type = ON",
            
            # Connection optimization
            "SET SESSION wait_timeout = 28800",
            "SET SESSION interactive_timeout = 28800",
        ]
        
        optimizations_applied = 0
        for query in optimization_queries:
            try:
                db.session.execute(text(query))
                optimizations_applied += 1
            except Exception as e:
                # Some settings may require specific privileges
                logger_handler.logger.debug(f"Configuration skip: {str(e)[:50]}")
        
        logger_handler.logger.info(f"Database configuration optimization completed: {optimizations_applied} optimizations applied")
        
    except Exception as e:
        logger_handler.log_database_error('database_configuration', e)

def create_database_maintenance_routine(app, db, logger_handler):
    """
    Create automated database maintenance routine
    """
    @app.cli.command()
    def db_maintenance():
        """Run database maintenance tasks"""
        try:
            with app.app_context():
                logger_handler.logger.info("Starting database maintenance routine")
                
                # Optimize all tables
                maintenance_queries = [
                    "OPTIMIZE TABLE attendance_data",
                    "OPTIMIZE TABLE qr_codes", 
                    "OPTIMIZE TABLE projects",
                    "OPTIMIZE TABLE users",
                    "OPTIMIZE TABLE employee",
                ]
                
                successful_optimizations = 0
                for query in maintenance_queries:
                    try:
                        db.session.execute(text(query))
                        logger_handler.logger.info(f"Executed: {query}")
                        successful_optimizations += 1
                    except Exception as e:
                        logger_handler.logger.warning(f"Maintenance query failed: {query} - {str(e)}")
                
                db.session.commit()
                
                logger_handler.logger.info(f"Database maintenance completed: {successful_optimizations} tables optimized")
                print("✅ Database maintenance completed successfully")
                
        except Exception as e:
            logger_handler.log_database_error('database_maintenance', e)
            print(f"❌ Database maintenance failed: {e}")

def implement_caching_strategy(app, db, logger_handler):
    """
    Implement intelligent caching strategy for improved performance
    """
    from functools import wraps
    import hashlib
    
    # Simple in-memory cache
    cache_storage = {}
    cache_ttl = {}
    
    def cached_query(ttl=300):  # 5 minutes default TTL
        """Decorator for caching database queries"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Create cache key
                cache_key = f"{func.__name__}_{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"
                current_time = datetime.utcnow().timestamp()
                
                # Check if cached result exists and is still valid
                if cache_key in cache_storage:
                    if current_time - cache_ttl.get(cache_key, 0) < ttl:
                        logger_handler.logger.debug(f"Cache hit for {func.__name__}")
                        return cache_storage[cache_key]
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                cache_storage[cache_key] = result
                cache_ttl[cache_key] = current_time
                
                logger_handler.logger.debug(f"Cache miss for {func.__name__} - result cached")
                return result
            return wrapper
        return decorator
    
    # Clean up expired cache entries periodically
    def cleanup_cache():
        current_time = datetime.utcnow().timestamp()
        expired_keys = [
            key for key, timestamp in cache_ttl.items() 
            if current_time - timestamp > 300  # 5 minutes
        ]
        
        for key in expired_keys:
            cache_storage.pop(key, None)
            cache_ttl.pop(key, None)
        
        if expired_keys:
            logger_handler.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    # Schedule cache cleanup
    @app.before_request
    def before_request_cache_cleanup():
        # Cleanup cache every 100 requests (approximately)
        import random
        if random.randint(1, 100) == 1:
            cleanup_cache()
    
    logger_handler.logger.info("Caching strategy implemented successfully")
    return cached_query

def initialize_performance_optimizations(app, db, logger_handler):
    """
    Initialize all performance optimizations with compatibility
    """
    try:
        logger_handler.logger.info("Starting performance optimization...")
        
        # Create advanced indexes
        index_success = create_advanced_performance_indexes(db, logger_handler)
        
        # Optimize database configuration
        optimize_database_configuration(db, logger_handler)
        
        # Create maintenance routines
        create_database_maintenance_routine(app, db, logger_handler)
        
        # Implement caching
        cached_query = implement_caching_strategy(app, db, logger_handler)
        
        if index_success:
            logger_handler.logger.info("✅ Performance optimization completed successfully")
        else:
            logger_handler.logger.warning("⚠️ Performance optimization completed with some issues")
            
        return cached_query
        
    except Exception as e:
        logger_handler.log_database_error('performance_initialization', e)
        return None