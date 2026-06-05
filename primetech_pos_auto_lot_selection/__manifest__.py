# -*- coding: utf-8 -*-
{
    'name': 'POS Auto Lot/Serial Selection and block sale out stock',
    'version': '18.0.0.1',
    'category': 'Point of Sale',
    'summary': """Automatic lot selection in Point Of sale """,
    'description': """This module automatically selects available Lot/Serial numbers for tracked products in the Point of Sale (POS).""",
    'author': 'PrimeTech',
    'license': 'AGPL-3',
    'company': 'https://www.primetechafrik.com',
    'website': "https://www.primetechafrik.com",
    'depends': ['point_of_sale', 'product'],
    'data': [
        'views/pos_config_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'primetech_pos_auto_lot_selection/static/src/**/*.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 20000,
    'currency': 'XAF',
}
