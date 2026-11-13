from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    pos_deposit_payment_ids = fields.Many2many(
        "account.payment", "primetech_pos_deposit_invoice_rel",
        "move_id", "payment_id",
        string="Dépôts partenaires utilisés", copy=False, readonly=True,
    )

    def _apply_partner_deposits(self):
        """Apply available POS partner deposits to newly posted customer invoices."""
        Payment = self.env["account.payment"]
        for move in self.filtered(lambda record: record.state == "posted" and record.move_type in ("out_invoice", "out_receipt") and record.partner_id):
            partner = move.partner_id.commercial_partner_id
            invoice_lines = move.line_ids.filtered(
                lambda line: line.account_id.account_type == "asset_receivable"
                and line.amount_residual > 0
                and line.partner_id.commercial_partner_id == partner
            )
            for invoice_line in invoice_lines:
                deposits = Payment.search([
                    ("pos_customer_cash_payment", "=", True),
                    ("pos_settlement_type", "=", "deposit"),
                    ("partner_id", "=", partner.id),
                    ("company_id", "=", move.company_id.id),
                    ("state", "in", ("posted", "paid")),
                ], order="date, id")
                deposit_lines = self.env["account.move.line"]
                used_deposits = Payment
                amount_left = invoice_line.amount_residual
                for deposit in deposits:
                    deposit_line = deposit.move_id.line_ids.filtered(
                        lambda line: line.account_id == invoice_line.account_id
                        and line.partner_id.commercial_partner_id == partner
                        and line.amount_residual < 0
                        and not line.reconciled
                    )[:1]
                    if not deposit_line:
                        continue
                    deposit_lines |= deposit_line
                    used_deposits |= deposit
                    amount_left -= abs(deposit_line.amount_residual)
                    if amount_left <= 0:
                        break
                if deposit_lines:
                    (invoice_line | deposit_lines).reconcile()
                    move.pos_deposit_payment_ids = [(4, deposit.id) for deposit in used_deposits]

    def action_post(self):
        result = super().action_post()
        self._apply_partner_deposits()
        self._apply_supplier_advances()
        return result

    def _apply_supplier_advances(self):
        """Apply open POS supplier advances to newly posted supplier bills."""
        Payment = self.env["account.payment"]
        for move in self.filtered(lambda record: record.state == "posted" and record.move_type in ("in_invoice", "in_receipt") and record.partner_id):
            partner = move.partner_id.commercial_partner_id
            for bill_line in move.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable" and line.amount_residual < 0 and line.partner_id.commercial_partner_id == partner):
                advances = Payment.search([
                    ("pos_customer_cash_payment", "=", True), ("pos_settlement_type", "=", "supplier_advance"),
                    ("partner_type", "=", "supplier"), ("partner_id", "=", partner.id),
                    ("company_id", "=", move.company_id.id), ("state", "in", ("posted", "paid")),
                ], order="date, id")
                advance_lines = self.env["account.move.line"]
                used_advances = Payment
                amount_left = abs(bill_line.amount_residual)
                for advance in advances:
                    advance_line = advance.move_id.line_ids.filtered(lambda line: line.account_id == bill_line.account_id and line.partner_id.commercial_partner_id == partner and line.amount_residual > 0 and not line.reconciled)[:1]
                    if not advance_line:
                        continue
                    advance_lines |= advance_line
                    used_advances |= advance
                    amount_left -= advance_line.amount_residual
                    if amount_left <= 0:
                        break
                if advance_lines:
                    (bill_line | advance_lines).reconcile()
                    move.pos_deposit_payment_ids = [(4, advance.id) for advance in used_advances]
