from odoo import fields, models, api, _
import base64
from io import BytesIO
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountPartnerLedger(models.TransientModel):
    _name = "account.report.partner.ledger"
    _inherit = "account.common.partner.report"
    _description = "Account Partner Ledger"

    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on "
                                          "report if the currency differs from "
                                          "the company currency.")
    reconciled = fields.Boolean('Reconciled Entries')

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled,
                             'amount_currency': self.amount_currency})
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_partnerledger').with_context(landscape=True).\
            report_action(self, data=data)

    def action_export_excel(self):
        """Export Partner Ledger to Excel"""
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 
                                   'result_selection', 'reconciled', 'amount_currency', 'partner_ids'])[0]
        
        # Build context for filtering
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        
        # Generate Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        self._generate_partner_ledger_excel(workbook, data)
        workbook.close()
        output.seek(0)
        
        # Create attachment
        file_name = 'Partner_Ledger_Report.xlsx'
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

    def _generate_partner_ledger_excel(self, workbook, data):
        """Generate Excel content for Partner Ledger"""
        sheet = workbook.add_worksheet('Partner Ledger')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center'
        })
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#FFC300', 'border': 1, 'align': 'center'
        })
        partner_format = workbook.add_format({
            'bold': True, 'bg_color': '#E0E0E0', 'border': 1
        })
        content_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right'})
        
        # Title
        sheet.merge_range('A1:G1', 'PARTNER LEDGER', title_format)
        row = 2
        
        # Headers
        headers = ['Date', 'JRNL', 'Account', 'Ref', 'Debit', 'Credit', 'Balance']
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        row += 1
        
        # Get partners with transactions (same logic as print report)
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        
        # Determine account types based on result_selection
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'customer':
            account_types = ['asset_receivable']
        elif result_selection == 'supplier':
            account_types = ['liability_payable']
        else:
            account_types = ['asset_receivable', 'liability_payable']
        
        # Get account IDs for the selected types
        self.env.cr.execute("""
            SELECT a.id
            FROM account_account a
            WHERE a.account_type IN %s
            AND NOT a.deprecated""", (tuple(account_types),))
        account_ids = [a for (a,) in self.env.cr.fetchall()]
        
        move_state = ['posted'] if data['form'].get('target_move', 'all') == 'posted' else ['draft', 'posted']
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        params = [tuple(move_state), tuple(account_ids)] + query_get_data[2]
        
        query = """
            SELECT DISTINCT "account_move_line".partner_id
            FROM """ + query_get_data[0] + """, account_account AS account, account_move AS am
            WHERE "account_move_line".partner_id IS NOT NULL
                AND "account_move_line".account_id = account.id
                AND am.id = "account_move_line".move_id
                AND am.state IN %s
                AND "account_move_line".account_id IN %s
                AND NOT account.deprecated
                AND """ + query_get_data[1] + reconcile_clause
        
        self.env.cr.execute(query, tuple(params))
        
        if data['form'].get('partner_ids'):
            partner_ids = data['form']['partner_ids']
        else:
            partner_ids = [res['partner_id'] for res in self.env.cr.dictfetchall()]
        
        partners = self.env['res.partner'].browse(partner_ids).sorted(key=lambda x: (x.ref or '', x.name or ''))
        
        # Prepare data structure similar to print report
        data['computed'] = {
            'move_state': move_state,
            'account_ids': account_ids,
            'ACCOUNT_TYPE': account_types
        }
        
        for partner in partners:
            partner_name = (partner.ref or '') + ' - ' + (partner.name or '')
            sheet.write(row, 0, partner_name, partner_format)
            sheet.merge_range(row, 1, row, 6, '', partner_format)
            row += 1
            
            lines = self._get_partner_lines(data, partner)
            
            if not lines:
                sheet.write(row, 0, 'No transactions', content_format)
                sheet.merge_range(row, 1, row, 6, '', content_format)
                row += 1
            else:
                balance = 0.0
                for line in lines:
                    sheet.write(row, 0, line.get('date', ''), content_format)
                    sheet.write(row, 1, line.get('code', ''), content_format)
                    sheet.write(row, 2, line.get('a_name', ''), content_format)
                    sheet.write(row, 3, line.get('displayed_name', ''), content_format)
                    sheet.write(row, 4, line.get('debit', 0.0), number_format)
                    sheet.write(row, 5, line.get('credit', 0.0), number_format)
                    balance += line.get('debit', 0.0) - line.get('credit', 0.0)
                    sheet.write(row, 6, balance, number_format)
                    row += 1
                
                total_debit = sum(l.get('debit', 0.0) for l in lines)
                total_credit = sum(l.get('credit', 0.0) for l in lines)
                total_balance = total_debit - total_credit
                
                sheet.write(row, 0, 'Total ' + partner.name, partner_format)
                sheet.merge_range(row, 1, row, 3, '', partner_format)
                sheet.write(row, 4, total_debit, number_format)
                sheet.write(row, 5, total_credit, number_format)
                sheet.write(row, 6, total_balance, number_format)
                row += 1
            
            row += 1
        
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 8)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:G', 15)
    
    def _get_partner_lines(self, data, partner):
        """Get transaction lines for a specific partner (similar to print report's _lines method)"""
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        params = [partner.id, tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        
        query = """
            SELECT "account_move_line".id, "account_move_line".date, j.code, acc.name->>'en_US' as a_name, 
                   "account_move_line".ref, m.name as move_name, "account_move_line".name, 
                   "account_move_line".debit, "account_move_line".credit
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
            LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
            LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
            WHERE "account_move_line".partner_id = %s
                AND m.state IN %s
                AND "account_move_line".account_id IN %s 
                AND """ + query_get_data[1] + reconcile_clause + """
            ORDER BY "account_move_line".date"""
        
        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        
        # Format the results
        for r in res:
            r['displayed_name'] = '-'.join(
                str(r[field_name]) for field_name in ('move_name', 'ref', 'name')
                if r[field_name] not in (None, '', '/')
            )
        
        return res
