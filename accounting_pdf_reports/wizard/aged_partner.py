import time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountAgedTrialBalance(models.TransientModel):
    _name = 'account.aged.trial.balance'
    _inherit = 'account.common.partner.report'
    _description = 'Account Aged Trial balance Report'

    period_length = fields.Integer(string='Period Length (days)', required=True, default=30)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))

    def _get_report_data(self, data):
        res = {}
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length'])[0])
        period_length = data['form']['period_length']
        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))
        start = data['form']['date_from']
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and (str((5 - (i + 1)) * period_length) + '-' + str((5 - i) * period_length)) or (
                            '+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_aged_partner_balance').\
            with_context(landscape=True).report_action(self, data=data)

    def action_export_excel(self):
        """Export Aged Partner Balance to Excel"""
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'journal_ids', 'target_move', 
                                   'result_selection', 'period_length'])[0]
        data = self._get_report_data(data)
        
        # Generate Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        self._generate_aged_partner_excel(workbook, data)
        workbook.close()
        output.seek(0)
        
        # Create attachment
        file_name = 'Aged_Partner_Balance_Report.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def _generate_aged_partner_excel(self, workbook, data):
        """Generate Excel content for Aged Partner Balance"""
        sheet = workbook.add_worksheet('Aged Partner Balance')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center'
        })
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#FFC300', 'border': 1, 'align': 'center'
        })
        content_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right'})
        total_format = workbook.add_format({
            'bold': True, 'bg_color': '#D9EAD3', 'border': 1, 'num_format': '#,##0.00', 'align': 'right'
        })
        total_label_format = workbook.add_format({
            'bold': True, 'bg_color': '#D9EAD3', 'border': 1
        })
        
        # Title
        sheet.merge_range('A1:H1', 'AGED PARTNER BALANCE', title_format)
        row = 2
        
        # Info
        sheet.write(row, 0, f"Date: {data['form']['date_from']}")
        sheet.write(row, 4, f"Period Length: {data['form']['period_length']} days")
        row += 1
        
        # Result selection info
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'customer':
            partner_type = 'Receivable Accounts'
        elif result_selection == 'supplier':
            partner_type = 'Payable Accounts'
        else:
            partner_type = 'Receivable and Payable Accounts'
        sheet.write(row, 0, f"Partner's: {partner_type}")
        
        target_move = data['form'].get('target_move', 'all')
        target_move_text = 'All Entries' if target_move == 'all' else 'All Posted Entries'
        sheet.write(row, 4, f"Target Moves: {target_move_text}")
        row += 2
        
        # Headers - Dynamic based on periods
        headers = ['Partners', 'Not due']
        for i in range(4, -1, -1):
            period_data = data['form'].get(str(i), {})
            headers.append(period_data.get('name', ''))
        headers.append('Total')
        
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        row += 1
        
        # Get account type based on result_selection
        if result_selection == 'customer':
            account_types = ['asset_receivable']
        elif result_selection == 'supplier':
            account_types = ['liability_payable']
        else:
            account_types = ['asset_receivable', 'liability_payable']
        
        # Get partner data using the same method as PDF report
        report_model = self.env['report.accounting_pdf_reports.report_agedpartnerbalance']
        partner_ids = data['form'].get('partner_ids', [])
        date_from = data['form']['date_from']
        period_length = data['form']['period_length']
        
        movelines, total, dummy = report_model._get_partner_move_lines(
            account_types, partner_ids, date_from, target_move, period_length
        )
        
        # Write Account Total row first
        if movelines:
            sheet.write(row, 0, 'Account Total', total_label_format)
            sheet.write(row, 1, total[6], total_format)  # Not due (direction)
            sheet.write(row, 2, total[4], total_format)
            sheet.write(row, 3, total[3], total_format)
            sheet.write(row, 4, total[2], total_format)
            sheet.write(row, 5, total[1], total_format)
            sheet.write(row, 6, total[0], total_format)
            sheet.write(row, 7, total[5], total_format)  # Total
            row += 1
        
        # Write partner data - only partners with data (already filtered by _get_partner_move_lines)
        for partner in movelines:
            sheet.write(row, 0, partner.get('name', ''), content_format)
            sheet.write(row, 1, partner.get('direction', 0.0), number_format)  # Not due
            sheet.write(row, 2, partner.get('4', 0.0), number_format)
            sheet.write(row, 3, partner.get('3', 0.0), number_format)
            sheet.write(row, 4, partner.get('2', 0.0), number_format)
            sheet.write(row, 5, partner.get('1', 0.0), number_format)
            sheet.write(row, 6, partner.get('0', 0.0), number_format)
            sheet.write(row, 7, partner.get('total', 0.0), number_format)
            row += 1
        
        # Column widths
        sheet.set_column('A:A', 40)
        sheet.set_column('B:H', 15)
