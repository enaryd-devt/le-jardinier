# -*- coding: utf-8 -*-
# Part of Odoo, WiCoders Solutions.
{
    "name": "Sale Order Price Change Restriction",
    "summary": """Restrict Sale price change on orders""",
    "description": """
       When a product is added to a sale order, its price is taken from the applicable pricelist. 
       Only users with price-change rights can modify this price.
    """,
    "author": "Wicoders Solutions",
    "website": "https://www.wicoders.com",
    'license': "AGPL-3",
    "category": "Sales",
    "version": "18.0.1.0.0",
    "data": [
        "security/price_security.xml",
    ],
    "depends": ["sale_management"],
    "images": [
        "static/description/banner.jpeg",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
