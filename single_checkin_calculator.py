#!/usr/bin/env python3
"""
Safe Enhanced Single Check-in Working Hours Calculator with SP/PW Support
========================================================================

This version maintains full backward compatibility while adding SP/PW support.
It gracefully handles missing data and falls back to standard calculation when needed.
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import math
import re
from logger_handler import log_database_operations


def parse_employee_id_for_work_type(employee_id: str) -> Tuple[str, str]:
    """Parse employee ID to extract base ID and work type"""
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
    
    # Default to regular work
    return employee_id_clean, 'regular'


class SingleCheckInCalculator:
    """Enhanced calculator for single check-in attendance systems with SP/PW support"""
    
    def __init__(self, max_work_period_hours: float = 12.0, min_break_minutes: int = 30):
        self.max_work_period_hours = max_work_period_hours
        self.min_break_minutes = min_break_minutes
    
    @log_database_operations('single_checkin_hours_calculation_sp_pw')
    def calculate_employee_hours(self, employee_id: str, start_date: datetime, end_date: datetime, 
                                 attendance_records: List[Dict]) -> Dict[str, Any]:
        """
        Calculate working hours for an employee with SP/PW support and robust error handling
        """
        try:
            print(f"🔍 Calculating hours for employee {employee_id} with SP/PW support")
            
            # Parse base employee ID and work type
            base_employee_id, _ = parse_employee_id_for_work_type(employee_id)
            
            # Filter and categorize records
            records_by_type = {'regular': [], 'SP': [], 'PW': []}
            
            for record in attendance_records:
                try:
                    # Extract record data safely
                    if hasattr(record, '__dict__'):
                        record_emp_id = str(getattr(record, 'employee_id', '')).strip()
                        record_date = getattr(record, 'check_in_date', None)
                        record_time = getattr(record, 'check_in_time', None)
                        location = getattr(record, 'location_name', 'Unknown Location')
                        record_id = getattr(record, 'id', 0)
                    else:
                        record_emp_id = str(record.get('employee_id', '')).strip()
                        record_date = record.get('check_in_date')
                        record_time = record.get('check_in_time')
                        location = record.get('location_name', 'Unknown Location')
                        record_id = record.get('id', 0)
                    
                    # Skip invalid records
                    if not record_emp_id or record_date is None or record_time is None:
                        continue
                    
                    # Parse work type from this record
                    record_base_id, work_type = parse_employee_id_for_work_type(record_emp_id)
                    
                    # Only include records for this base employee
                    if record_base_id == base_employee_id:
                        # Create a simple record dict for processing
                        processed_record = {
                            'id': record_id,
                            'employee_id': record_emp_id,
                            'check_in_date': record_date,
                            'check_in_time': record_time,
                            'location_name': location,
                            'work_type': work_type,
                            'timestamp': datetime.combine(record_date, record_time) if record_date and record_time else datetime.now()
                        }
                        records_by_type[work_type].append(processed_record)
                        
                except Exception as record_error:
                    print(f"⚠️ Error processing record: {record_error}")
                    continue
            
            total_records = sum(len(records_by_type[wt]) for wt in records_by_type)
            print(f"📊 Found {total_records} records - Regular: {len(records_by_type['regular'])}, SP: {len(records_by_type['SP'])}, PW: {len(records_by_type['PW'])}")
            
            # Calculate hours for each work type
            daily_hours = {}
            weekly_totals = []
            current_date = start_date
            current_week_hours = {'regular': [], 'SP': [], 'PW': []}
            
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                
                # Calculate hours for each work type on this day
                hours_by_type = {}
                is_miss_punch_by_type = {}
                
                for work_type in ['regular', 'SP', 'PW']:
                    day_records = [r for r in records_by_type[work_type] 
                                 if r['check_in_date'] == current_date.date()]
                    hours, is_miss_punch = self._calculate_daily_hours_from_records(day_records)
                    hours_by_type[work_type] = hours
                    is_miss_punch_by_type[work_type] = is_miss_punch
                
                # Store daily data with SP/PW support
                total_day_hours = sum(hours_by_type.values())
                daily_hours[date_key] = {
                    'total_minutes': int(total_day_hours * 60),
                    'total_hours': total_day_hours,
                    'regular_hours': hours_by_type['regular'],
                    'sp_hours': hours_by_type['SP'],
                    'pw_hours': hours_by_type['PW'],
                    'is_miss_punch': any(is_miss_punch_by_type.values()),
                    'records_count': sum(len([r for r in records_by_type[wt] if r['check_in_date'] == current_date.date()]) 
                                       for wt in ['regular', 'SP', 'PW']),
                    'miss_punch_details': {
                        'regular': is_miss_punch_by_type['regular'],
                        'SP': is_miss_punch_by_type['SP'],
                        'PW': is_miss_punch_by_type['PW']
                    }
                }
                
                # Add to weekly calculation
                for work_type in ['regular', 'SP', 'PW']:
                    current_week_hours[work_type].append(max(0, hours_by_type[work_type]))
                
                # Check if end of week or end of period
                if current_date.weekday() == 6 or current_date == end_date:
                    week_regular_total = sum(current_week_hours['regular'])
                    week_sp_total = sum(current_week_hours['SP'])
                    week_pw_total = sum(current_week_hours['PW'])
                    
                    # Only regular hours count toward overtime
                    week_regular_hours = min(week_regular_total, 40.0)
                    week_overtime_hours = max(0, week_regular_total - 40.0)
                    
                    weekly_totals.append({
                        'total_hours': week_regular_total + week_sp_total + week_pw_total,
                        'regular_hours': week_regular_hours,
                        'overtime_hours': week_overtime_hours,
                        'sp_hours': week_sp_total,
                        'pw_hours': week_pw_total,
                        'total_minutes': int((week_regular_total + week_sp_total + week_pw_total) * 60),
                        'regular_minutes': int(week_regular_hours * 60),
                        'overtime_minutes': int(week_overtime_hours * 60),
                        'sp_minutes': int(week_sp_total * 60),
                        'pw_minutes': int(week_pw_total * 60)
                    })
                    
                    current_week_hours = {'regular': [], 'SP': [], 'PW': []}
                
                current_date += timedelta(days=1)
            
            # Calculate grand totals
            grand_total_hours = sum(week['total_hours'] for week in weekly_totals)
            grand_regular_hours = sum(week['regular_hours'] for week in weekly_totals)
            grand_overtime_hours = sum(week['overtime_hours'] for week in weekly_totals)
            grand_sp_hours = sum(week['sp_hours'] for week in weekly_totals)
            grand_pw_hours = sum(week['pw_hours'] for week in weekly_totals)
            
            print(f"✅ Employee {employee_id}: Total: {grand_total_hours:.2f}h (Regular: {grand_regular_hours:.2f}h, OT: {grand_overtime_hours:.2f}h, SP: {grand_sp_hours:.2f}h, PW: {grand_pw_hours:.2f}h)")
            
            result = {
                'employee_id': employee_id,
                'base_employee_id': base_employee_id,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'include_travel_time': True,
                'daily_hours': daily_hours,
                'weekly_hours': weekly_totals,
                'grand_totals': {
                    'total_hours': grand_total_hours,
                    'regular_hours': grand_regular_hours,
                    'overtime_hours': grand_overtime_hours,
                    'sp_hours': grand_sp_hours,
                    'pw_hours': grand_pw_hours,
                    'total_minutes': int(grand_total_hours * 60),
                    'regular_minutes': int(grand_regular_hours * 60),
                    'overtime_minutes': int(grand_overtime_hours * 60),
                    'sp_minutes': int(grand_sp_hours * 60),
                    'pw_minutes': int(grand_pw_hours * 60)
                }
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Error calculating working hours for employee {employee_id}: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return self._empty_result(employee_id, start_date, end_date)
    
    def _calculate_daily_hours_from_records(self, day_records: List[Dict]) -> Tuple[float, bool]:
        """Calculate hours for a single day from processed records"""
        if not day_records:
            return 0.0, False
        
        # Sort records by timestamp
        try:
            sorted_records = sorted(day_records, key=lambda r: r['timestamp'])
        except Exception as e:
            print(f"⚠️ Error sorting records: {e}")
            return 0.0, True
        
        # Single record = miss punch
        if len(sorted_records) == 1:
            return 0.0, True
        
        # Calculate complete pairs only
        num_complete_pairs = len(sorted_records) // 2
        total_hours = 0.0
        
        for i in range(0, num_complete_pairs * 2, 2):
            try:
                start_time = sorted_records[i]['timestamp']
                end_time = sorted_records[i + 1]['timestamp']
                
                duration = end_time - start_time
                period_hours = duration.total_seconds() / 3600.0
                
                # Validate reasonable work period
                if 0 < period_hours <= self.max_work_period_hours:
                    total_hours += period_hours
                    
            except Exception as e:
                print(f"⚠️ Error calculating work period: {e}")
                continue
        
        # Round to nearest quarter hour
        total_hours = round(total_hours * 4) / 4
        
        # Determine if miss punch
        is_miss_punch = len(sorted_records) % 2 != 0
        
        return total_hours, is_miss_punch
    
    def _empty_result(self, employee_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Return empty result structure with SP/PW support"""
        base_employee_id, _ = parse_employee_id_for_work_type(employee_id)
        
        return {
            'employee_id': employee_id,
            'base_employee_id': base_employee_id,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'include_travel_time': True,
            'daily_hours': {},
            'weekly_hours': [],
            'grand_totals': {
                'total_hours': 0.0,
                'regular_hours': 0.0,
                'overtime_hours': 0.0,
                'sp_hours': 0.0,
                'pw_hours': 0.0,
                'total_minutes': 0,
                'regular_minutes': 0,
                'overtime_minutes': 0,
                'sp_minutes': 0,
                'pw_minutes': 0
            }
        }
    
    def calculate_all_employees_hours(self, start_date: datetime, end_date: datetime, 
                                      attendance_records: List[Dict]) -> Dict[str, Any]:
        """Calculate working hours for all employees with robust error handling"""
        try:
            print(f"🚀 Starting calculation for all employees with SP/PW support")
            
            # Get unique base employee IDs safely
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
            
            print(f"👥 Found {len(base_employee_ids)} unique base employees")
            
            results = {}
            for base_emp_id in sorted(base_employee_ids):
                try:
                    print(f"\n🔄 Processing base employee {base_emp_id}")
                    results[base_emp_id] = self.calculate_employee_hours(
                        base_emp_id, start_date, end_date, attendance_records
                    )
                except Exception as e:
                    print(f"❌ Error processing employee {base_emp_id}: {e}")
                    results[base_emp_id] = self._empty_result(base_emp_id, start_date, end_date)
                    continue
            
            return {
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d'),
                'include_travel_time': True,
                'employee_count': len(base_employee_ids),
                'employees': results
            }
            
        except Exception as e:
            print(f"❌ Error calculating hours for all employees: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            # Return minimal safe result
            return {
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d'),
                'include_travel_time': True,
                'employee_count': 0,
                'employees': {}
            }