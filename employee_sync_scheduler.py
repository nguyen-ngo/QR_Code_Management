#!/usr/bin/env python3
"""
Employee Synchronization Scheduler
=================================

This script provides automated scheduling for employee synchronization.
Can be run via cron or as a standalone scheduler with configurable intervals.
"""

import os
import sys
import time
import schedule
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the main synchronizer
from employee_table_sync import EmployeeSynchronizer, load_configuration, EmployeeSyncLogger

class EmployeeSyncScheduler:
    """Automated employee synchronization scheduler"""
    
    def __init__(self):
        self.logger = EmployeeSyncLogger('logs/employee_sync_scheduler.log')
        self.is_running = False
        self.last_sync_time = None
        self.sync_interval_minutes = int(os.getenv('SYNC_INTERVAL_MINUTES', 60))  # Default: 1 hour
        
    def run_sync_job(self):
        """Execute a single synchronization job"""
        if self.is_running:
            self.logger.warning("Synchronization already in progress, skipping this run")
            return
        
        self.is_running = True
        self.logger.info("Starting scheduled employee synchronization")
        
        try:
            # Load configurations
            remote_config, local_config = load_configuration()
            
            # Initialize and run synchronizer
            synchronizer = EmployeeSynchronizer(remote_config, local_config)
            stats = synchronizer.run_synchronization()
            
            # Log results (stats already contains serialized datetime objects)
            if stats['errors_encountered'] == 0:
                self.logger.info("Scheduled synchronization completed successfully", {
                    'duration_seconds': (stats['end_time'] - stats['start_time']).total_seconds() if stats['end_time'] and stats['start_time'] else 0,
                    'records_processed': stats['total_remote_records'],
                    'records_inserted': stats['records_inserted'],
                    'records_deleted': stats['records_deleted']
                })
            else:
                self.logger.error("Scheduled synchronization completed with errors", None, {
                    'error_count': stats['errors_encountered'],
                    'records_processed': stats['total_remote_records']
                })
            
            self.last_sync_time = datetime.now()
            
        except Exception as e:
            self.logger.error("Scheduled synchronization failed", e)
        
        finally:
            self.is_running = False
    
    def start_scheduler(self):
        """Start the background scheduler"""
        self.logger.info(f"Starting employee sync scheduler (interval: {self.sync_interval_minutes} minutes)")
        
        # Schedule the job
        schedule.every(self.sync_interval_minutes).minutes.do(self.run_sync_job)
        
        # Run immediately on start
        self.logger.info("Running initial synchronization")
        self.run_sync_job()
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_daily_sync(self):
        """Run synchronization once daily (for cron usage)"""
        self.logger.info("Running daily employee synchronization")
        self.run_sync_job()

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Employee Synchronization Scheduler')
    parser.add_argument('--mode', choices=['once', 'daily', 'continuous'], 
                       default='once', help='Synchronization mode')
    parser.add_argument('--interval', type=int, default=60,
                       help='Sync interval in minutes (for continuous mode)')
    
    args = parser.parse_args()
    
    # Set environment variable for interval
    os.environ['SYNC_INTERVAL_MINUTES'] = str(args.interval)
    
    scheduler = EmployeeSyncScheduler()
    
    if args.mode == 'once':
        print("🔄 Running single employee synchronization...")
        scheduler.run_sync_job()
    elif args.mode == 'daily':
        print("📅 Running daily employee synchronization...")
        scheduler.run_daily_sync()
    elif args.mode == 'continuous':
        print(f"🔁 Starting continuous synchronization (every {args.interval} minutes)...")
        scheduler.start_scheduler()
    
    print("✅ Synchronization completed")

if __name__ == "__main__":
    main()