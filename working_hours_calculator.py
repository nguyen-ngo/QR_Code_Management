#!/usr/bin/env python3
"""
Working Hours Calculator for Employee Payroll
============================================

This module implements the working hours calculation logic
based on the Java files provided. It handles:
- Daily time calculations with travel time options
- Weekly regular and overtime hours
- Record pairing (check-in/check-out)
- Missing punch detection
- Quarter-hour rounding

Based on the Java classes:
- DailyTimeCalculator.java
- WeeklyTimeCalculator.java 
- PayrollReport.java
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import math
from logger_handler import log_database_operations

# Constants from Java implementation
RECORD_GROUPING_MAX_MINUTES = 60 * 6  # 6 hours
MAX_REGULAR_TIME_MINUTES = 60 * 40    # 40 hours per week

@dataclass
class AttendanceRecord:
    """Represents a single attendance record"""
    id: int
    employee_id: str
    check_in_date: datetime
    check_in_time: time
    location_name: str
    record_type: str = 'check_in'  # 'check_in' or 'check_out'
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            # Combine date and time for timestamp
            self.timestamp = datetime.combine(self.check_in_date, self.check_in_time)

@dataclass 
class RecordPair:
    """Represents a paired check-in/check-out record"""
    check_in: Optional[AttendanceRecord]
    check_out: Optional[AttendanceRecord]
    is_miss_punch: bool = False
    date: datetime = None
    location: str = ""
    
    def __post_init__(self):
        if self.check_in:
            self.date = self.check_in.check_in_date
            self.location = self.check_in.location_name
        elif self.check_out:
            self.date = self.check_out.check_in_date
            self.location = self.check_out.location_name
    
    @property
    def duration_minutes(self) -> int:
        """Calculate duration in minutes between check-in and check-out"""
        if self.is_miss_punch or not self.check_in or not self.check_out:
            return -1
        
        duration = self.check_out.timestamp - self.check_in.timestamp
        return int(duration.total_seconds() / 60)

class TimeCalculator:
    """Base time calculator with rounding functionality"""
    
    @staticmethod
    def round_time_to_nearest_quarter_hour(minutes: int) -> int:
        """Round time to nearest quarter hour (15 minutes)"""
        if minutes < 0:
            return minutes  # Keep negative values for miss punches
        
        # Round to nearest 15-minute interval
        return round(minutes / 15) * 15

class DailyTimeCalculator(TimeCalculator):
    """Calculate daily working hours with travel time options"""
    
    def __init__(self):
        self.record_pairs: List[RecordPair] = []
    
    def add_record_pair(self, pair: RecordPair):
        """Add a record pair to the daily calculation"""
        self.record_pairs.append(pair)
    
    def get_minutes_total_exclude_travel_time(self) -> int:
        """Calculate total minutes excluding travel time"""
        minute_total = 0
        
        for pair in self.record_pairs:
            if not pair.is_miss_punch:
                minute_total += pair.duration_minutes
            else:
                return -1  # Miss punch detected
        
        return self.round_time_to_nearest_quarter_hour(minute_total)
        
class WeeklyTimeCalculator(TimeCalculator):
    """Calculate weekly regular and overtime hours"""
    
    def __init__(self):
        self.daily_calculators: List[DailyTimeCalculator] = []
        self.total_minutes = 0
        self.regular_minutes = 0
        self.overtime_minutes = 0
    
    def add_daily_calculator(self, daily_calc: DailyTimeCalculator):
        """Add a daily time calculator to the weekly calculation"""
        self.daily_calculators.append(daily_calc)
    
    def calculate_time(self):
        """Calculate weekly totals with regular and overtime split"""
        self.total_minutes = 0
        
        for daily_calc in self.daily_calculators:
            daily_minutes = daily_calc.get_minutes_total_exclude_travel_time()
        
        # Calculate regular and overtime
        if self.total_minutes > MAX_REGULAR_TIME_MINUTES:
            self.regular_minutes = MAX_REGULAR_TIME_MINUTES
        else:
            self.regular_minutes = self.total_minutes
        
        self.overtime_minutes = self.total_minutes - self.regular_minutes
    
    @property
    def total_hours(self) -> float:
        """Get total hours as decimal"""
        return self.total_minutes / 60.0
    
    @property
    def regular_hours(self) -> float:
        """Get regular hours as decimal"""
        return self.regular_minutes / 60.0
    
    @property
    def overtime_hours(self) -> float:
        """Get overtime hours as decimal"""
        return self.overtime_minutes / 60.0

class RecordPairBuilder:
    """Build record pairs from attendance records"""
    
    @staticmethod
    def build_pairs_from_records(records: List[AttendanceRecord]) -> List[RecordPair]:
        """Build check-in/check-out pairs from attendance records"""
        if not records:
            return []
        
        # Sort records by timestamp
        sorted_records = sorted(records, key=lambda r: r.timestamp)
        pairs = []
        
        i = 0
        while i < len(sorted_records):
            current_record = sorted_records[i]
            
            # Look for matching check-out record
            check_out_record = None
            if i + 1 < len(sorted_records):
                next_record = sorted_records[i + 1]
                # Simple pairing: assume alternating check-in/check-out
                if current_record.record_type == 'check_in' and next_record.record_type == 'check_out':
                    check_out_record = next_record
                    i += 2  # Skip both records
                else:
                    i += 1
            else:
                i += 1
            
            # Create pair
            if current_record.record_type == 'check_in':
                pair = RecordPair(
                    check_in=current_record,
                    check_out=check_out_record,
                    is_miss_punch=(check_out_record is None)
                )
            else:
                # Orphaned check-out
                pair = RecordPair(
                    check_in=None,
                    check_out=current_record,
                    is_miss_punch=True
                )
            
            pairs.append(pair)
        
        return pairs

class WorkingHoursCalculator:
    """Main calculator for employee working hours"""
    
    def __init__(self):
        pass
    
    @log_database_operations('working_hours_calculation')
    def calculate_employee_hours(self, employee_id: str, start_date: datetime, end_date: datetime, 
                                 attendance_records: List[Dict]) -> Dict[str, Any]:
        """
        Calculate working hours for an employee over a date range
        
        Args:
            employee_id: Employee ID
            start_date: Start date for calculation
            end_date: End date for calculation
            attendance_records: List of attendance records from database
            
        Returns:
            Dictionary containing daily and weekly hour calculations
        """
        try:
            # Convert database records to AttendanceRecord objects
            records = []
            for record in attendance_records:
                # Handle both dictionary and SQLAlchemy object formats
                if hasattr(record, '__dict__'):
                    # SQLAlchemy object
                    emp_id = str(record.employee_id)
                    date_val = record.check_in_date
                    time_val = record.check_in_time
                    location = record.location_name
                    record_id = record.id
                else:
                    # Dictionary
                    emp_id = str(record['employee_id'])
                    date_val = record['check_in_date']
                    time_val = record['check_in_time']
                    location = record['location_name']
                    record_id = record['id']
                
                if emp_id == employee_id:
                    att_record = AttendanceRecord(
                        id=record_id,
                        employee_id=emp_id,
                        check_in_date=date_val,
                        check_in_time=time_val,
                        location_name=location,
                        record_type='check_in'  # Default, could be enhanced
                    )
                    records.append(att_record)
            
            # Group records by date
            daily_records = {}
            for record in records:
                date_key = record.check_in_date.strftime('%Y-%m-%d')
                if date_key not in daily_records:
                    daily_records[date_key] = []
                daily_records[date_key].append(record)
            
            # Calculate daily hours
            daily_hours = {}
            weekly_calculators = []
            
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                day_records = daily_records.get(date_key, [])
                
                daily_calc = DailyTimeCalculator()
                
                if day_records:
                    # Build record pairs
                    pairs = RecordPairBuilder.build_pairs_from_records(day_records)
                    for pair in pairs:
                        daily_calc.add_record_pair(pair)
                
                # Calculate daily totals
                total_minutes = daily_calc.get_minutes_total_exclude_travel_time()
                
                daily_hours[date_key] = {
                    'total_minutes': total_minutes,
                    'total_hours': total_minutes / 60.0 if total_minutes > 0 else 0,
                    'is_miss_punch': total_minutes < 0,
                    'records_count': len(day_records)
                }
                
                # Add to weekly calculator (group by week)
                if current_date.weekday() == 0:  # Monday - start new week
                    weekly_calc = WeeklyTimeCalculator()
                    weekly_calculators.append(weekly_calc)
                
                if weekly_calculators:
                    weekly_calculators[-1].add_daily_calculator(daily_calc)
                
                current_date += timedelta(days=1)
            
            # Calculate weekly totals
            weekly_hours = []
            for week_calc in weekly_calculators:
                week_calc.calculate_time()
                weekly_hours.append({
                    'total_hours': week_calc.total_hours,
                    'regular_hours': week_calc.regular_hours,
                    'overtime_hours': week_calc.overtime_hours,
                    'total_minutes': week_calc.total_minutes,
                    'regular_minutes': week_calc.regular_minutes,
                    'overtime_minutes': week_calc.overtime_minutes
                })
            
            # Calculate grand totals
            grand_total_hours = sum(week['total_hours'] for week in weekly_hours)
            grand_regular_hours = sum(week['regular_hours'] for week in weekly_hours)
            grand_overtime_hours = sum(week['overtime_hours'] for week in weekly_hours)
            
            return {
                'employee_id': employee_id,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'daily_hours': daily_hours,
                'weekly_hours': weekly_hours,
                'grand_totals': {
                    'total_hours': grand_total_hours,
                    'regular_hours': grand_regular_hours,
                    'overtime_hours': grand_overtime_hours,
                    'total_minutes': int(grand_total_hours * 60),
                    'regular_minutes': int(grand_regular_hours * 60),
                    'overtime_minutes': int(grand_overtime_hours * 60)
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculating working hours for employee {employee_id}: {e}")
            raise e
    
    def calculate_all_employees_hours(self, start_date: datetime, end_date: datetime, 
                                      attendance_records: List[Dict]) -> Dict[str, Any]:
        """Calculate working hours for all employees in the given period"""
        try:
            # Get unique employee IDs
            employee_ids = set()
            for record in attendance_records:
                if hasattr(record, '__dict__'):
                    employee_ids.add(str(record.employee_id))
                else:
                    employee_ids.add(str(record['employee_id']))
            
            results = {}
            for emp_id in employee_ids:
                results[emp_id] = self.calculate_employee_hours(emp_id, start_date, end_date, attendance_records)
            
            return {
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d'),
                'employee_count': len(employee_ids),
                'employees': results
            }
            
        except Exception as e:
            print(f"❌ Error calculating hours for all employees: {e}")
            raise e