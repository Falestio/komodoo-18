from odoo import models, fields, api

class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    is_public_holiday = fields.Boolean(string='Is Public Holiday', default=False)
    holiday_source = fields.Char(string='Holiday Source', default='Manual')
