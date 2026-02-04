from odoo import fields, models


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
