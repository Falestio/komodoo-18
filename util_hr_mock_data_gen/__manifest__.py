{
    'name': 'HR Mock Data Generator',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Utilities',
    'summary': 'Generate mock attendance data for testing',
    'description': """
        Generate fake attendance data with customizable parameters:
        - Select employees
        - Set date range
        - Control late percentage
        - Control overtime percentage
        - Respect employee work schedules
    """,
    'depends': [
        'hr',
        'hr_attendance',
        'resource',
    ],
    'data': [
        'views/generator_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'util_hr_mock_data_gen/static/src/js/attendance_generator.js',
            'util_hr_mock_data_gen/static/src/xml/attendance_generator.xml',
            'util_hr_mock_data_gen/static/src/css/attendance_generator.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
