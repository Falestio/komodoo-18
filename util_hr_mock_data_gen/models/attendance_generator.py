import random
from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class AttendanceGenerator(models.AbstractModel):
    _name = 'util.attendance.generator'
    _description = 'Attendance Mock Data Generator'

    @api.model
    def get_employees(self):
        """Get list of active employees"""
        employees = self.env['hr.employee'].search([('active', '=', True)], order='name')
        return [{
            'id': emp.id,
            'name': emp.name,
            'department': emp.department_id.name if emp.department_id else '',
            'job': emp.job_id.name if emp.job_id else '',
        } for emp in employees]

    def _is_holiday(self, date, employee=None):
        """Check if date is a public holiday"""
        domain = [
            ('date_from', '<=', datetime.combine(date, time.max)),
            ('date_to', '>=', datetime.combine(date, time.min)),
        ]
        if employee:
            domain.append('|')
            domain.append(('resource_id', '=', False))
            domain.append(('resource_id', '=', employee.resource_id.id))
        else:
            domain.append(('resource_id', '=', False))
        
        return bool(self.env['resource.calendar.leaves'].search(domain, limit=1))

    def _daterange(self, date_from, date_to):
        """Generate date range"""
        current = date_from
        while current <= date_to:
            yield current
            current += timedelta(days=1)

    @api.model
    def generate_attendance(self, params):
        """Generate mock attendance data
        
        :param params: dict with keys:
            - employee_ids: list of employee IDs
            - date_from: start date (string)
            - date_to: end date (string)
            - check_in_hour: expected check-in hour (0-23)
            - check_in_minute: expected check-in minute (0-59)
            - check_out_hour: expected check-out hour (0-23)
            - check_out_minute: expected check-out minute (0-59)
            - late_percentage: percentage of late check-ins (0-100)
            - overtime_percentage: percentage with overtime (0-100)
            - randomize: boolean to enable randomization
            - variance_minutes: variance in check-in/out times
            - delete_existing: boolean to delete existing attendance in period
        """
        try:
            employee_ids = params.get('employee_ids', [])
            date_from = fields.Date.from_string(params.get('date_from'))
            date_to = fields.Date.from_string(params.get('date_to'))
            check_in_hour = params.get('check_in_hour', 8)
            check_in_minute = params.get('check_in_minute', 0)
            check_out_hour = params.get('check_out_hour', 17)
            check_out_minute = params.get('check_out_minute', 0)
            late_percentage = params.get('late_percentage', 10)
            overtime_percentage = params.get('overtime_percentage', 20)
            randomize = params.get('randomize', True)
            variance_minutes = params.get('variance_minutes', 30)
            delete_existing = params.get('delete_existing', False)
            
            if not employee_ids:
                raise UserError('Please select at least one employee')
            
            if date_from > date_to:
                raise UserError('Start date must be before end date')
            
            employees = self.env['hr.employee'].browse(employee_ids)
            
            # Delete existing attendance if requested
            if delete_existing:
                existing = self.env['hr.attendance'].search([
                    ('employee_id', 'in', employee_ids),
                    ('check_in', '>=', datetime.combine(date_from, time.min)),
                    ('check_in', '<=', datetime.combine(date_to, time.max)),
                ])
                existing.unlink()
            
            generated_count = 0
            skipped_count = 0
            
            for employee in employees:
                for work_date in self._daterange(date_from, date_to):
                    # Skip weekends (Saturday=5, Sunday=6)
                    if work_date.weekday() >= 5:
                        skipped_count += 1
                        continue
                    
                    # Skip holidays
                    if self._is_holiday(work_date, employee):
                        skipped_count += 1
                        continue
                    
                    # Check if attendance already exists for this employee on this date
                    existing_attendance = self.env['hr.attendance'].search([
                        ('employee_id', '=', employee.id),
                        ('check_in', '>=', datetime.combine(work_date, time.min)),
                        ('check_in', '<', datetime.combine(work_date + timedelta(days=1), time.min)),
                    ], limit=1)
                    
                    if existing_attendance:
                        skipped_count += 1
                        continue
                    
                    # Determine if this day should be late
                    is_late = randomize and (random.randint(0, 100) < late_percentage)
                    
                    # Determine if this day should have overtime
                    has_overtime = randomize and (random.randint(0, 100) < overtime_percentage)
                    
                    # Generate check-in time
                    check_in_dt = datetime.combine(work_date, time(check_in_hour, check_in_minute))
                    
                    # Apply variance for check-in
                    if is_late:
                        # Add minutes to make late (5-60 minutes)
                        variance = random.randint(5, 60)
                    else:
                        # Subtract minutes to make early (never late when not marked as late)
                        variance = random.randint(-variance_minutes, -1) if randomize else 0
                    
                    check_in_dt = check_in_dt + timedelta(minutes=variance)
                    
                    # Generate check-out time
                    check_out_dt = datetime.combine(work_date, time(check_out_hour, check_out_minute))
                    
                    # Add overtime if applicable
                    if has_overtime:
                        overtime_minutes = random.randint(30, 180)  # 0.5 to 3 hours
                        check_out_dt = check_out_dt + timedelta(minutes=overtime_minutes)
                    
                    # Apply variance to checkout
                    checkout_variance = random.randint(-variance_minutes, variance_minutes) if randomize else 0
                    check_out_dt = check_out_dt + timedelta(minutes=checkout_variance)
                    
                    # Create attendance record
                    self.env['hr.attendance'].create({
                        'employee_id': employee.id,
                        'check_in': check_in_dt,
                        'check_out': check_out_dt,
                    })
                    generated_count += 1
            
            return {
                'success': True,
                'generated': generated_count,
                'skipped': skipped_count,
                'message': f'Successfully generated {generated_count} attendance records ({skipped_count} days skipped)',
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error: {str(e)}',
            }
