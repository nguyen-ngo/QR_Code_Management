#!/usr/bin/env python3
"""
Enhanced Single Check-in Working Hours Calculator
===============================================

This integrates the comprehensive working hours calculation logic from 
working_hours_calculator.py into the existing SingleCheckInCalculator system.

Key enhancements:
- Quarter-hour rounding
- Travel time handling between locations
- Record pairing logic
- Weekly overtime calculations
- Miss punch detection
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import math
from logger_handler import log_database_operations

# Constants from comprehensive working hours calculator
TRAVEL_TIME_MAX_MINUTES = 60
RECORD_GROUPING_MAX_MINUTES = 60 * 6  # 6 hours
MAX_REGULAR_TIME_MINUTES = 60 * 40    # 40 hours per week


@dataclass
class CheckInRecord:
    """Represents a single check-in record"""
    id: int
    employee_id: str
    check_in_date: datetime
    check_in_time: time
    location_name: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            # Combine date and time for timestamp
            self.timestamp = datetime.combine(self.check_in_date, self.check_in_time)


@dataclass 
class WorkPeriod:
    """Represents a calculated work period from consecutive check-ins"""
    start_record: CheckInRecord
    end_record: Optional[CheckInRecord]
    duration_minutes: int = 0
    is_complete: bool = False
    location_name: str = ""
    
    def __post_init__(self):
        if self.end_record and self.start_record:
            duration = self.end_record.timestamp - self.start_record.timestamp
            self.duration_minutes = int(duration.total_seconds() / 60)
            self.is_complete = True
            self.location_name = self.start_record.location_name
        else:
            self.duration_minutes = 0
            self.is_complete = False
            if self.start_record:
                self.location_name = self.start_record.location_name


class EnhancedTimeCalculator:
    """Enhanced time calculator with quarter-hour rounding functionality"""
    
    @staticmethod
    def round_time_to_nearest_quarter_hour(minutes: int) -> int:
        """Round time to nearest quarter hour (15 minutes)"""
        if minutes < 0:
            return minutes  # Keep negative values for miss punches
        
        # Round to nearest 15-minute interval
        return round(minutes / 15) * 15
    
    @staticmethod
    def group_work_periods_by_travel_time(periods: List[WorkPeriod]) -> List[List[WorkPeriod]]:
        """Group work periods based on travel time gaps"""
        if not periods:
            return []
        
        # Sort periods by start time
        sorted_periods = sorted([p for p in periods if p.is_complete], 
                               key=lambda p: p.start_record.timestamp)
        
        if not sorted_periods:
            return []
        
        all_groups = []
        current_group = [sorted_periods[0]]
        
        for i in range(1, len(sorted_periods)):
            prev_period = sorted_periods[i-1]
            current_period = sorted_periods[i]
            
            # Calculate time gap between periods
            gap_minutes = (current_period.start_record.timestamp - 
                          prev_period.end_record.timestamp).total_seconds() / 60
            
            if gap_minutes > TRAVEL_TIME_MAX_MINUTES:
                # Start new group - gap too large for travel time
                all_groups.append(current_group)
                current_group = [current_period]
            else:
                # Add to current group - within travel time
                current_group.append(current_period)
        
        all_groups.append(current_group)
        return all_groups
    
    @staticmethod
    def calculate_group_minutes_with_travel_time(group: List[WorkPeriod]) -> int:
        """Calculate total minutes for a group including travel time"""
        if not group:
            return 0
        
        # Find overall start and end times for the group
        start_time = min(period.start_record.timestamp for period in group)
        end_time = max(period.end_record.timestamp for period in group)
        
        duration = end_time - start_time
        return int(duration.total_seconds() / 60)


class WeeklyHoursCalculator:
    """Calculate weekly regular and overtime hours"""
    
    def __init__(self):
        self.total_minutes = 0
        self.regular_minutes = 0
        self.overtime_minutes = 0
    
    def calculate_weekly_totals(self, daily_minutes_list: List[int]):
        """Calculate weekly totals with regular and overtime split"""
        self.total_minutes = sum(minutes for minutes in daily_minutes_list if minutes > 0)
        
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


class SingleCheckInCalculator:
    """Enhanced calculator for single check-in attendance systems"""
    
    def __init__(self, max_work_period_hours: float = 12.0, min_break_minutes: int = 30, 
                 include_travel_time: bool = True):
        self.max_work_period_hours = max_work_period_hours
        self.min_break_minutes = min_break_minutes
        self.include_travel_time = include_travel_time
        self.time_calculator = EnhancedTimeCalculator()
    
    @log_database_operations('enhanced_single_checkin_hours_calculation')
    def calculate_employee_hours(self, employee_id: str, start_date: datetime, end_date: datetime, 
                                 attendance_records: List[Dict]) -> Dict[str, Any]:
        """
        Enhanced calculation with travel time, quarter-hour rounding, and overtime logic
        """
        try:
            print(f"🔍 Calculating enhanced hours for employee {employee_id}")
            
            # Convert database records to CheckInRecord objects
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
                    checkin_record = CheckInRecord(
                        id=record_id,
                        employee_id=emp_id,
                        check_in_date=date_val,
                        check_in_time=time_val,
                        location_name=location
                    )
                    records.append(checkin_record)
            
            if not records:
                print(f"📝 No records found for employee {employee_id}")
                return self._create_empty_result(employee_id, start_date, end_date)
            
            # Sort records by timestamp
            records.sort(key=lambda x: x.timestamp)
            print(f"📊 Processing {len(records)} records for employee {employee_id}")
            
            # Group records by date and calculate daily hours
            daily_records = {}
            for record in records:
                date_key = record.check_in_date.strftime('%Y-%m-%d')
                if date_key not in daily_records:
                    daily_records[date_key] = []
                daily_records[date_key].append(record)
            
            # Calculate daily hours with enhanced logic
            daily_hours = {}
            weekly_minutes_list = []
            
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                day_records = daily_records.get(date_key, [])
                
                if day_records:
                    daily_total_minutes = self._calculate_daily_hours_enhanced(day_records)
                else:
                    daily_total_minutes = 0
                
                daily_hours[date_key] = {
                    'total_minutes': daily_total_minutes,
                    'total_hours': daily_total_minutes / 60.0 if daily_total_minutes > 0 else 0,
                    'is_miss_punch': daily_total_minutes < 0,
                    'records_count': len(day_records),
                    'include_travel_time': self.include_travel_time
                }
                
                # Collect for weekly calculation
                if daily_total_minutes > 0:
                    weekly_minutes_list.append(daily_total_minutes)
                
                current_date += timedelta(days=1)
            
            # Calculate weekly totals with overtime
            weekly_calc = WeeklyHoursCalculator()
            weekly_calc.calculate_weekly_totals(weekly_minutes_list)
            
            weekly_hours = [{
                'total_hours': weekly_calc.total_hours,
                'regular_hours': weekly_calc.regular_hours,
                'overtime_hours': weekly_calc.overtime_hours,
                'total_minutes': weekly_calc.total_minutes,
                'regular_minutes': weekly_calc.regular_minutes,
                'overtime_minutes': weekly_calc.overtime_minutes
            }]
            
            # Calculate grand totals
            grand_total_hours = weekly_calc.total_hours
            grand_regular_hours = weekly_calc.regular_hours
            grand_overtime_hours = weekly_calc.overtime_hours
            
            result = {
                'employee_id': employee_id,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'include_travel_time': self.include_travel_time,
                'calculation_method': 'enhanced_single_checkin',
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
            
            print(f"✅ Enhanced calculation completed for employee {employee_id}: {grand_total_hours:.2f} total hours")
            return result
            
        except Exception as e:
            print(f"❌ Error in enhanced calculation for employee {employee_id}: {e}")
            raise e
    
    def _calculate_daily_hours_enhanced(self, day_records: List[CheckInRecord]) -> int:
        """
        Enhanced daily calculation with travel time and quarter-hour rounding
        """
        try:
            # Convert consecutive check-ins to work periods
            work_periods = self._build_work_periods_from_checkins(day_records)
            
            if not work_periods:
                return 0
            
            # Check for incomplete periods (miss punches)
            incomplete_periods = [p for p in work_periods if not p.is_complete]
            if incomplete_periods:
                print(f"⚠️ Found {len(incomplete_periods)} incomplete work periods (miss punches)")
                return -1  # Indicate miss punch
            
            if self.include_travel_time:
                # Group periods and calculate with travel time
                return self._calculate_with_travel_time(work_periods)
            else:
                # Sum individual periods without travel time
                total_minutes = sum(period.duration_minutes for period in work_periods if period.is_complete)
                return self.time_calculator.round_time_to_nearest_quarter_hour(total_minutes)
        
        except Exception as e:
            print(f"❌ Error calculating daily hours: {e}")
            return -1
    
    def _build_work_periods_from_checkins(self, records: List[CheckInRecord]) -> List[WorkPeriod]:
        """
        Build work periods from consecutive check-ins
        Logic: 1st = start, 2nd = end, 3rd = start new period, etc.
        """
        periods = []
        
        for i in range(0, len(records), 2):
            start_record = records[i]
            end_record = records[i + 1] if i + 1 < len(records) else None
            
            # Validate work period duration
            if end_record:
                duration_hours = (end_record.timestamp - start_record.timestamp).total_seconds() / 3600
                if duration_hours > self.max_work_period_hours:
                    print(f"⚠️ Work period exceeds {self.max_work_period_hours} hours, treating as miss punch")
                    end_record = None
            
            period = WorkPeriod(
                start_record=start_record,
                end_record=end_record
            )
            periods.append(period)
        
        return periods
    
    def _calculate_with_travel_time(self, work_periods: List[WorkPeriod]) -> int:
        """Calculate total minutes including travel time between locations"""
        complete_periods = [p for p in work_periods if p.is_complete]
        
        if not complete_periods:
            return 0
        
        # Group periods by travel time
        period_groups = self.time_calculator.group_work_periods_by_travel_time(complete_periods)
        
        total_minutes = 0
        for group in period_groups:
            group_minutes = self.time_calculator.calculate_group_minutes_with_travel_time(group)
            total_minutes += group_minutes
        
        return self.time_calculator.round_time_to_nearest_quarter_hour(total_minutes)
    
    def _create_empty_result(self, employee_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Create empty result structure for employees with no records"""
        return {
            'employee_id': employee_id,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'include_travel_time': self.include_travel_time,
            'calculation_method': 'enhanced_single_checkin',
            'daily_hours': {},
            'weekly_hours': [],
            'grand_totals': {
                'total_hours': 0.0,
                'regular_hours': 0.0,
                'overtime_hours': 0.0,
                'total_minutes': 0,
                'regular_minutes': 0,
                'overtime_minutes': 0
            }
        }
    
    def calculate_all_employees_hours(self, start_date: datetime, end_date: datetime, 
                                      attendance_records: List[Dict]) -> Dict[str, Any]:
        """Calculate enhanced working hours for all employees in the given period"""
        try:
            # Get unique employee IDs
            employee_ids = set()
            for record in attendance_records:
                if hasattr(record, '__dict__'):
                    employee_ids.add(str(record.employee_id))
                else:
                    employee_ids.add(str(record['employee_id']))
            
            print(f"📊 Calculating enhanced hours for {len(employee_ids)} employees")
            
            results = {}
            for emp_id in employee_ids:
                results[emp_id] = self.calculate_employee_hours(emp_id, start_date, end_date, attendance_records)
            
            return {
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d'),
                'include_travel_time': self.include_travel_time,
                'calculation_method': 'enhanced_single_checkin',
                'employee_count': len(employee_ids),
                'employees': results
            }
            
        except Exception as e:
            print(f"❌ Error calculating enhanced hours for all employees: {e}")
            raise e