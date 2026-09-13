{
    "name": "PrimeTech Mass Bank Reconciliation",
    "summary": "Apply one manual counterpart account to multiple bank transactions",
    "description": """
        Apply one manual counterpart account to compatible bank transactions in bulk.
        Includes configurable matching, multi-company security, and persistent audit logs.
    """,
    "version": "18.0.1.0.4",
    "author": "PrimeTech Services",
    "category": "Accounting",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/mass_bank_reconcile_security.xml",
        "security/ir.model.access.csv",
        "wizard/mass_bank_reconcile_wizard_views.xml",
        "data/server_actions.xml",
        "views/mass_bank_reconcile_menu.xml",
    ],
    "application": False,
    "installable": True,
}
