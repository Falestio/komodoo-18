from odoo import api, fields, models
from datetime import datetime
import locale


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

    # Debug fields to show raw UTC time (what's actually stored in database)
    check_in_utc = fields.Char(
        string='Check In (Raw UTC)',
        compute='_compute_utc_times',
        help='Raw UTC time stored in database - for debugging timezone issues'
    )
    
    check_out_utc = fields.Char(
        string='Check Out (Raw UTC)',
        compute='_compute_utc_times',
        help='Raw UTC time stored in database - for debugging timezone issues'
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

    @api.depends('check_in', 'check_out')
    def _compute_utc_times(self):
        """Show raw UTC time stored in database for debugging"""
        for record in self:
            record.check_in_utc = str(record.check_in) if record.check_in else ''
            record.check_out_utc = str(record.check_out) if record.check_out else ''

    @api.depends('check_in', 'check_out')
    def _compute_formatted_fields(self):
        """Compute formatted date and time fields for payslip display"""
        # Indonesian day and month names
        days_id = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
        months_id = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                     'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        
        for record in self:
            if record.check_in:
                # Format: Senin, 2 Februari 2026
                day_name = days_id[record.check_in.weekday()]
                day_num = record.check_in.day
                month_name = months_id[record.check_in.month - 1]
                year = record.check_in.year
                record.check_in_date_formatted = f"{day_name}, {day_num} {month_name} {year}"
                
                # Time only: HH:MM
                record.check_in_time_only = record.check_in.strftime('%H:%M')
            else:
                record.check_in_date_formatted = ''
                record.check_in_time_only = ''
            
            if record.check_out:
                record.check_out_time_only = record.check_out.strftime('%H:%M')
            else:
                record.check_out_time_only = ''
