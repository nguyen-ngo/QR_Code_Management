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
- SP/PW/PT (Special Project/Periodic Work/Part-Time) support with consolidation

Based on the Java classes:
- DailyTimeCalculator.java
- WeeklyTimeCalculator.java 
- PayrollReport.java
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import math
import re
from logger_handler import log_database_operations

# Constants from Java implementation
RECORD_GROUPING_MAX_MINUTES = 60 * 6  # 6 hours
MAX_REGULAR_TIME_MINUTES = 60 * 40    # 40 hours per week


def parse_employee_id_for_work_type(employee_id: str) -> Tuple[str, str]:
    """
    Parse employee ID to extract base ID and work type (supports SP, PW, PT)
    
    Args:
        employee_id: Employee ID string (e.g., "1234", "1234 SP", "1234 PW", "1234 PT")
        
    Returns:
        Tuple of (base_employee_id, work_type)
        work_type is one of: 'regular', 'SP', 'PW', 'PT'
    """
    if not employee_id:
        return str(employee_id), 'regular'
    
    employee_id_clean = str(employee_id).strip().upper()
    
    # Check for SP (Special Project)
    sp_pattern = r'^(\d+)\s*SP$'
    sp_match = re.match(sp_pattern, employee_id_clean)
    if sp_match:
        return sp_match.group(1), 'SP'
    
    # Check for PW (Periodic Work)
    pw_pattern = r'^(\d+)\s*PW$'
    pw_match = re.match(pw_pattern, employee_id_clean)
    if pw_match:
        return pw_match.group(1), 'PW'
    
    # Check for PT (Part-Time)
    pt_pattern = r'^(\d+)\s*PT$'
    pt_match = re.match(pt_pattern, employee_id_clean)
    if pt_match:
        return pt_match.group(1), 'PT'
    
    # Default to regular work
    return employee_id_clean, 'regular'


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
    action_description: str = ''
    
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
            if daily_minutes > 0:
                self.total_minutes += daily_minutes
        
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
    """Builds record pairs from attendance records"""
    
    @staticmethod
    def build_pairs_from_records(records: List[AttendanceRecord]) -> List[RecordPair]:
        """
        Build check-in/check-out pairs from a list of attendance records
        
        Args:
            records: List of AttendanceRecord objects, should be for a single day
            
        Returns:
            List of RecordPair objects
        """
        if not records:
            return []
        
        # Sort by timestamp
        sorted_records = sorted(records, key=lambda r: r.timestamp)
        
        pairs = []
        i = 0
        
        while i < len(sorted_records):
            current_record = sorted_records[i]
            
            # Check if this is a check-in
            if current_record.record_type == 'check_in':
                # Look for matching check-out
                check_out_record = None
                is_miss_punch = False
                j = i + 1
                
                while j < len(sorted_records):
                    next_record = sorted_records[j]
                    if next_record.record_type == 'check_out':
                        check_out_record = next_record
                        i = j + 1  # Move past the check-out
                        break
                    elif next_record.record_type == 'check_in':
                        # Another IN, keep looking
                        j += 1
                
                # If no OUT found, it's an incomplete pair (missed punch)
                if check_out_record is None:
                    is_miss_punch = True
                    i += 1
                
                # Create the pair
                pair = RecordPair(
                    check_in=current_record,
                    check_out=check_out_record,
                    is_miss_punch=is_miss_punch
                )
                pairs.append(pair)
                
            else:
                # Orphaned check-out (OUT without preceding IN)
                pair = RecordPair(
                    check_in=None,
                    check_out=current_record,
                    is_miss_punch=True
                )
                pairs.append(pair)
                i += 1
        
        return pairs


