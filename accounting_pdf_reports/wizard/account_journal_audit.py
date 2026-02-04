from odoo import fields, models, api
import base64
from io import BytesIO
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountPrintJournal(models.TransientModel):
    _name = "account.print.journal"
    _inherit = "account.common.journal.report"
    _description = "Account Print Journal"

    sort_selection = fields.Selection([('date', 'Date'), ('move_name', 'Journal Entry Number')],
                                      'Entries Sorted by', required=True, default='move_name')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True,
                                   default=lambda self: self.env['account.journal'].search([('type', 'in', ['sale', 'purchase'])]))

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_journal').with_context(landscape=True).report_action(self, data=data)

    def action_export_excel(self):
        """Export Journal Audit to Excel"""
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 
                                   'amount_currency', 'sort_selection'])[0]
        
        # Generate Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        self._generate_journal_excel(workbook, data)
        workbook.close()
        output.seek(0)
        
        # Create attachment
        file_name = 'Journal_Audit_Report.xlsx'
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

    def _generate_journal_excel(self, workbook, data):
        """Generate Excel content for Journal Audit"""
        sheet = workbook.add_worksheet('Journal Audit')
        
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
        sheet.merge_range('A1:F1', 'JOURNAL AUDIT', title_format)
        row = 2
        
        # Headers
        headers = ['Date', 'Move', 'Entry Label', 'Account', 'Debit', 'Credit']
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        row += 1
        
        # Get journals
        journal_ids = data['form'].get('journal_ids', [])
        journals = self.env['account.journal'].browse(journal_ids)
        
        # Write data for each journal
        for journal in journals:
            sheet.write(row, 0, f"Journal: {journal.name}", header_format)
            sheet.merge_range(row, 1, row, 5, '', header_format)
            row += 1
            
            # Placeholder for journal lines
            sheet.write(row, 0, 'No entries', content_format)
            row += 2
        
        # Column widths
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 25)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:F', 15)
