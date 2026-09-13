from odoo import fields, models


class MassBankReconcileLog(models.Model):
    _name = "primetech.mass.bank.reconcile.log"
    _description = "Mass Bank Reconciliation Log"
    _order = "date desc, id desc"

    user_id = fields.Many2one("res.users", required=True, readonly=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True)
    journal_id = fields.Many2one("account.journal", required=True, readonly=True)
    manual_account_id = fields.Many2one("account.account", required=True, readonly=True)
    statement_line_ids = fields.Many2many(
        "account.bank.statement.line",
        "primetech_reconcile_log_statement_rel",
        "log_id",
        "statement_line_id",
        readonly=True,
    )
    line_count = fields.Integer(readonly=True)
    total_amount = fields.Monetary(readonly=True, currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", required=True, readonly=True)
    date = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    state = fields.Selection(
        [("done", "Done"), ("failed", "Failed")], required=True, readonly=True
    )
    message = fields.Text(readonly=True)