class WorkingHoursCalculator:
    """
    Main calculator for employee working hours with SP/PW/PT support.
    
    This calculator consolidates employees by base ID, grouping records for
    1234, 1234 SP, 1234 PW, 1234 PT under base employee 1234.
    """
    
    def __init__(self):
        pass
    
    @log_database_operations('working_hours_calculation')
    def calculate_employee_hours(self, employee_id: str, start_date: datetime, end_date: datetime, 
                                 attendance_records: List[Dict]) -> Dict[str, Any]:
        """
        Calculate working hours for an employee over a date range with SP/PW/PT support.
        
        This method consolidates all records for base employee ID including SP, PW, PT variants.
        
        Args:
            employee_id: Base employee ID (without SP/PW/PT suffix)
            start_date: Start date for calculation
            end_date: End date for calculation
            attendance_records: List of attendance records from database
            
        Returns:
            Dictionary containing daily and weekly hour calculations with SP/PW/PT breakdown
        """
        try:
            print(f"🔍 Calculating hours for base employee {employee_id} with SP/PW/PT support")
            
            # Parse base employee ID
            base_employee_id, _ = parse_employee_id_for_work_type(employee_id)
            
            # Filter and categorize records by work type
            records_by_type = {'regular': [], 'SP': [], 'PW': [], 'PT': []}
            
            for record in attendance_records:
                try:
                    # Extract employee_id from record
                    if hasattr(record, '__dict__'):
                        record_emp_id = str(getattr(record, 'employee_id', '')).strip()
                        record_date = getattr(record, 'check_in_date', None)
                        record_time = getattr(record, 'check_in_time', None)
                        location = getattr(record, 'location_name', 'Unknown Location')
                        record_id = getattr(record, 'id', 0)
                        record_type = getattr(record, 'record_type', 'check_in')
                        action_desc = getattr(record, 'action_description', '')
                    else:
                        record_emp_id = str(record.get('employee_id', '')).strip()
                        record_date = record.get('check_in_date')
                        record_time = record.get('check_in_time')
                        location = record.get('location_name', 'Unknown Location')
                        record_id = record.get('id', 0)
                        record_type = record.get('record_type', 'check_in')
                        action_desc = record.get('action_description', '')
                    
                    # Skip invalid records
                    if not record_emp_id or record_date is None or record_time is None:
                        continue
                    
                    # Parse work type from record's employee ID
                    record_base_id, work_type = parse_employee_id_for_work_type(record_emp_id)
                    
                    # Only include records for this base employee
                    if record_base_id == base_employee_id:
                        # Determine record type from action_description if available
                        if action_desc:
                            action_lower = action_desc.lower()
                            if 'out' in action_lower or 'checkout' in action_lower:
                                record_type = 'check_out'
                            else:
                                record_type = 'check_in'
                        
                        # Create AttendanceRecord object
                        att_record = AttendanceRecord(
                            id=record_id,
                            employee_id=record_emp_id,
                            check_in_date=record_date if isinstance(record_date, datetime) else datetime.combine(record_date, datetime.min.time()),
                            check_in_time=record_time,
                            location_name=location,
                            record_type=record_type,
                            action_description=action_desc
                        )
                        records_by_type[work_type].append(att_record)
                        
                except Exception as record_error:
                    print(f"⚠️ Error processing record: {record_error}")
                    continue
            
            total_records = sum(len(records_by_type[wt]) for wt in records_by_type)
            print(f"📊 Found {total_records} records - Regular: {len(records_by_type['regular'])}, SP: {len(records_by_type['SP'])}, PW: {len(records_by_type['PW'])}, PT: {len(records_by_type['PT'])}")
            
            # Group records by date for each work type
            daily_records_by_type = {wt: {} for wt in ['regular', 'SP', 'PW', 'PT']}
            
            for work_type in ['regular', 'SP', 'PW', 'PT']:
                for record in records_by_type[work_type]:
                    date_key = record.check_in_date.strftime('%Y-%m-%d') if isinstance(record.check_in_date, datetime) else record.check_in_date.strftime('%Y-%m-%d')
                    if date_key not in daily_records_by_type[work_type]:
                        daily_records_by_type[work_type][date_key] = []
                    daily_records_by_type[work_type][date_key].append(record)
            
            # Calculate daily hours for each work type
            daily_hours = {}
            weekly_hours = []
            current_week_hours = {'regular': 0, 'SP': 0, 'PW': 0, 'PT': 0}
            
            current_date = start_date
            if isinstance(current_date, datetime):
                current_date = current_date.date() if hasattr(current_date, 'date') else current_date
            
            end_date_val = end_date
            if isinstance(end_date_val, datetime):
                end_date_val = end_date_val.date() if hasattr(end_date_val, 'date') else end_date_val
            
            while current_date <= end_date_val:
                date_key = current_date.strftime('%Y-%m-%d')
                
                # Calculate hours for each work type on this day
                hours_by_type = {}
                is_miss_punch_by_type = {}
                records_count_by_type = {}
                
                for work_type in ['regular', 'SP', 'PW', 'PT']:
                    day_records = daily_records_by_type[work_type].get(date_key, [])
                    records_count_by_type[work_type] = len(day_records)
                    
                    if day_records:
                        # Build pairs and calculate hours
                        daily_calc = DailyTimeCalculator()
                        pairs = RecordPairBuilder.build_pairs_from_records(day_records)
                        for pair in pairs:
                            daily_calc.add_record_pair(pair)
                        
                        total_minutes = daily_calc.get_minutes_total_exclude_travel_time()
                        
                        if total_minutes < 0:
                            hours_by_type[work_type] = 0.0
                            is_miss_punch_by_type[work_type] = True
                        else:
                            hours_by_type[work_type] = total_minutes / 60.0
                            is_miss_punch_by_type[work_type] = False
                    else:
                        hours_by_type[work_type] = 0.0
                        is_miss_punch_by_type[work_type] = False
                
                # Store daily data with SP/PW/PT breakdown
                total_day_hours = sum(hours_by_type.values())
                total_records_count = sum(records_count_by_type.values())
                
                daily_hours[date_key] = {
                    'total_minutes': int(total_day_hours * 60),
                    'total_hours': total_day_hours,
                    'regular_hours': hours_by_type['regular'],
                    'sp_hours': hours_by_type['SP'],
                    'pw_hours': hours_by_type['PW'],
                    'pt_hours': hours_by_type['PT'],
                    'is_miss_punch': any(is_miss_punch_by_type.values()),
                    'records_count': total_records_count,
                    'miss_punch_details': {
                        'regular': is_miss_punch_by_type['regular'],
                        'SP': is_miss_punch_by_type['SP'],
                        'PW': is_miss_punch_by_type['PW'],
                        'PT': is_miss_punch_by_type['PT']
                    }
                }
                
                # Accumulate weekly hours by type
                for work_type in ['regular', 'SP', 'PW', 'PT']:
                    current_week_hours[work_type] += hours_by_type[work_type]
                
                # Check for end of week (Sunday) or end of period
                is_end_of_week = current_date.weekday() == 6
                is_end_of_period = current_date >= end_date_val
                
                if is_end_of_week or is_end_of_period:
                    # Calculate weekly totals
                    week_regular_total = current_week_hours['regular']
                    week_sp_total = current_week_hours['SP']
                    week_pw_total = current_week_hours['PW']
                    week_pt_total = current_week_hours['PT']
                    week_total = week_regular_total + week_sp_total + week_pw_total + week_pt_total
                    
                    # Only regular hours count toward overtime (40 hour rule)
                    week_regular_hours = min(week_regular_total, 40.0)
                    week_overtime_hours = max(0, week_regular_total - 40.0)
                    
                    weekly_hours.append({
                        'total_hours': round(week_total, 2),
                        'regular_hours': round(week_regular_hours, 2),
                        'overtime_hours': round(week_overtime_hours, 2),
                        'sp_hours': round(week_sp_total, 2),
                        'pw_hours': round(week_pw_total, 2),
                        'pt_hours': round(week_pt_total, 2),
                        'total_minutes': int(week_total * 60),
                        'regular_minutes': int(week_regular_hours * 60),
                        'overtime_minutes': int(week_overtime_hours * 60),
                        'sp_minutes': int(week_sp_total * 60),
                        'pw_minutes': int(week_pw_total * 60),
                        'pt_minutes': int(week_pt_total * 60)
                    })
                    
                    # Reset for next week
                    current_week_hours = {'regular': 0, 'SP': 0, 'PW': 0, 'PT': 0}
                
                current_date += timedelta(days=1)
            
            # Calculate grand totals
            grand_total_hours = sum(week['total_hours'] for week in weekly_hours)
            grand_regular_hours = sum(week['regular_hours'] for week in weekly_hours)
            grand_overtime_hours = sum(week['overtime_hours'] for week in weekly_hours)
            grand_sp_hours = sum(week['sp_hours'] for week in weekly_hours)
            grand_pw_hours = sum(week['pw_hours'] for week in weekly_hours)
            grand_pt_hours = sum(week.get('pt_hours', 0) for week in weekly_hours)
            
            print(f"✅ Employee {employee_id}: Total: {grand_total_hours:.2f}h (Regular: {grand_regular_hours:.2f}h, OT: {grand_overtime_hours:.2f}h, SP: {grand_sp_hours:.2f}h, PW: {grand_pw_hours:.2f}h, PT: {grand_pt_hours:.2f}h)")
            
            return {
                'employee_id': employee_id,
                'base_employee_id': base_employee_id,
                'start_date': start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date),
                'end_date': end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date),
                'daily_hours': daily_hours,
                'weekly_hours': weekly_hours,
                'grand_totals': {
                    'total_hours': round(grand_total_hours, 2),
                    'regular_hours': round(grand_regular_hours, 2),
                    'overtime_hours': round(grand_overtime_hours, 2),
                    'sp_hours': round(grand_sp_hours, 2),
                    'pw_hours': round(grand_pw_hours, 2),
                    'pt_hours': round(grand_pt_hours, 2),
                    'total_minutes': int(grand_total_hours * 60),
                    'regular_minutes': int(grand_regular_hours * 60),
                    'overtime_minutes': int(grand_overtime_hours * 60),
                    'sp_minutes': int(grand_sp_hours * 60),
                    'pw_minutes': int(grand_pw_hours * 60),
                    'pt_minutes': int(grand_pt_hours * 60)
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculating working hours for employee {employee_id}: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise e
    
    def calculate_all_employees_hours(self, start_date: datetime, end_date: datetime, 
                                      attendance_records: List[Dict]) -> Dict[str, Any]:
        """
        Calculate working hours for all employees in the given period.
        
        This method consolidates employees by base ID, so records for 1234, 1234 SP, 
        1234 PW, 1234 PT will all be grouped under base employee 1234.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            attendance_records: List of attendance records from database
            
        Returns:
            Dictionary containing hours data for all employees with SP/PW/PT breakdown
        """
        try:
            print(f"🚀 Starting calculation for all employees with SP/PW/PT consolidation")
            
            # Get unique BASE employee IDs (consolidate SP/PW/PT variants)
            base_employee_ids = set()
            for record in attendance_records:
                try:
                    if hasattr(record, '__dict__'):
                        employee_id = str(getattr(record, 'employee_id', '')).strip()
                    else:
                        employee_id = str(record.get('employee_id', '')).strip()
                    
                    if employee_id:
                        base_id, _ = parse_employee_id_for_work_type(employee_id)
                        if base_id:
                            base_employee_ids.add(base_id)
                            
                except Exception as e:
                    print(f"⚠️ Error processing employee ID: {e}")
                    continue
            
            print(f"👥 Found {len(base_employee_ids)} unique base employees (after consolidation)")
            
            results = {}
            for base_emp_id in sorted(base_employee_ids):
                try:
                    print(f"\n🔄 Processing base employee {base_emp_id}")
                    results[base_emp_id] = self.calculate_employee_hours(
                        base_emp_id, start_date, end_date, attendance_records
                    )
                except Exception as e:
                    print(f"❌ Error processing employee {base_emp_id}: {e}")
                    # Return empty result for this employee
                    results[base_emp_id] = {
                        'employee_id': base_emp_id,
                        'base_employee_id': base_emp_id,
                        'start_date': start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date),
                        'end_date': end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date),
                        'daily_hours': {},
                        'weekly_hours': [],
                        'grand_totals': {
                            'total_hours': 0.0,
                            'regular_hours': 0.0,
                            'overtime_hours': 0.0,
                            'sp_hours': 0.0,
                            'pw_hours': 0.0,
                            'pt_hours': 0.0,
                            'total_minutes': 0,
                            'regular_minutes': 0,
                            'overtime_minutes': 0,
                            'sp_minutes': 0,
                            'pw_minutes': 0,
                            'pt_minutes': 0
                        }
                    }
                    continue
            
            return {
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period_start': start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date),
                'period_end': end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date),
                'employee_count': len(base_employee_ids),
                'employees': results
            }
            
        except Exception as e:
            print(f"❌ Error calculating hours for all employees: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise e