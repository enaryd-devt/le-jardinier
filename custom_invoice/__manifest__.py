{
    'name': 'PrimeTech Invoice Report custom',
    'version': '1.0',
    'summary': 'Custom invoice layout for Odoo 18',
    'author': 'PrimeTech',
    'depends': ['account'],
    'data': [
        "views/custom_report_invoice.xml",
    ],
    'installable': True,
    'application': False,
}