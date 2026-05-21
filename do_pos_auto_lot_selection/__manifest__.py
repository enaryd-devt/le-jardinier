# -*- coding: utf-8 -*-
{
    'name': 'POS Auto Lot/Serial Selection',
    'version': '18.0.0.1',
    'category': 'Point of Sale',
    'summary': """Automatic lot selection in Point Of sale """,
    'description': """This module automatically selects available Lot/Serial numbers for tracked products in the Point of Sale (POS).""",
    'author': 'Do Incredible',
    'license': 'AGPL-3',
    'company': 'https://www.doincredible.com',
    'website': "https://www.doincredible.com",
    'depends': ['point_of_sale', 'mrp','mrp_product_expiry','product'],
    'data': [
        'views/pos_config_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'do_pos_auto_lot_selection/static/src/**/*.js',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 20,
    'currency': 'EUR',
}
