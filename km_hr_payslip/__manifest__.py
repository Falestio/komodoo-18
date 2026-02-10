{
    'name': 'Komodoo HR Payslip',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Extends payslip form with Attendance, Overtime, and Time Off tabs',
    'description': """
        Extends the payslip form view to show:
        - Worked Days tab with attendance records from the payslip period
        - Overtime tab with approved overtime records from the payslip period
        - Time Off tab with validated leave records from the payslip period
    """,
    'depends': [
        'hr_payroll_community',
        'ohrms_overtime',
        'hr_attendance',
        'hr_holidays',
    ],
    'data': [
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
