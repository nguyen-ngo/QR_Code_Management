#!/usr/bin/env python3
"""
Payroll Excel Exporter
=====================

Enhanced Excel exporter for payroll reports with working hours calculations.
Based on the Java PayrollReport.java implementation.

Features:
- Employee working hours with daily/weekly breakdown
- Regular and overtime hour calculations
- Travel time inclusion options
- Professional Excel formatting
- Multiple report formats
"""

import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from single_checkin_calculator import SingleCheckInCalculator
from logger_handler import log_database_operations


class PayrollExcelExporter:
    """Excel exporter for payroll reports with working hours"""
    
    def __init__(self, company_name: str = "Company Name", contract_name: str = "Default Contract"):
        self.company_name = company_name
        self.contract_name = contract_name
        
        # Excel styling
        self.header1_style = None
        self.header2_style = None
        self.header3_style = None
        self.table_header_style = None
        self.data_style = None
        self.total_style = None
        
    def _setup_styles(self, workbook: Workbook):
        """Setup Excel cell styles"""
        
        # Header 1 style (Company name)
        self.header1_style = {
            'font': Font(name="Arial", size=16, bold=True, color="FFFFFF"),
            'fill': PatternFill(start_color="2F4F4F", end_color="2F4F4F", fill_type="solid"),
            'alignment': Alignment(horizontal="center", vertical="center")
        }
        
        # Header 2 style (Report title)
        self.header2_style = {
            'font': Font(name="Arial", size=14, bold=True, color="FFFFFF"),
            'fill': PatternFill(start_color="4682B4", end_color="4682B4", fill_type="solid"),
            'alignment': Alignment(horizontal="center", vertical="center")
        }
        
        # Header 3 style (Contract and date range)
        self.header3_style = {
            'font': Font(name="Arial", size=12, bold=True),
            'alignment': Alignment(horizontal="center", vertical="center")
        }
        
        # Table header style
        self.table_header_style = {
            'font': Font(name="Arial", size=11, bold=True, color="FFFFFF"),
            'fill': PatternFill(start_color="366092", end_color="366092", fill_type="solid"),
            'alignment': Alignment(horizontal="center", vertical="center"),
            'border': Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin")
            )
        }
        
        # Data style
        self.data_style = {
            'font': Font(name="Arial", size=10),
            'alignment': Alignment(horizontal="center", vertical="center"),
            'border': Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin")
            )
        }
        
        # Total style
        self.total_style = {
            'font': Font(name="Arial", size=11, bold=True),
            'fill': PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid"),
            'alignment': Alignment(horizontal="center", vertical="center"),
            'border': Border(
                left=Side(style="thick"),
                right=Side(style="thick"),
                top=Side(style="thick"),
                bottom=Side(style="thick")
            )
        }
    
    def _apply_style(self, cell, style_dict):
        """Apply a style dictionary to a cell"""
        for attr, value in style_dict.items():
            setattr(cell, attr, value)
    
    @log_database_operations('payroll_excel_export')
    def create_payroll_report(self, start_date: datetime, end_date: datetime, 
                             attendance_records: List[Dict], employee_names: Dict[str, str] = None,
                             include_travel_time: bool = True) -> io.BytesIO:
        """
        Create a comprehensive payroll report with working hours
        
        Args:
            start_date: Report start date
            end_date: Report end date  
            attendance_records: List of attendance records
            employee_names: Dictionary mapping employee_id to full name
            include_travel_time: Whether to include travel time in calculations
            
        Returns:
            BytesIO buffer containing the Excel file
        """
        try:
            print(f"📊 Creating payroll report from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Calculate working hours
            calculator = SingleCheckInCalculator()
            hours_data = calculator.calculate_all_employees_hours(start_date, end_date, attendance_records)
            
            # Create workbook
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "Payroll Report"
            
            # Setup styles
            self._setup_styles(workbook)
            
            # Write report headers
            current_row = self._write_report_headers(worksheet, start_date, end_date)
            
            # Write employee data
            current_row = self._write_employee_payroll_data(worksheet, hours_data, employee_names, current_row)
            
            # Write summary totals
            self._write_summary_totals(worksheet, hours_data, current_row)
            
            # Auto-adjust column widths
            self._auto_adjust_columns(worksheet)
            
            # Save to BytesIO
            excel_buffer = io.BytesIO()
            workbook.save(excel_buffer)
            excel_buffer.seek(0)
            
            print("✅ Payroll report Excel file created successfully")
            return excel_buffer
            
        except Exception as e:
            print(f"❌ Error creating payroll report: {e}")
            raise e
    
    def _write_report_headers(self, worksheet, start_date: datetime, end_date: datetime) -> int:
        """Write report headers and return next row number"""
        current_row = 1
        
        # Company name
        cell = worksheet.cell(row=current_row, column=1, value=self.company_name)
        self._apply_style(cell, self.header1_style)
        worksheet.merge_cells(f'A{current_row}:M{current_row}')
        current_row += 1
        
        # Report title
        cell = worksheet.cell(row=current_row, column=1, value="Payroll Report - Working Hours Summary")
        self._apply_style(cell, self.header2_style)
        worksheet.merge_cells(f'A{current_row}:M{current_row}')
        current_row += 1
        
        # Contract name
        cell = worksheet.cell(row=current_row, column=1, value=self.contract_name)
        self._apply_style(cell, self.header3_style)
        worksheet.merge_cells(f'A{current_row}:M{current_row}')
        current_row += 1
        
        # Date range
        date_range = f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        cell = worksheet.cell(row=current_row, column=1, value=date_range)
        self._apply_style(cell, self.header3_style)
        worksheet.merge_cells(f'A{current_row}:M{current_row}')
        current_row += 2  # Add extra space
        
        return current_row
    
    def _write_employee_payroll_data(self, worksheet, hours_data: Dict, employee_names: Dict[str, str], start_row: int) -> int:
        """Write employee payroll data and return next row number"""
        current_row = start_row
        
        # Table headers
        headers = [
            "#", "Employee ID", "Employee Name", 
            "Week 1 Mon", "Week 1 Tue", "Week 1 Wed", "Week 1 Thu", "Week 1 Fri", "Week 1 Sat", "Week 1 Sun",
            "Week 1 Regular", "Week 1 OT",
            "Week 2 Mon", "Week 2 Tue", "Week 2 Wed", "Week 2 Thu", "Week 2 Fri", "Week 2 Sat", "Week 2 Sun", 
            "Week 2 Regular", "Week 2 OT",
            "Total Regular", "Total OT", "Grand Total"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=current_row, column=col, value=header)
            self._apply_style(cell, self.table_header_style)
        current_row += 1
        
        # Employee data
        counter = 1
        for employee_id, emp_data in hours_data['employees'].items():
            # Employee basic info
            employee_name = employee_names.get(employee_id, f"Employee {employee_id}") if employee_names else f"Employee {employee_id}"
            
            row_data = [
                counter,
                employee_id,
                employee_name
            ]
            
            # Calculate daily hours for two weeks (14 days)
            daily_hours = self._calculate_daily_hours_for_payroll(emp_data, hours_data['period_start'])
            
            # Week 1 daily hours (7 days)
            week1_total = 0
            for day_idx in range(7):
                hours = daily_hours.get(day_idx, 0)
                row_data.append(round(hours, 2))
                week1_total += hours
            
            # Week 1 regular and OT
            week1_regular = min(week1_total, 40.0)
            week1_ot = max(0, week1_total - 40.0)
            row_data.extend([round(week1_regular, 2), round(week1_ot, 2)])
            
            # Week 2 daily hours (7 days)
            week2_total = 0
            for day_idx in range(7, 14):
                hours = daily_hours.get(day_idx, 0)
                row_data.append(round(hours, 2))
                week2_total += hours
            
            # Week 2 regular and OT
            week2_regular = min(week2_total, 40.0)
            week2_ot = max(0, week2_total - 40.0)
            row_data.extend([round(week2_regular, 2), round(week2_ot, 2)])
            
            # Totals
            total_regular = week1_regular + week2_regular
            total_ot = week1_ot + week2_ot
            grand_total = total_regular + total_ot
            row_data.extend([round(total_regular, 2), round(total_ot, 2), round(grand_total, 2)])
            
            # Write row data
            for col, value in enumerate(row_data, 1):
                cell = worksheet.cell(row=current_row, column=col, value=value)
                self._apply_style(cell, self.data_style)
            
            current_row += 1
            counter += 1
        
        return current_row + 1  # Add space before summary
    
    def _calculate_daily_hours_for_payroll(self, emp_data: Dict, start_date_str: str) -> Dict[int, float]:
        """Calculate daily hours for payroll format (14 days)"""
        daily_hours = {}
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        
        for day_idx in range(14):
            current_date = start_date + timedelta(days=day_idx)
            date_key = current_date.strftime('%Y-%m-%d')
            
            if date_key in emp_data['daily_hours']:
                day_data = emp_data['daily_hours'][date_key]
                if not day_data['is_miss_punch']:
                    daily_hours[day_idx] = day_data['total_hours']
                else:
                    daily_hours[day_idx] = 0  # Miss punch = 0 hours
            else:
                daily_hours[day_idx] = 0  # No records = 0 hours
        
        return daily_hours
    
    def _write_summary_totals(self, worksheet, hours_data: Dict, start_row: int):
        """Write summary totals section"""
        current_row = start_row + 1
        
        # Summary header
        cell = worksheet.cell(row=current_row, column=1, value="PAYROLL SUMMARY")
        self._apply_style(cell, self.header2_style)
        worksheet.merge_cells(f'A{current_row}:F{current_row}')
        current_row += 2
        
        # Calculate totals across all employees
        total_employees = len(hours_data['employees'])
        total_regular_hours = 0
        total_overtime_hours = 0
        total_hours = 0
        
        for emp_data in hours_data['employees'].values():
            total_regular_hours += emp_data['grand_totals']['regular_hours']
            total_overtime_hours += emp_data['grand_totals']['overtime_hours']
            total_hours += emp_data['grand_totals']['total_hours']
        
        # Summary data
        summary_data = [
            ("Total Employees:", total_employees),
            ("Total Regular Hours:", round(total_regular_hours, 2)),
            ("Total Overtime Hours:", round(total_overtime_hours, 2)),
            ("Grand Total Hours:", round(total_hours, 2)),
            ("Travel Time Included:", "Yes" if hours_data['include_travel_time'] else "No"),
            ("Report Generated:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ]
        
        for label, value in summary_data:
            cell1 = worksheet.cell(row=current_row, column=1, value=label)
            self._apply_style(cell1, self.total_style)
            cell2 = worksheet.cell(row=current_row, column=2, value=value)
            self._apply_style(cell2, self.total_style)
            current_row += 1
    
    def _auto_adjust_columns(self, worksheet):
        """Auto-adjust column widths"""
        for column in worksheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 20)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    @log_database_operations('detailed_hours_export')
    def create_detailed_hours_report(self, start_date: datetime, end_date: datetime,
                                    attendance_records: List[Dict], employee_names: Dict[str, str] = None,
                                    include_travel_time: bool = True) -> io.BytesIO:
        """
        Create a detailed daily hours report for all employees
        
        Args:
            start_date: Report start date
            end_date: Report end date
            attendance_records: List of attendance records
            employee_names: Dictionary mapping employee_id to full name
            include_travel_time: Whether to include travel time in calculations
            
        Returns:
            BytesIO buffer containing the Excel file
        """
        try:
            print(f"📊 Creating detailed hours report from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Calculate working hours
            calculator = SingleCheckInCalculator()
            hours_data = calculator.calculate_all_employees_hours(start_date, end_date, attendance_records)
            
            # Create workbook
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "Detailed Hours Report"
            
            # Setup styles
            self._setup_styles(workbook)
            
            # Write headers
            current_row = 1
            cell = worksheet.cell(row=current_row, column=1, value=self.company_name)
            self._apply_style(cell, self.header1_style)
            worksheet.merge_cells(f'A{current_row}:J{current_row}')
            current_row += 1
            
            cell = worksheet.cell(row=current_row, column=1, value="Detailed Daily Hours Report")
            self._apply_style(cell, self.header2_style)
            worksheet.merge_cells(f'A{current_row}:J{current_row}')
            current_row += 2
            
            # Table headers
            headers = ["Employee ID", "Employee Name", "Date", "Day of Week", "Total Hours", 
                      "Status", "Records Count", "Regular Hours", "Overtime Hours", "Notes"]
            
            for col, header in enumerate(headers, 1):
                cell = worksheet.cell(row=current_row, column=col, value=header)
                self._apply_style(cell, self.table_header_style)
            current_row += 1
            
            # Write detailed data
            for employee_id, emp_data in hours_data['employees'].items():
                employee_name = employee_names.get(employee_id, f"Employee {employee_id}") if employee_names else f"Employee {employee_id}"
                
                # Sort daily hours by date
                daily_items = sorted(emp_data['daily_hours'].items())
                
                for date_str, day_data in daily_items:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day_name = date_obj.strftime('%A')
                    
                    # Determine status and notes
                    if day_data['is_miss_punch']:
                        status = "Miss Punch"
                        notes = "Missing check-in or check-out"
                        hours = 0
                    elif day_data['records_count'] == 0:
                        status = "No Records"
                        notes = "No attendance records"
                        hours = 0
                    else:
                        status = "Complete"
                        notes = f"{day_data['records_count']} record(s)"
                        hours = day_data['total_hours']
                    
                    # Calculate regular/overtime for this day
                    regular_hours = min(hours, 8.0)  # Daily limit
                    overtime_hours = max(0, hours - 8.0)
                    
                    row_data = [
                        employee_id,
                        employee_name,
                        date_str,
                        day_name,
                        round(hours, 2),
                        status,
                        day_data['records_count'],
                        round(regular_hours, 2),
                        round(overtime_hours, 2),
                        notes
                    ]
                    
                    for col, value in enumerate(row_data, 1):
                        cell = worksheet.cell(row=current_row, column=col, value=value)
                        self._apply_style(cell, self.data_style)
                        
                        # Color code miss punches
                        if status == "Miss Punch":
                            cell.fill = PatternFill(start_color="FFE6E6", end_color="FFE6E6", fill_type="solid")
                        elif status == "No Records":
                            cell.fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
                    
                    current_row += 1
            
            # Auto-adjust columns
            self._auto_adjust_columns(worksheet)
            
            # Save to BytesIO
            excel_buffer = io.BytesIO()
            workbook.save(excel_buffer)
            excel_buffer.seek(0)
            
            print("✅ Detailed hours report Excel file created successfully")
            return excel_buffer
            
        except Exception as e:
            print(f"❌ Error creating detailed hours report: {e}")
            raise e