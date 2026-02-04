from odoo import models, api, fields
from datetime import date
import base64
from io import BytesIO
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountTaxReport(models.TransientModel):
    _name = 'account.tax.report.wizard'
    _inherit = "account.common.report"
    _description = 'Tax Report'

    date_from = fields.Date(
        string='Date From', required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1))
    )
    date_to = fields.Date(
        string='Date To', required=True,
        default=lambda self: fields.Date.to_string(date.today())
    )

    def _print_report(self, data):
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)

    def action_export_excel(self):
        """Export Tax Report to Excel"""
        data = {}
        data['form'] = self.read(['date_from', 'date_to', 'target_move'])[0]
        
        # Generate Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        self._generate_tax_excel(workbook, data)
        workbook.close()
        output.seek(0)
        
        # Create attachment
        file_name = 'Tax_Report.xlsx'
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

    def _generate_tax_excel(self, workbook, data):
        """Generate Excel content for Tax Report"""
        sheet = workbook.add_worksheet('Tax Report')
        
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
        sheet.merge_range('A1:C1', 'TAX REPORT', title_format)
        row = 2
        
        # Info
        sheet.write(row, 0, f"Date From: {data['form']['date_from']}")
        sheet.write(row, 2, f"Date To: {data['form']['date_to']}")
        row += 2
        
        # Headers
        headers = ['Tax Name', 'Base Amount', 'Tax Amount']
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        row += 1
        
        # Get tax data
        taxes = self.env['account.tax'].search([])
        
        # Write data (simplified - would need actual computation)
        for tax in taxes:
            sheet.write(row, 0, tax.name, content_format)
            sheet.write(row, 1, 0.0, number_format)
            sheet.write(row, 2, 0.0, number_format)
            row += 1
        
        # Column widths
        sheet.set_column('A:A', 30)
        sheet.set_column('B:C', 18)
