from odoo import api, fields, models
from datetime import datetime, time, timedelta


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    checkin_photo = fields.Image(
        string='Check-in Photo',
        help='Photo taken during check-in'
    )

    checkout_photo = fields.Image(
        string='Check-out Photo',
        help='Photo taken during check-out'
    )

    is_late = fields.Boolean(
        string='Is Late',
        compute='_compute_is_late',
        store=True,
        help='True if employee checked in more than 1 minute after scheduled time'
    )

    # Formatted fields for payslip display
    check_in_date_formatted = fields.Char(
        string='Date',
        compute='_compute_formatted_fields',
        help='Formatted date for display'
    )
    
    check_in_time_only = fields.Char(
        string='Check In Time',
        compute='_compute_formatted_fields',
        help='Check in time only'
    )
    
    check_out_time_only = fields.Char(
        string='Check Out Time',
        compute='_compute_formatted_fields',
        help='Check out time only'
    )

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_is_late(self):
        """Check if employee is late based on working schedule (>1 minute = late)
        Handles multiple attendance periods per day (Morning, Break, Afternoon)
        Converts check_in to working schedule timezone before comparison"""
        from pytz import timezone, utc
        
        for record in self:
            record.is_late = False
            if not record.check_in or not record.employee_id:
                continue
            
            try:
                # Get calendar and timezone
                calendar = record.employee_id.resource_calendar_id or record.employee_id.company_id.resource_calendar_id
                if not calendar:
                    continue
                
                tz_name = calendar.tz or 'UTC'
                tz = timezone(tz_name)
                
                # Convert check_in from UTC to working schedule timezone
                check_in_utc = utc.localize(record.check_in.replace(tzinfo=None))
                check_in_tz = check_in_utc.astimezone(tz)
                
                # Get work date and time in the working schedule timezone
                work_date = check_in_tz.date()
                check_in_time_decimal = check_in_tz.hour + check_in_tz.minute / 60.0
                
                # Get all scheduled periods for this weekday (0=Monday)
                weekday = str(work_date.weekday())
                lines = calendar.attendance_ids.filtered(
                    lambda att: att.dayofweek == weekday
                    and not att.display_type
                    and att.hour_from is not None
                    and att.hour_to is not None
                    and att.hour_from < att.hour_to
                    and (not att.date_from or att.date_from <= work_date)
                    and (not att.date_to or att.date_to >= work_date)
                ).sorted('hour_from')
                
                if not lines:
                    continue
                
                # Find which period the check-in falls into
                relevant_period = None
                for line in lines:
                    # Check if check-in is within or after this period's start
                    if check_in_time_decimal >= line.hour_from:
                        # This could be the relevant period
                        relevant_period = line
                        # If check-in is before the period ends, use this period
                        if check_in_time_decimal <= line.hour_to:
                            break
                
                # If no relevant period found, use the first period
                if not relevant_period:
                    relevant_period = lines[0]
                
                # Get scheduled start time for the relevant period
                hour_from = relevant_period.hour_from
                hours = int(hour_from)
                minutes = int((hour_from - hours) * 60)
                
                # Create scheduled start time in the working schedule timezone
                scheduled_start_tz = tz.localize(datetime.combine(work_date, time(hours, minutes, 0)))
                
                # Check if late (more than 1 minute after scheduled start)
                late_threshold = timedelta(minutes=1)
                if check_in_tz > (scheduled_start_tz + late_threshold):
                    record.is_late = True
            except Exception:
                record.is_late = False
                continue

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_formatted_fields(self):
        """Compute formatted date and time fields for payslip display
        Adjusts times based on working schedule timezone"""
        from pytz import timezone, utc
        
        # Indonesian day and month names
        days_id = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
        months_id = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        
        for record in self:
            if record.check_in:
                calendar = record.employee_id.resource_calendar_id or record.employee_id.company_id.resource_calendar_id
                tz_name = calendar.tz if calendar else 'UTC'
                tz = timezone(tz_name)
                
                check_in_utc = utc.localize(record.check_in.replace(tzinfo=None))
                check_in_tz = check_in_utc.astimezone(tz)
                
                day_name = days_id[check_in_tz.weekday()]
                day_num = check_in_tz.day
                month_name = months_id[check_in_tz.month - 1]
                year = check_in_tz.year
                record.check_in_date_formatted = f"{day_name}, {day_num} {month_name} {year}"
                
                # Format time in working schedule timezone: HH:MM
                record.check_in_time_only = check_in_tz.strftime('%H:%M')
            else:
                record.check_in_date_formatted = ''
                record.check_in_time_only = ''
            
            if record.check_out:
                calendar = record.employee_id.resource_calendar_id or record.employee_id.company_id.resource_calendar_id
                tz_name = calendar.tz if calendar else 'UTC'
                tz = timezone(tz_name)
                
                check_out_utc = utc.localize(record.check_out.replace(tzinfo=None))
                check_out_tz = check_out_utc.astimezone(tz)
                
                record.check_out_time_only = check_out_tz.strftime('%H:%M')
            else:
                record.check_out_time_only = ''
