from odoo import api, models, fields


class AccountFinancialReport(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"

    @api.depends('parent_id', 'parent_id.level')
    def _get_level(self):
        '''Returns a dictionary with key=the ID of a record and value = the level of this
           record in the tree structure.'''
        for report in self:
            level = 0
            if report.parent_id:
                level = report.parent_id.level + 1
            report.level = level

    def _get_children_by_order(self):
        res = self
        children = self.search([('parent_id', 'in', self.ids)], order='sequence ASC')
        if children:
            for child in children:
                res += child._get_children_by_order()
        
        # Support for horizontal balance sheet (T-format)
        if self.env.context.get('account_financial_report_horizontal_side'):
            res = self._filter_by_side(res)
        
        return res
    
    def _has_exclusively_report_types(self, report_types):
        """Check if report has exclusively certain account types"""
        self.ensure_one()
        if self.type == 'accounts':
            for account in self.account_ids:
                if account.account_type not in report_types:
                    return False
        elif self.type == 'account_type':
            for account_type in self.account_type_ids:
                if account_type.type not in report_types:
                    return False
        elif self.type == 'account_report':
            # Mixed types, rely on siblings filtering
            return True
        return all(
            r._has_exclusively_report_types(report_types)
            for r in self.children_ids
        )
    
    def _filter_by_side(self, reports):
        """Filter reports by side (left/right) for T-format balance sheet"""
        side = self.env.context['account_financial_report_horizontal_side']
        report_types = {
            'left': ['asset_receivable', 'asset_cash', 'asset_current', 
                    'asset_non_current', 'asset_prepayments', 'asset_fixed'],
            'right': ['liability_payable', 'liability_credit_card', 
                     'liability_current', 'liability_non_current', 
                     'equity', 'equity_unaffected']
        }[side]
        
        last_good_report = self.browse([])
        last_bad_report = self.browse([])
        result = self.browse([])
        
        for report in reports:
            if not report.parent_id:
                result += report
            # Special treatment for profit and loss
            elif side == 'right' and report.name in ['Income', 'Profit and Loss', 'Profit (Loss) to report']:
                result += report
            elif side == 'left' and report.name in ['Expense']:
                last_bad_report = report
            # Don't check children if we already checked the parent
            elif report.parent_id == last_bad_report:
                continue
            elif report.parent_id == last_good_report or \
                    report._has_exclusively_report_types(report_types):
                last_good_report = report
                result += report
            else:
                last_bad_report = report
        
        return result

    name = fields.Char('Report Name', required=True, translate=True)
    parent_id = fields.Many2one('account.financial.report', 'Parent')
    children_ids = fields.One2many('account.financial.report', 'parent_id', 'Account Report')
    sequence = fields.Integer('Sequence')
    level = fields.Integer(compute='_get_level', string='Level', store=True, recursive=True)
    type = fields.Selection([
        ('sum', 'View'),
        ('accounts', 'Accounts'),
        ('account_type', 'Account Type'),
        ('account_report', 'Report Value'),
        ], 'Type', default='sum')
    account_ids = fields.Many2many(
        'account.account', 'account_account_financial_report',
        'report_line_id', 'account_id', 'Accounts'
    )
    account_report_id = fields.Many2one('account.financial.report', 'Report Value')
    account_type_ids = fields.Many2many(
        'account.account.type', 'account_account_financial_report_type',
        'report_id', 'account_type_id', 'Account Types'
    )
    report_domain = fields.Char(string="Report Domain")
    sign = fields.Selection(
        [('-1', 'Reverse balance sign'), ('1', 'Preserve balance sign')], 'Sign on Reports',
        required=True, default='1',
        help='For accounts that are typically more debited than credited and that you would '
             'like to print as negative amounts in your reports, you should reverse the sign '
             'of the balance; e.g.: Expense account. The same applies for accounts that are '
             'typically more credited than debited and that you would like to print as positive '
             'amounts in your reports; e.g.: Income account.'
    )
    display_detail = fields.Selection([
        ('no_detail', 'No detail'),
        ('detail_flat', 'Display children flat'),
        ('detail_with_hierarchy', 'Display children with hierarchy')
        ], 'Display details', default='detail_flat')
    style_overwrite = fields.Selection([
        ('0', 'Automatic formatting'),
        ('1', 'Main Title 1 (bold, underlined)'),
        ('2', 'Title 2 (bold)'),
        ('3', 'Title 3 (bold, smaller)'),
        ('4', 'Normal Text'),
        ('5', 'Italic Text (smaller)'),
        ('6', 'Smallest Text'),
        ], 'Financial Report Style', default='0',
        help="You can set up here the format you want this record to be displayed. "
             "If you leave the automatic formatting, it will be computed based on the "
             "financial reports hierarchy (auto-computed field 'level').")
    children_ids = fields.One2many('account.financial.report', 'parent_id', string='Children')

