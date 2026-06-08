# -*- coding: utf-8 -*-
{
    'name': 'POS Prevent Negative Stock',
    'version': '18.0',
    'summary': 'Block sales of out-of-stock items in POS | Prevent Negative Stock',
    'description': """
- Odoo 16.0+ to 18.0+
- Requires "Point of Sale" & "Inventory" modules
    """,
    'category': 'Point of Sale',
    'author': 'Hamza S',
    'website': 'https://www.youtube.com/channel/UCtxZFzAvIgewoJwlmGvRvwA',  # Replace with your site or Odoo Apps profile
    'license': 'OPL-1',
    'price': 6.00,  # USD
    'currency': 'USD',
    'depends': ['base','point_of_sale', 'stock'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_prevent_negative_stock_hs/static/src/js/pos_negative_stock.js',
        ],
    },
    'images': ['static/description/banner.gif',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'live_test_url':'https://youtu.be/SsHAkRZucJA'
}
