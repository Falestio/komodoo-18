from odoo import fields, models, api
import base64
from io import BytesIO
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountBalanceReport(models.TransientModel):
    _name = 'account.balance.report'
    _inherit = "account.common.account.report"
    _description = 'Trial Balance Report'

    journal_ids = fields.Many2many(
        'account.journal', 'account_balance_report_journal_rel',
        'account_id', 'journal_id',
        string='Journals', required=True, default=[]
    )
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'account_trial_balance_analytic_rel', string='Analytic Accounts'
    )

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))
        return records, data

    def _print_report(self, data):
        records, data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_trial_balance').report_action(records, data=data)

    def action_export_excel(self):
        """Export Trial Balance to Excel"""
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'display_account'])[0]
        
        # Generate Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        self._generate_trial_balance_excel(workbook, data)
        workbook.close()
        output.seek(0)
        
        # Create attachment
        file_name = 'Trial_Balance_Report.xlsx'
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

    def _generate_trial_balance_excel(self, workbook, data):
        """Generate Excel content for Trial Balance"""
        sheet = workbook.add_worksheet('Trial Balance')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center'
        })
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#FFC300', 'border': 1, 'align': 'center'
        })
        content_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right'})
        
        # Title
        sheet.merge_range('A1:E1', 'TRIAL BALANCE', title_format)
        row = 2
        
        # Info
        sheet.write(row, 0, f"Date From: {data['form']['date_from'] or ''}")
        sheet.write(row, 3, f"Date To: {data['form']['date_to'] or ''}")
        row += 2
        
        # Headers
        headers = ['Code', 'Account', 'Debit', 'Credit', 'Balance']
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        row += 1
        
        # Get accounts
        display_account = data['form'].get('display_account', 'all')
        accounts = self.env['account.account'].search([])
        
        report_model = self.env['report.accounting_pdf_reports.report_trialbalance']
        account_res = report_model._get_accounts(accounts, display_account)
        
        # Write data
        total_debit = 0.0
        total_credit = 0.0
        total_balance = 0.0
        
        for account in account_res:
            sheet.write(row, 0, account.get('code', ''), content_format)
            sheet.write(row, 1, account.get('name', ''), content_format)
            sheet.write(row, 2, account.get('debit', 0.0), number_format)
            sheet.write(row, 3, account.get('credit', 0.0), number_format)
            sheet.write(row, 4, account.get('balance', 0.0), number_format)
            
            total_debit += account.get('debit', 0.0)
            total_credit += account.get('credit', 0.0)
            total_balance += account.get('balance', 0.0)
            row += 1
        
        # Total row
        sheet.write(row, 0, 'Total', header_format)
        sheet.write(row, 1, '', header_format)
        sheet.write(row, 2, total_debit, number_format)
        sheet.write(row, 3, total_credit, number_format)
        sheet.write(row, 4, total_balance, number_format)
        
        # Column widths
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 40)
        sheet.set_column('C:E', 18)
