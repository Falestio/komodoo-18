{
	'name': 'KM HR Attendance Dashboard',
	'version': '18.0.1.0.0',
	'category': 'Human Resources/Attendance',
	'summary': 'Attendance dashboard and employee attendance history',
	'author': 'Komodoo',
	'license': 'LGPL-3',
	'depends': [
		'km_hr_attendance',
	],
	'data': [
		'views/attendance_dashboard_views.xml',
	],
	'assets': {
		'web.assets_backend': [
			'km_hr_attendance_dashboard/static/src/css/attendance_dashboard.css',
			'km_hr_attendance_dashboard/static/src/js/attendance_dashboard.js',
			'km_hr_attendance_dashboard/static/src/js/employee_attendance_history.js',
			'km_hr_attendance_dashboard/static/src/xml/attendance_dashboard.xml',
			'km_hr_attendance_dashboard/static/src/xml/employee_attendance_history.xml',
		],
	},
	'installable': True,
	'auto_install': False,
}
