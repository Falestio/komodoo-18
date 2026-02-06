# -- coding: utf-8 --
################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import datetime, timedelta
from dateutil import relativedelta
import pandas as pd
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.resource.models.utils import HOURS_PER_DAY


class HrOvertime(models.Model):
    """ Model to manage Overtime requests for employees."""
    _name = 'hr.overtime'
    _description = "HR Overtime"
    _inherit = ['mail.thread']

    def _get_employee_domain(self):
        """Get the domain for the employee field based on the current user."""
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)], limit=1)
        domain = [('id', '=', employee.id)]
        if self.env.user.has_group('hr.group_hr_user'):
            domain = []
        return domain

    def _default_employee(self):
        """ Get the default employee based on the current user."""
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)],
                                              limit=1)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """When date_from is set, allow editing of duration and date_to."""
        # Validation is done elsewhere
        if self.date_from and not self.date_to:
            # Initialize date_to to same as date_from if not set
            self.date_to = self.date_from

    @api.onchange('duration_value', 'duration_type')
    def _onchange_duration_value(self):
        """Calculate end date based on duration value."""
        if self.date_from and self.duration_value and self.duration_value > 0:
            start = self.date_from
            if self.duration_type == 'hours':
                # Add hours to date_from
                self.date_to = start + timedelta(hours=self.duration_value)
            elif self.duration_type == 'days':
                # Add days to date_from
                self.date_to = start + timedelta(days=self.duration_value)

    @api.onchange('date_to')
    def _onchange_date_to(self):
        """Calculate duration value when date_to is manually changed."""
        if self.date_from and self.date_to and self.date_to > self.date_from:
            diff = self.date_to - self.date_from
            total_seconds = diff.total_seconds()
            
            if self.duration_type == 'hours':
                # Calculate hours (including fractional hours)
                self.duration_value = total_seconds / 3600  # Convert to hours
            elif self.duration_type == 'days':
                # Calculate days (including fractional days)
                self.duration_value = total_seconds / (24 * 3600)  # Convert to days

    name = fields.Char('Name', readonly=True,
                       help="Name of the overtime request.")
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  domain=_get_employee_domain,
                                  default=lambda
                                      self: self.env.user.employee_id.id,
                                  required=True,
                                  help="Employee for whom the overtime request "
                                       "is made")
    department_id = fields.Many2one('hr.department',
                                    string="Department",
                                    related="employee_id.department_id",
                                    help="Department of the employee.")
    job_id = fields.Many2one('hr.job', string="Job",
                             related="employee_id.job_id",
                             help="Job position of the employee.")
    manager_id = fields.Many2one('res.users', string="Manager",
                                 related="employee_id.parent_id.user_id",
                                 store=True, help="Manager of the employee.")
    current_user_id = fields.Many2one('res.users',
                                      string="Current User",
                                      related='employee_id.user_id',
                                      default=lambda self: self.env.uid,
                                      store=True,
                                      help="User currently logged in.")
    is_current_user = fields.Boolean('Current User ',
                                     help="Boolean field indicating "
                                          "weather the current user is "
                                          "associated with the overtime "
                                          "request.")
    project_id = fields.Many2one('project.project',
                                 string="Project", help="Project associated "
                                                        "with the overtime "
                                                        "request.")
    project_manager_id = fields.Many2one('res.users',
                                         string="Project Manager",
                                         help="Manager of the project "
                                              "associated with the overtime "
                                              "request.")
    contract_id = fields.Many2one('hr.contract', string="Contract",
                                  related="employee_id.contract_id",
                                  help="Contract of the employee")
    date_from = fields.Datetime('Start Date & Time', required=True,
                                help="Start date and time of the overtime request.")
    duration_type = fields.Selection([('hours', 'Hours'), ('days', 'Days')],
                                     string="Duration Type", default="hours",
                                     required=True,
                                     help="Type of duration for the overtime request")
    duration_value = fields.Float('Duration',
                                  help="Number of hours or days for overtime. "
                                       "Leave empty to calculate from end time.",
                                  digits=(10, 2))
    date_to = fields.Datetime('End Date & Time',
                              help="End date and time of the overtime request. "
                                   "Auto-calculated or can be filled manually.")
    days_no_tmp = fields.Float('Hours', compute="_get_days", store=True,
                               help="Temporary field to store the calculated "
                                    "hours for the overtime request.")
    days_no = fields.Float('No. of Days', compute="_get_days", store=True,
                           help="Number of days for the overtime request.")
    desc = fields.Text('Description', help="Description of the overtime "
                                           "request.")
    state = fields.Selection([('draft', 'Draft'),
                              ('f_approve', 'Waiting'),
                              ('approved', 'Approved'),
                              ('refused', 'Refused')], string="state",
                             default="draft", help="State of the overtime "
                                                   "request.")
    cancel_reason = fields.Text('Refuse Reason',
                                help="Reason for refusing "
                                     "the overtime request.")
    leave_id = fields.Many2one('hr.leave.allocation',
                               string="Leave ID", help="Leave associated with "
                                                       "the overtime request.")
    attchd_copy = fields.Binary('Attach A File',
                                help="Attachment file for the overtime request")
    attchd_copy_name = fields.Char('File Name',
                                   help="Name of the attached file")
    type = fields.Selection([('cash', 'Cash'), ('leave', 'Leave')],
                            default="leave", required=True, string="Type",
                            help="Type of the overtime request")
    overtime_type_id = fields.Many2one('overtime.type',
                                       domain="[('type','=',type), "
                                              "('duration_type','=',"
                                              "duration_type)]",
                                       help="Overtime Type")
    public_holiday = fields.Char(string='Public Holiday', readonly=True,
                                 help="Indicates if there are public holidays "
                                      "in the overtime request period")
    attendance_ids = fields.Many2many('hr.attendance',
                                      string='Attendance',
                                      help="Attendance records associated with "
                                           "the overtime request.")
    work_schedule_ids = fields.One2many(
        related='employee_id.resource_calendar_id.attendance_ids',
        help="Work schedule of the employee")
    global_leaves_ids = fields.One2many(
        related='employee_id.resource_calendar_id.global_leave_ids',
        help="Global leaves of the employee")
    cash_hrs_amount = fields.Float(string='Overtime Amount', readonly=True,
                                   help="Amount for overtime based on hours")
    cash_day_amount = fields.Float(string='Overtime Amount', readonly=True,
                                   help="Amount for overtime based on days")
    is_payslip_paid = fields.Boolean('Paid in Payslip', readonly=True,
                                     help="Indicates whether the overtime is paid "
                                          "in the payslip.")

    @api.onchange('employee_id')
    def _get_defaults(self):
        """ Set default values for fields based on the selected employee."""
        for sheet in self:
            if sheet.employee_id:
                sheet.update({
                    'department_id': sheet.employee_id.department_id.id,
                    'job_id': sheet.employee_id.job_id.id,
                    'manager_id': sheet.sudo().employee_id.parent_id.user_id.id,
                })

    @api.depends('project_id')
    def _get_project_manager(self):
        """Update the 'project_manager_id' based on the selected project."""
        for sheet in self:
            if sheet.project_id:
                sheet.update({
                    'project_manager_id': sheet.project_id.user_id.id,
                })

    @api.depends('date_from', 'date_to', 'duration_type')
    def _get_days(self):
        """Calculate the number of days or hours based on the duration type and sync duration_value"""
        for recd in self:
            if recd.date_from and recd.date_to:
                if recd.date_from > recd.date_to:
                    raise ValidationError(
                        'Start Date must be less than End Date')
        for sheet in self:
            if sheet.date_from and sheet.date_to:
                start_dt = fields.Datetime.from_string(sheet.date_from)
                finish_dt = fields.Datetime.from_string(sheet.date_to)
                diff = sheet.date_to - sheet.date_from
                
                # Calculate total hours
                total_seconds = diff.total_seconds()
                total_hours = total_seconds / 3600
                
                # Calculate days with fractional part
                calculated_days = total_hours / 24
                
                # Always store the days value
                sheet.days_no = calculated_days
                
                # Update days_no_tmp based on duration_type
                if sheet.duration_type == 'hours':
                    sheet.days_no_tmp = total_hours
                    # Sync duration_value with total hours
                    if abs(sheet.duration_value - total_hours) > 0.01:  # Avoid infinite loop
                        sheet.duration_value = total_hours
                else:  # days
                    sheet.days_no_tmp = calculated_days
                    # Sync duration_value with total days
                    if abs(sheet.duration_value - calculated_days) > 0.01:  # Avoid infinite loop
                        sheet.duration_value = calculated_days
            else:
                sheet.days_no_tmp = 0.0
                sheet.days_no = 0.0

    @api.onchange('overtime_type_id')
    def _get_hour_amount(self):
        """Calculate the overtime amount based on the selected overtime type,
        duration type, and contract details."""
        if self.overtime_type_id.rule_line_ids and self.duration_type == 'hours':
            for recd in self.overtime_type_id.rule_line_ids:
                if recd.from_hrs < self.days_no_tmp <= recd.to_hrs and self.contract_id:
                    if self.contract_id.over_hour:
                        cash_amount = self.contract_id.over_hour * recd.hrs_amount
                        self.cash_hrs_amount = cash_amount
                    else:
                        raise UserError(
                            _("Hour Overtime Needs Hour Wage in Employee Contract."))
        elif self.overtime_type_id.rule_line_ids and self.duration_type == 'days':
            for recd in self.overtime_type_id.rule_line_ids:
                if recd.from_hrs < self.days_no_tmp <= recd.to_hrs and self.contract_id:
                    if self.contract_id.over_day:
                        cash_amount = self.contract_id.over_day * recd.hrs_amount
                        self.cash_day_amount = cash_amount
                    else:
                        raise UserError(
                            _("Day Overtime Needs Day Wage in Employee Contract."))

    def action_submit_to_finance(self):
        """Submit the overtime request for finance approval."""
        return self.sudo().write({
            'state': 'f_approve'
        })

    def action_approve(self):
        """Approve the overtime request and create a leave record if the type
        is 'leave'"""
        if self.overtime_type_id.type == 'leave':
            if self.duration_type == 'days':
                holiday_vals = {
                    'name': 'Overtime',
                    'holiday_status_id': self.overtime_type_id.leave_type_id.id,
                    'number_of_days': self.days_no_tmp,
                    'notes': self.desc,
                    'employee_id': self.employee_id.id,
                    'state': 'confirm',
                    'date_from': self.date_from.date(),
                    'date_to': self.date_to.date()
                }
            else:
                day_hour = self.days_no_tmp / HOURS_PER_DAY
                holiday_vals = {
                    'name': 'Overtime',
                    'holiday_status_id': self.overtime_type_id.leave_type_id.id,
                    'number_of_days': day_hour,
                    'notes': self.desc,
                    'employee_id': self.employee_id.id,
                    'state': 'confirm',
                    'date_from': self.date_from.date(),
                    'date_to': self.date_to.date()
                }
            holiday = self.env['hr.leave.allocation'].sudo().create(
                holiday_vals)
            self.leave_id = holiday.id
        return self.sudo().write({
            'state': 'approved',
        })

    def action_reject(self):
        """Set the state of the overtime request to 'refused'."""
        self.state = 'refused'

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        """Check if there are overlapping overtime requests for the same
        employee on the same day."""
        for req in self:
            domain = [
                ('date_from', '<=', req.date_to),
                ('date_to', '>=', req.date_from),
                ('employee_id', '=', req.employee_id.id),
                ('id', '!=', req.id),
                ('state', 'not in', ['refused']),
            ]
            no_of_holidays = self.search_count(domain)
            if no_of_holidays:
                raise ValidationError(_(
                    'You can not have 2 Overtime requests that overlaps on '
                    'same day!'))

    @api.model
    def create(self, values):
        """ Create a new overtime request with a unique sequence number"""
        seq = self.env['ir.sequence'].next_by_code('hr.overtime') or '/'
        values['name'] = seq
        return super(HrOvertime, self.sudo()).create(values)

    def unlink(self):
        """Unlink the overtime request, preventing deletion if it's not in
        'draft' state."""
        for overtime in self.filtered(
                lambda overtime: overtime.state != 'draft'):
            raise UserError(
                _('You cannot delete TIL request which is not in draft state.'))
        return super(HrOvertime, self).unlink()

    @api.onchange('date_from', 'date_to', 'employee_id')
    def _onchange_date(self):
        """ Update the 'public_holiday' field based on the presence of public
        holidays in the selected date range.Update the 'attendance_ids' field
        based on the attendance records within the selected date range."""
        holiday = False
        if self.contract_id and self.date_from and self.date_to:
            for leaves in self.contract_id.resource_calendar_id.global_leave_ids:
                leave_dates = pd.date_range(leaves.date_from,
                                            leaves.date_to).date
                overtime_dates = pd.date_range(self.date_from,
                                               self.date_to).date
                for over_time in overtime_dates:
                    for leave_date in leave_dates:
                        if leave_date == over_time:
                            holiday = True
            if holiday:
                self.write({
                    'public_holiday': 'You have Public Holidays in your Overtime request.'})
            else:
                self.write({'public_holiday': ' '})
            hr_attendance = self.env['hr.attendance'].search(
                [('check_in', '>=', self.date_from),
                 ('check_in', '<=', self.date_to),
                 ('employee_id', '=', self.employee_id.id)])
            self.update({
                'attendance_ids': [(6, 0, hr_attendance.ids)]
            })
