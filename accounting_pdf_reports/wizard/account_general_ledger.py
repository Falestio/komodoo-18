from odoo import fields, models, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountReportGeneralLedger(models.TransientModel):
    _name = "account.report.general.ledger"
    _inherit = "account.common.account.report"
    _description = "General Ledger Report"

    initial_balance = fields.Boolean(
        string='Include Initial Balances',
        help='If you selected date, this field allow you to add a row '
             'to display the amount of debit/credit/balance that precedes '
             'the filter you have set.'
    )
    sortby = fields.Selection(
        [('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string='Sort by', required=True, default='sort_date'
    )
    journal_ids = fields.Many2many(
        'account.journal', 'account_report_general_ledger_journal_rel',
        'account_id', 'journal_id', string='Journals', required=True
    )

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        records = self.env[data['model']].browse(data.get('ids', []))
        return records, data

    def _print_report(self, data):
        records, data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(landscape=True).report_action(records, data=data)

    def action_export_excel(self):
        """Export General Ledger to Excel"""
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'display_account', 
                                  'initial_balance', 'sortby', 'analytic_account_ids', 'account_ids', 'partner_ids'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        
        # Generate Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        self._generate_excel_report(workbook, data)
        workbook.close()
        output.seek(0)
        
        # Create attachment
        file_name = 'General_Ledger_Report.xlsx'
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

    def _generate_excel_report(self, workbook, data):
        """Generate Excel content for General Ledger"""
        sheet = workbook.add_worksheet('General Ledger')
        
        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFC300',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        content_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        number_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00',
            'align': 'right',
            'valign': 'vcenter'
        })
        account_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8E8E8',
            'border': 1,
            'align': 'left'
        })
        
        # Set column widths
        sheet.set_column('A:A', 12)  # Date
        sheet.set_column('B:B', 10)  # JRNL
        sheet.set_column('C:C', 25)  # Partner
        sheet.set_column('D:D', 15)  # Ref
        sheet.set_column('E:E', 20)  # Move
        sheet.set_column('F:F', 15)  # Debit
        sheet.set_column('G:G', 15)  # Credit
        sheet.set_column('H:H', 15)  # Balance
        
        # Write title
        row = 0
        sheet.merge_range(row, 0, row, 7, 'General Ledger Report', title_format)
        row += 2
        
        # Write headers
        headers = ['Date', 'JRNL', 'Partner', 'Ref', 'Move', 'Debit', 'Credit', 'Balance']
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        row += 1
        
        # Get report data
        report_obj = self.env['report.accounting_pdf_reports.report_general_ledger']
        accounts = self.env['account.account'].search([])
        if data['form'].get('account_ids'):
            accounts = self.env['account.account'].browse(data['form']['account_ids'])
        
        analytic_account_ids = data['form'].get('analytic_account_ids', [])
        partner_ids = data['form'].get('partner_ids', [])
        
        accounts_res = report_obj._get_account_move_entry(
            accounts, analytic_account_ids, partner_ids,
            data['form'].get('initial_balance', False),
            data['form'].get('sortby', 'sort_date'),
            data['form'].get('display_account', 'all')
        )
        
        # Write account data
        for account in accounts_res:
            if account.get('move_lines'):
                # Write account header
                account_name = f"{account.get('code', '')} {account.get('name', '')}"
                sheet.merge_range(row, 0, row, 4, account_name, account_format)
                sheet.write(row, 5, account.get('debit', 0.0), number_format)
                sheet.write(row, 6, account.get('credit', 0.0), number_format)
                sheet.write(row, 7, account.get('balance', 0.0), number_format)
                row += 1
                
                # Write move lines
                for line in account.get('move_lines', []):
                    sheet.write(row, 0, line.get('ldate', ''), content_format)
                    sheet.write(row, 1, line.get('lcode', ''), content_format)
                    sheet.write(row, 2, line.get('partner_name', ''), content_format)
                    sheet.write(row, 3, line.get('lref', ''), content_format)
                    sheet.write(row, 4, line.get('move_name', ''), content_format)
                    sheet.write(row, 5, line.get('debit', 0.0), number_format)
                    sheet.write(row, 6, line.get('credit', 0.0), number_format)
                    sheet.write(row, 7, line.get('balance', 0.0), number_format)
                    row += 1
