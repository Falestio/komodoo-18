# -*- coding: utf-8 -*-
{
    'name': 'Search By Date Range',
    'version': '18.0.1.0',
    'category': 'web',
    'summary': 'Search by date range in List view',
    'description': """
Search by date range in List view
--------------------------------------------------
This module adds date range and numeric range search filters directly in list view.
Features:
- Date/Datetime field range filter
- Numeric field (integer, float, monetary) range filter
- Auto-detect date and numeric fields from list view columns
    """,
    'author': 'Wibicon',
    'website': 'https://wibicon.com',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'search_by_date_range/static/src/components/search_by_date_range.css',
            'search_by_date_range/static/src/components/search_by_date_range.js',
            'search_by_date_range/static/src/components/search_by_date_range.xml',
        ],
        'web.assets_backend_lazy': [
            'search_by_date_range/static/src/components/search_by_date_range_pivot.js',
            'search_by_date_range/static/src/components/search_by_date_range_pivot.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
