from odoo import api, fields, models
import base64
from io import BytesIO
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter
import logging
_logging = logging.getLogger(__name__)

class AccountingReport(models.TransientModel):
    _name = "accounting.report"
    _inherit = "account.common.report"
    _description = "Accounting Report"

    @api.model
    def _get_account_report(self):
        reports = []
        if self._context.get('active_id'):
            menu = self.env['ir.ui.menu'].browse(self._context.get('active_id')).name
            reports = self.env['account.financial.report'].search([('name', 'ilike', menu)])
        return reports and reports[0] or False

    enable_filter = fields.Boolean(string='Enable Comparison')
    account_report_id = fields.Many2one('account.financial.report', string='Account Reports',
                                        required=True, default=_get_account_report)
    label_filter = fields.Char(string='Column Label', help="This label will be displayed on report to "
                                                           "show the balance computed for the given comparison filter.")
    filter_cmp = fields.Selection([('filter_no', 'No Filters'), ('filter_date', 'Date')],
                                  string='Filter by', required=True, default='filter_no')
    date_from_cmp = fields.Date(string='Date From')
    date_to_cmp = fields.Date(string='Date To')
    debit_credit = fields.Boolean(string='Display Debit/Credit Columns',
                                  help="This option allows you to get more details about "
                                       "the way your balances are computed."
                                       " Because it is space consuming, we do not allow to"
                                       " use it while doing a comparison.")
    enable_report_T = fields.Boolean(string='Enable Balance Sheet Standar (T)',
                                     help="Display balance sheet in horizontal T-format with Assets on left and Liabilities on right")

    def _build_comparison_context(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
            result['strict_range'] = True
        return result

    def check_report(self):
        res = super(AccountingReport, self).check_report()
        data = {}
        data['form'] = self.read(['account_report_id', 'date_from_cmp', 'date_to_cmp', 'journal_ids', 'filter_cmp', 'target_move'])[0]
        for field in ['account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(data)
        res['data']['form']['comparison_context'] = comparison_context
        return res

    def _print_report(self, data):
        data['form'].update(self.read(['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter', 'target_move', 'enable_report_T'])[0])
        
        # Dynamically set paperformat for T-format Balance Sheet
        report_action = self.env.ref('accounting_pdf_reports.action_report_financial')
        if self.enable_report_T and self.account_report_id.name in ['Balance Sheet', 'Neraca']:
            paperformat = self.env.ref('accounting_pdf_reports.paperformat_euro_landscape', raise_if_not_found=False)
            if paperformat:
                # Temporarily update the report action's paperformat
                report_action.write({'paperformat_id': paperformat.id})
        else:
            # Reset to default (no specific paperformat or portrait)
            report_action.write({'paperformat_id': False})
        
        return report_action.report_action(self, data=data, config=False)

    def action_export_excel(self):
        """Export Financial Report to Excel"""
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['account_report_id', 'date_from', 'date_to', 'journal_ids', 
                                   'target_move', 'enable_filter', 'debit_credit', 
                                   'date_from_cmp', 'date_to_cmp', 'filter_cmp', 'label_filter', 'company_id'])[0]
        
        # Prepare data structure for report model
        # Keep account_report_id as single value for later use but store original for building context
        account_report_id_value = data['form']['account_report_id']
        if isinstance(account_report_id_value, tuple):
            account_report_id_value = account_report_id_value[0]
        
        # Build context (needs original data['form'] structure)
        used_context = self._build_contexts(data)
        data['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        
        # Convert to expected format for report model
        data['account_report_id'] = [account_report_id_value]
        data['enable_filter'] = data['form']['enable_filter']
        data['debit_credit'] = data['form']['debit_credit']
        
        if data['form']['enable_filter']:
            comparison_context = self._build_comparison_context(data)
            data['comparison_context'] = comparison_context
        
        # Generate Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        self._generate_financial_excel(workbook, data)
        workbook.close()
        output.seek(0)
        
        # Create attachment
        report_name = self.account_report_id.name or 'Financial_Report'
        file_name = f'{report_name.replace(" ", "_")}.xlsx'
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

    def _generate_financial_excel(self, workbook, data):
        """Generate Excel content for Financial Report (Balance Sheet / P&L)"""
        sheet = workbook.add_worksheet(self.account_report_id.name[:31])  # Excel sheet name limit
        
        # Formats
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center'
        })
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#FFC300', 'border': 1, 'align': 'center'
        })
        account_format = workbook.add_format({
            'bold': True, 'border': 1
        })
        content_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right'})
        
        # Title
        sheet.merge_range('A1:C1', self.account_report_id.name.upper(), title_format)
        row = 2
        
        # Info
        sheet.write(row, 0, f"Date From: {data['form']['date_from'] or ''}")
        sheet.write(row, 2, f"Date To: {data['form']['date_to'] or ''}")
        row += 2
        
        # Headers
        if data['form'].get('debit_credit'):
            headers = ['Name', 'Debit', 'Credit', 'Balance', '%']
        elif data['form'].get('enable_filter'):
            label_filter = data['form'].get('label_filter', 'Comparison')
            headers = ['Name', 'Balance', label_filter, 'Net Change', '%']
        else:
            headers = ['Name', 'Balance', '%']
        
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        row += 1
        
        # Get financial report data
        report_model = self.env['report.accounting_pdf_reports.report_financial']
        report_lines = report_model.get_account_lines(data)
        
        # Calculate total for percentage (like Odoo 10 approach)
        total_parent = 0.0
        for line in report_lines:
            name = line.get('name', '')
            level = line.get('level', 0)
            if isinstance(level, str):
                level = 0
            elif isinstance(level, bool):
                level = int(level)
            # Find the first level 1 parent (Aktiva, Assets, Pendapatan, etc.)
            if name in ['Aktiva', 'AKTIVA', 'Assets', 'ASSETS', 'Pendapatan', 'PENDAPATAN', 'Revenue', 'REVENUE'] or (level == 1 and total_parent == 0):
                total_parent = abs(line.get('balance', 0))
                break
        
        # Write data
        for line in report_lines:
            level = line.get('level', 0)
            # Ensure level is an integer (it might be a string like 'bold')
            if isinstance(level, str):
                # If level is a style string, treat as level 0
                level = 0
            elif isinstance(level, bool):
                # If level is boolean, convert to int
                level = int(level)
            
            indent = '  ' * level
            
            if level == 0:
                name_format = account_format
            else:
                name_format = content_format
            
            sheet.write(row, 0, indent + line.get('name', ''), name_format)
            
            # Calculate percentage against total_parent
            balance = line.get('balance', 0.0)
            percentage = (abs(balance) / total_parent * 100) if total_parent and balance != 0 else 0.0
            
            if data['form'].get('debit_credit'):
                sheet.write(row, 1, line.get('debit', 0.0), number_format)
                sheet.write(row, 2, line.get('credit', 0.0), number_format)
                sheet.write(row, 3, balance, number_format)
                sheet.write(row, 4, f"{percentage:.1f}%" if percentage > 0 else '', content_format)
            elif data['form'].get('enable_filter'):
                sheet.write(row, 1, balance, number_format)
                sheet.write(row, 2, line.get('balance_cmp', 0.0), number_format)
                sheet.write(row, 3, line.get('net_change', 0.0), number_format)
                sheet.write(row, 4, f"{percentage:.1f}%" if percentage > 0 else '', content_format)
            else:
                sheet.write(row, 1, balance, number_format)
                sheet.write(row, 2, f"{percentage:.1f}%" if percentage > 0 else '', content_format)
            
            row += 1
        
        # Column widths
        sheet.set_column('A:A', 50)
        if data['form'].get('debit_credit'):
            sheet.set_column('B:D', 18)
            sheet.set_column('E:E', 10)  # % column
        elif data['form'].get('enable_filter'):
            sheet.set_column('B:D', 18)
            sheet.set_column('E:E', 10)  # % column
        else:
            sheet.set_column('B:B', 18)
            sheet.set_column('C:C', 10)  # % column
