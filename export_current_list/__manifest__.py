# -*- coding: utf-8 -*-
{
    'name': 'Export Current List View',
    'version': '18.0.1.0.0',
    'category': 'Web',
    'summary': 'Export selected rows from list view to Excel',
    'description': """
Export Current List View to Excel
=================================
This module adds a button to export selected rows from list view to Excel file.

Features:
- Export only selected (checked) rows
- Export only visible columns in current list view
- Maintains column order as displayed
- Supports all field types including numeric, date, boolean
    """,
    'author': 'Wibicon',
    'website': 'https://wibicon.com',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'export_current_list/static/src/components/export_current_list.js',
            'export_current_list/static/src/components/export_current_list.xml',
            'export_current_list/static/src/components/export_current_list.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
