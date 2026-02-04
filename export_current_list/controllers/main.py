# -*- coding: utf-8 -*-
import json
import io
from odoo import http
from odoo.http import request, content_disposition


class ExportCurrentListController(http.Controller):
    
    def _format_value_for_export(self, record, field_name, field_type):
        """Format field value for Excel export"""
        value = record[field_name]
        
        if value is None or value is False:
            return '' if field_type != 'boolean' else False
        
        if field_type in ('many2one',):
            return value.display_name if hasattr(value, 'display_name') else str(value)
        elif field_type in ('many2many', 'one2many'):
            return ', '.join(rec.display_name for rec in value) if value else ''
        elif field_type == 'selection':
            field_obj = record._fields[field_name]
            selection_dict = dict(field_obj.selection)
            return selection_dict.get(value, value)
        elif field_type == 'boolean':
            return value
        else:
            return value
    
    @http.route('/web/export/current_list_xls', type='http', auth='user')
    def export_current_list_xls(self, data, token):
        """Export current list view data to Excel"""
        try:
            import xlsxwriter
        except ImportError:
            raise Exception("xlsxwriter library is required. Install it with: pip install xlsxwriter")
        
        data = json.loads(data)
        model_name = data.get('model', 'export')
        headers = data.get('headers', [])
        domain = data.get('domain', [])
        context = data.get('context', {})
        field_names = data.get('field_names', [])
        selected_ids = data.get('selected_ids', [])
        is_domain_selected = data.get('is_domain_selected', False)
        
        # Get Model
        Model = request.env[model_name].with_context(**context)
        
        # Determine which records to export
        if is_domain_selected:
            # Export ALL records matching the domain
            records = Model.search(domain)
        elif selected_ids:
            # Export only selected records by IDs
            records = Model.browse(selected_ids)
        else:
            # Fallback: use domain
            records = Model.search(domain)
        
        # Get field types
        field_types = {fname: Model._fields[fname].type for fname in field_names if fname in Model._fields}
        
        # Prepare rows from records
        rows = []
        for record in records:
            row = []
            for field_name in field_names:
                field_type = field_types.get(field_name, 'char')
                cell_value = self._format_value_for_export(record, field_name, field_type)
                row.append(cell_value)
            rows.append(row)
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Data')
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': 'yyyy-mm-dd',
        })
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            # Set column width based on header length (minimum 12)
            worksheet.set_column(col, col, max(len(str(header)) + 2, 12))
        
        # Write data rows
        for row_idx, row in enumerate(rows, start=1):
            for col_idx, cell_value in enumerate(row):
                if isinstance(cell_value, (int, float)) and not isinstance(cell_value, bool):
                    worksheet.write_number(row_idx, col_idx, cell_value, number_format)
                else:
                    worksheet.write(row_idx, col_idx, cell_value if cell_value else '', cell_format)
        
        # Auto-fit columns based on content
        for col_idx, header in enumerate(headers):
            max_len = len(str(header))
            for row in rows:
                if col_idx < len(row) and row[col_idx]:
                    max_len = max(max_len, len(str(row[col_idx])))
            worksheet.set_column(col_idx, col_idx, min(max_len + 2, 50))
        
        workbook.close()
        output.seek(0)
        
        # Generate filename
        filename = f"{model_name.replace('.', '_')}_export.xlsx"
        
        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ],
            cookies={'fileToken': token}
        )
        
        return response
