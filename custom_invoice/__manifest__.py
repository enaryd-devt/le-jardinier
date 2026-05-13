{
    'name': 'PrimeTech Invoice Report custom',
    'version': '1.0',
    'summary': 'Custom invoice layout for Odoo 18',
    'author': 'PrimeTech',
    'license': 'LGPL-3',
    'depends': ['account', "sale", "account", "stock", "point_of_sale", "base",],
    'data': [
        "views/custom_report_invoice.xml",
        "views/custom_receipt_payment.xml",
        "views/custom_saleorder.xml",
    ],
    'installable': True,
    'application': False,
}