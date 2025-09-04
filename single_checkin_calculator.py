#!/usr/bin/env python3
"""
Single Check-in Working Hours Calculator
=======================================

Calculator specifically designed for single check-in systems where each
attendance record represents a check-in only (not check-in/check-out pairs).

This calculator interprets consecutive check-ins as work periods:
- 1st check-in = start work
- 2nd check-in = end work (or start of next period)
- 3rd check-in = end previous period, start new period
- etc.

Based on your attendance system structure.
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import math
from logger_handler import log_database_operations


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
    
    def __post_init__(self):
        if self.end_record and self.start_record:
            duration = self.end_record.timestamp - self.start_record.timestamp
            self.duration_minutes = int(duration.total_seconds() / 60)
            self.is_complete = True
        else:
            self.duration_minutes = 0
            self.is_complete = False


class SingleCheckInCalculator:
    """Calculator for single check-in attendance systems"""
    
    def __init__(self, max_work_period_hours: float = 12.0, min_break_minutes: int = 30):
        self.max_work_period_hours = max_work_period_hours  # Maximum reasonable work period
        self.min_break_minutes = min_break_minutes  # Minimum break between work periods
    
    @log_database_operations('single_checkin_hours_calculation')
    def calculate_employee_hours(self, employee_id: str, start_date: datetime, end_date: datetime, 
                                 attendance_records: List[Dict]) -> Dict[str, Any]:
        """
        Calculate working hours for an employee using single check-in records
        
        Logic:
        - Convert consecutive check-ins into work periods
        - 1st check-in = start work, 2nd check-in = end work
        - Handle multiple periods per day
        - Round to nearest quarter hour
        """
        try:
            print(f"🔍 Calculating hours for employee {employee_id}")
            
            # Convert database records to CheckInRecord objects
            records = []
            for record in attendance_records:
                if hasattr(record, '__dict__'):
                    emp_id = str(record.employee_id)
                    date_val = record.check_in_date
                    time_val = record.check_in_time
                    location = record.location_name
                    record_id = record.id
                else:
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
                print(f"⚠️ No records found for employee {employee_id}")
                return self._empty_result(employee_id, start_date, end_date)
            
            print(f"📊 Found {len(records)} check-in records for employee {employee_id}")
            
            # Group records by date and calculate daily hours
            daily_records = {}
            for record in records:
                date_key = record.check_in_date.strftime('%Y-%m-%d')
                if date_key not in daily_records:
                    daily_records[date_key] = []
                daily_records[date_key].append(record)
            
            # Calculate daily hours
            daily_hours = {}
            weekly_totals = []
            
            current_date = start_date
            current_week_hours = []
            
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                day_records = daily_records.get(date_key, [])
                
                # Calculate hours for this day
                day_hours, is_miss_punch = self._calculate_daily_hours_from_checkins(day_records)
                
                daily_hours[date_key] = {
                    'total_minutes': int(day_hours * 60) if day_hours > 0 else 0,
                    'total_hours': day_hours if day_hours > 0 else 0,
                    'is_miss_punch': is_miss_punch,
                    'records_count': len(day_records)
                }
                
                print(f"📅 {date_key}: {len(day_records)} records, {day_hours:.2f} hours, miss_punch: {is_miss_punch}")
                
                # Add to weekly calculation (only positive hours)
                current_week_hours.append(max(0, day_hours))
                
                # Check if end of week (Sunday) or end of period
                if current_date.weekday() == 6 or current_date == end_date:  # Sunday or last day
                    week_total = sum(current_week_hours)
                    week_regular = min(week_total, 40.0)
                    week_overtime = max(0, week_total - 40.0)
                    
                    weekly_totals.append({
                        'total_hours': week_total,
                        'regular_hours': week_regular,
                        'overtime_hours': week_overtime,
                        'total_minutes': int(week_total * 60),
                        'regular_minutes': int(week_regular * 60),
                        'overtime_minutes': int(week_overtime * 60)
                    })
                    
                    current_week_hours = []
                
                current_date += timedelta(days=1)
            
            # Calculate grand totals
            grand_total_hours = sum(week['total_hours'] for week in weekly_totals)
            grand_regular_hours = sum(week['regular_hours'] for week in weekly_totals)
            grand_overtime_hours = sum(week['overtime_hours'] for week in weekly_totals)
            
            print(f"✅ Employee {employee_id}: {grand_total_hours:.2f} total hours, {grand_regular_hours:.2f} regular, {grand_overtime_hours:.2f} OT")
            
            return {
                'employee_id': employee_id,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'include_travel_time': True,  # Not applicable for single check-in system
                'daily_hours': daily_hours,
                'weekly_hours': weekly_totals,
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
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return self._empty_result(employee_id, start_date, end_date)
    
    def _calculate_daily_hours_from_checkins(self, day_records: List[CheckInRecord]) -> Tuple[float, bool]:
        """
        Calculate hours for a single day from check-in records
        
        CORRECTED Logic:
        - 0 records = No work (0 hours, not miss punch)
        - 1 record = Miss punch (incomplete pair)
        - 2, 4, 6, 8... records = Complete pairs, calculate all
        - 3, 5, 7, 9... records = Calculate complete pairs only, ignore last odd record
        
        Returns: (hours, is_miss_punch)
        """
        if not day_records:
            return 0.0, False  # No records = no work
        
        # Sort records by time
        sorted_records = sorted(day_records, key=lambda r: r.timestamp)
        print(f"📝 Processing {len(sorted_records)} records for daily calculation")
        
        # SINGLE RECORD = MISS PUNCH (CORRECTED)
        if len(sorted_records) == 1:
            print(f"⚠️ Single record found - Miss punch (incomplete pair)")
            return 0.0, True  # Single record is always miss punch
        
        # CALCULATE COMPLETE PAIRS ONLY (CORRECTED FOR ODD NUMBERS)
        # For odd numbers: process pairs and ignore the last unpaired record
        num_complete_pairs = len(sorted_records) // 2
        records_to_process = num_complete_pairs * 2  # Only process paired records
        
        print(f"📊 Processing {num_complete_pairs} complete pairs from {len(sorted_records)} total records")
        
        work_periods = []
        total_hours = 0.0
        
        # Process complete pairs only
        for i in range(0, records_to_process, 2):
            start_record = sorted_records[i]
            end_record = sorted_records[i + 1]
            
            period = WorkPeriod(start_record, end_record)
            
            # Validate work period duration
            if self._is_valid_work_period(period):
                work_periods.append(period)
                pair_hours = period.duration_minutes / 60.0
                total_hours += pair_hours
                print(f"✅ Valid work period: {start_record.check_in_time} - {end_record.check_in_time} = {pair_hours:.2f} hours")
            else:
                print(f"⚠️ Invalid work period: {period.duration_minutes/60:.2f} hours - treating as miss punch")
                return 0.0, True  # Invalid period = miss punch
        
        # Check if we had unpaired records (odd number)
        has_unpaired = len(sorted_records) % 2 != 0
        if has_unpaired:
            unpaired_record = sorted_records[-1]
            print(f"⚠️ Unpaired record found: {unpaired_record.check_in_time} (ignored in calculation)")
        
        # Round to nearest quarter hour
        rounded_hours = round(total_hours * 4) / 4
        
        # Determine if this is a miss punch scenario
        is_miss_punch = (num_complete_pairs == 0)  # No valid pairs = miss punch
        
        if is_miss_punch:
            print(f"⚠️ No valid work periods found - Miss punch")
            return 0.0, True
        else:
            print(f"✅ Daily total: {rounded_hours:.2f} hours from {num_complete_pairs} complete work periods")
            # Log the calculation for tracking
            print(f"📊 CORRECTED: Employee daily hours calculated - {rounded_hours:.2f} hours, Miss punch: {is_miss_punch}")
            return rounded_hours, False
    
    def _is_valid_work_period(self, period: WorkPeriod) -> bool:
        """Check if a work period is valid (reasonable duration)"""
        if not period.is_complete:
            return False
        
        hours = period.duration_minutes / 60.0
        
        # Must be positive and less than max work period
        if hours <= 0 or hours > self.max_work_period_hours:
            return False
        
        # Must be at least 15 minutes
        if period.duration_minutes < 15:
            return False
        
        return True
    
    def _empty_result(self, employee_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'employee_id': employee_id,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'include_travel_time': True,
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
        """Calculate working hours for all employees in the given period"""
        try:
            print(f"🚀 Starting calculation for all employees")
            
            # Get unique employee IDs
            employee_ids = set()
            for record in attendance_records:
                if hasattr(record, '__dict__'):
                    employee_ids.add(str(record.employee_id))
                else:
                    employee_ids.add(str(record['employee_id']))
            
            print(f"👥 Found {len(employee_ids)} unique employees")
            
            results = {}
            for emp_id in sorted(employee_ids):
                print(f"\n🔄 Processing employee {emp_id}")
                results[emp_id] = self.calculate_employee_hours(emp_id, start_date, end_date, attendance_records)
            
            return {
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d'),
                'include_travel_time': True,  # Not applicable for single check-in
                'employee_count': len(employee_ids),
                'employees': results
            }
            
        except Exception as e:
            print(f"❌ Error calculating hours for all employees: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise e