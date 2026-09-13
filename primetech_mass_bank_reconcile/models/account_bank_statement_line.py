from odoo import _, models
from odoo.exceptions import AccessError, UserError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _validate_mass_reconcile_compatibility(self, minimum_count=2):
        """Validate a selection before opening and again before processing."""
        if not self:
            raise UserError(_("No bank transaction has been selected."))
        if len(self) < minimum_count:
            raise UserError(_("Please select at least two bank transactions."))
        if len(self.company_id) != 1:
            raise UserError(
                _("The selected transactions must belong to the same company.")
            )
        if len(self.journal_id) != 1:
            raise UserError(
                _("The selected transactions must belong to the same bank journal.")
            )
        if self.journal_id.type not in ("bank", "cash"):
            raise UserError(
                _("Only bank or cash journal transactions can be processed.")
            )
        allowed_companies = self.env.companies
        if self.company_id not in allowed_companies:
            raise AccessError(_("You are not allowed to process this company."))
        currencies = self.mapped("foreign_currency_id")
        has_foreign_currency = self.filtered("foreign_currency_id")
        if has_foreign_currency and (
            len(has_foreign_currency) != len(self) or len(currencies) != 1
        ):
            raise UserError(
                _("The selected transactions must use the same transaction currency.")
            )
        directions = {
            1 if amount > 0 else -1 if amount < 0 else 0
            for amount in self.mapped("amount")
        }
        if len(directions) != 1:
            raise UserError(
                _(
                    "The selected transactions must have the same debit/credit direction."
                )
            )
        reconciled = self.filtered("is_reconciled")
        if reconciled:
            raise UserError(
                _(
                    "The transaction %s is already reconciled.",
                    reconciled[0].display_name,
                )
            )
        invalid_moves = self.filtered(lambda line: line.move_id.state != "posted")
        if invalid_moves:
            raise UserError(
                _(
                    "The transaction %s does not have a posted journal entry.",
                    invalid_moves[0].display_name,
                )
            )
        return True

    def action_open_mass_reconcile_wizard(self):
        self.check_access_rights("write")
        self.check_access_rule("write")
        if not self.env.user.has_group(
            "primetech_mass_bank_reconcile.group_mass_bank_reconcile_user"
        ):
            raise AccessError(
                _("You are not allowed to perform mass bank reconciliation.")
            )
        # A single reference transaction is enough when the wizard will expand
        # the selection with its matching criteria.  Final processing still
        # requires at least two lines.
        self._validate_mass_reconcile_compatibility(minimum_count=1)
        return {
            "type": "ir.actions.act_window",
            "name": _("Mass Bank Reconciliation"),
            "res_model": "primetech.mass.bank.reconcile.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_statement_line_ids": [(6, 0, self.ids)],
                "active_model": self._name,
                "active_ids": self.ids,
            },
        }
