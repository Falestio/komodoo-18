{
    'name': 'Indonesian Public Holiday Data',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Fetch Indonesian public holiday data',
    'license': 'LGPL-3',
    'description': """
        This module fetches Indonesian public holiday data from an API.
    """,
    'author': 'Falestio Hanif Al Hakim',
    'website': 'https://falestio.my.id',

    'depends': ['web', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/fetch_holiday_wizard_views.xml',
        'views/resource_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_backend': [
            'get_indonesian_public_holiday_data/static/src/resource_calendar_leave_list_view.js',
            'get_indonesian_public_holiday_data/static/src/resource_calendar_leave_list_view.xml',
        ],
    },
}
