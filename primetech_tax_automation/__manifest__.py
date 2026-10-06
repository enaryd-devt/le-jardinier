{
    'name': 'Fiscalité',
    'version': '18.0.2.1.4',
    'summary': 'Préparation fiscale connectée à la comptabilité, aux factures, au POS et aux règlements',
    'description': '''Préparation et contrôle fiscal pour Odoo 18.

Les règles fiscales utilisent les écritures comptables, la facturation, le Point de Vente,
les journaux de règlement et, lorsqu’il est installé, le module de paie. Les calculs,
précomptes, crédits, ajustements, échéances et sources sont traçables.''',
    'author': 'PrimeTech Services',
    'website': 'https://primetechafrik.com',
    'category': 'Comptabilité',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'account', 'point_of_sale', 'payroll'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/dgi_tva_ir_line_data.xml',
        'wizards/dsf_generation_wizard_views.xml',
        'report/dgi_tva_ir_declaration_report.xml',
        'views/tax_views.xml',
        'views/dgi_tva_ir_declaration_views.xml',
        'views/dsf_mapping_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'primetech_tax_automation/static/src/js/tax_dashboard.js',
            'primetech_tax_automation/static/src/js/year_date_field.js',
            'primetech_tax_automation/static/src/xml/tax_dashboard.xml',
            'primetech_tax_automation/static/src/scss/tax_dashboard.scss',
        ],
    },
    'external_dependencies': {'python': ['openpyxl']},
    'application': True,
    'installable': True,
    'auto_install': False,
}
