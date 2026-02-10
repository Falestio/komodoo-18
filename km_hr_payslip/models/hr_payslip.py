from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    payslip_attendance_ids = fields.Many2many(
        'hr.attendance',
        'km_payslip_attendance_rel',
        'payslip_id',
        'attendance_id',
        compute='_compute_payslip_attendance_ids',
        string='Attendance in Period',
        help="Attendance records within the payslip period.")
    payslip_overtime_ids = fields.Many2many(
        'hr.overtime',
        'km_payslip_overtime_rel',
        'payslip_id',
        'overtime_id',
        compute='_compute_payslip_overtime_ids',
        string='Overtime in Period',
        help="Overtime records within the payslip period.")
    payslip_leave_ids = fields.Many2many(
        'hr.leave',
        'km_payslip_leave_rel',
        'payslip_id',
        'leave_id',
        compute='_compute_payslip_leave_ids',
        string='Time Off in Period',
        help="Time off records within the payslip period.")

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_payslip_attendance_ids(self):
        """Compute attendance records within the payslip period."""
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                date_from = fields.Datetime.to_datetime(payslip.date_from)
                date_to_end = fields.Datetime.to_datetime(
                    payslip.date_to).replace(hour=23, minute=59, second=59)
                payslip.payslip_attendance_ids = self.env['hr.attendance'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('check_in', '>=', date_from),
                    ('check_in', '<=', date_to_end),
                ], order='check_in asc')
            else:
                payslip.payslip_attendance_ids = False

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_payslip_overtime_ids(self):
        """Compute approved overtime records within the payslip period."""
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                date_from = fields.Datetime.to_datetime(payslip.date_from)
                date_to_end = fields.Datetime.to_datetime(
                    payslip.date_to).replace(hour=23, minute=59, second=59)
                payslip.payslip_overtime_ids = self.env['hr.overtime'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('date_from', '>=', date_from),
                    ('date_from', '<=', date_to_end),
                    ('state', '=', 'approved'),
                ])
            else:
                payslip.payslip_overtime_ids = False

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_payslip_leave_ids(self):
        """Compute validated time off records within the payslip period."""
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                date_from = fields.Datetime.to_datetime(payslip.date_from)
                date_to_end = fields.Datetime.to_datetime(
                    payslip.date_to).replace(hour=23, minute=59, second=59)
                payslip.payslip_leave_ids = self.env['hr.leave'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('date_from', '>=', date_from),
                    ('date_from', '<=', date_to_end),
                    ('state', '=', 'validate'),
                ])
            else:
                payslip.payslip_leave_ids = False
