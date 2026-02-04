{
    'name': 'Komodoo Base Theme',
    'version': '18.0.1.0.0',
    'category': 'Theme',
    'summary': 'Komodoo custom theme based on muk_web_theme',
    'author': 'Komodoo',
    'license': 'LGPL-3',
    'depends': [
        'muk_web_theme',
    ],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'theme_komodoo_base/static/src/webclient/appsbar/appsbar.scss',
            'theme_komodoo_base/static/src/scss/buttons.scss',
            'theme_komodoo_base/static/src/scss/checkbox.scss',
        ],
        'web.assets_frontend': [
            'theme_komodoo_base/static/src/scss/buttons.scss',
            'theme_komodoo_base/static/src/scss/checkbox.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
}
