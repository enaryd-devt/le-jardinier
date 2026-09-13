from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class MassBankReconcileWizard(models.TransientModel):
    _name = "primetech.mass.bank.reconcile.wizard"
    _description = "Mass Bank Reconciliation"
    _inherit = ["analytic.mixin"]

    statement_line_ids = fields.Many2many(
        "account.bank.statement.line",
        "pt_mass_reconcile_wizard_line_rel",
        "wizard_id",
        "statement_line_id",
        required=True,
        readonly=True,
    )
    reference_line_id = fields.Many2one(
        "account.bank.statement.line",
        string="Reference transaction",
        required=True,
        readonly=True,
    )
    manual_account_id = fields.Many2one(
        "account.account",
        string="Counterpart account",
        required=True,
        check_company=True,
        domain=[
            ("deprecated", "=", False),
            (
                "account_type",
                "not in",
                ("asset_receivable", "liability_payable", "off_balance"),
            ),
        ],
        help="Chart of accounts account used as the manual counterpart for every "
        "selected bank transaction.",
    )
    company_id = fields.Many2one("res.company", compute="_compute_summary", store=True)
    journal_id = fields.Many2one(
        "account.journal", compute="_compute_summary", store=True
    )
    currency_id = fields.Many2one(
        "res.currency", compute="_compute_summary", store=True
    )
    line_count = fields.Integer(compute="_compute_summary", store=True)
    total_amount = fields.Monetary(compute="_compute_summary", store=True)
    total_debit = fields.Monetary(compute="_compute_summary", store=True)
    total_credit = fields.Monetary(compute="_compute_summary", store=True)
    partner_id = fields.Many2one("res.partner", compute="_compute_summary", store=True)
    label = fields.Char(required=True, default=lambda self: _("Mass reconciliation"))
    auto_validate = fields.Boolean(default=True)
    notes = fields.Text()
    match_partner = fields.Boolean(string="Match and apply a partner")
    matching_partner_id = fields.Many2one(
        "res.partner",
        string="Partner to match and apply",
        help="Only unreconciled transactions for this partner are gathered. The partner "
        "is also applied to every processed transaction and its counterpart line.",
    )

    @api.depends(
        "statement_line_ids",
        "statement_line_ids.amount",
        "statement_line_ids.partner_id",
        "statement_line_ids.company_id",
        "statement_line_ids.journal_id",
    )
    def _compute_summary(self):
        for wizard in self:
            lines = wizard.statement_line_ids
            wizard.company_id = lines[:1].company_id
            wizard.journal_id = lines[:1].journal_id
            wizard.currency_id = lines[:1].currency_id or self.env.company.currency_id
            wizard.line_count = len(lines)
            wizard.total_amount = sum(lines.mapped("amount"))
            wizard.total_debit = sum(
                amount for amount in lines.mapped("amount") if amount > 0
            )
            wizard.total_credit = -sum(
                amount for amount in lines.mapped("amount") if amount < 0
            )
            partners = lines.mapped("partner_id")
            wizard.partner_id = (
                partners
                if len(partners) == 1
                and len(lines.filtered("partner_id")) == len(lines)
                else False
            )

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        if (
            not values.get("statement_line_ids")
            and self.env.context.get("active_model") == "account.bank.statement.line"
        ):
            values["statement_line_ids"] = [
                (6, 0, self.env.context.get("active_ids", []))
            ]
        lines = (
            self.env["account.bank.statement.line"]
            .browse(self.env.context.get("active_ids", []))
            .exists()
        )
        if lines and "label" in field_list:
            labels = set(lines.mapped("payment_ref"))
            values["label"] = (
                labels.pop() if len(labels) == 1 else _("Mass reconciliation")
            )
        if lines and "reference_line_id" in field_list:
            values["reference_line_id"] = lines[0].id
        if lines and "matching_partner_id" in field_list and lines[0].partner_id:
            values["matching_partner_id"] = lines[0].partner_id.id
        return values

    @api.onchange("match_partner")
    def _onchange_match_partner(self):
        if self.match_partner and not self.matching_partner_id:
            self.matching_partner_id = self.reference_line_id.partner_id
        elif not self.match_partner:
            self.matching_partner_id = False

    def _matching_statement_line_domain(self):
        """Build a safe ORM domain from the selected reference transaction."""
        self.ensure_one()
        reference = self.reference_line_id
        if not reference:
            raise UserError(_("A reference transaction is required."))
        if not self.match_partner:
            raise UserError(_("Enable partner matching before gathering transactions."))
        if not self.matching_partner_id:
            raise UserError(_("Select the partner to match and apply."))

        domain = [
            ("company_id", "=", reference.company_id.id),
            ("journal_id", "=", reference.journal_id.id),
            ("is_reconciled", "=", False),
            ("move_id.state", "=", "posted"),
            ("foreign_currency_id", "=", reference.foreign_currency_id.id or False),
        ]
        if reference.amount > 0:
            domain.append(("amount", ">", 0))
        elif reference.amount < 0:
            domain.append(("amount", "<", 0))
        else:
            domain.append(("amount", "=", 0))
        domain.append(("partner_id", "=", self.matching_partner_id.id))
        return domain

    def action_find_matching_lines(self):
        """Gather unreconciled lines matching the configurable criteria."""
        self.ensure_one()
        reference = self.reference_line_id
        reference.check_access_rights("read")
        reference.check_access_rule("read")
        matching_lines = self.env["account.bank.statement.line"].search(
            self._matching_statement_line_domain()
        )
        if len(matching_lines) < 2:
            raise UserError(
                _("No other unreconciled transaction matches the selected criteria.")
            )
        matching_lines._validate_mass_reconcile_compatibility()
        self.statement_line_ids = [(6, 0, matching_lines.ids)]
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Matching transactions"),
                "message": _(
                    "%s matching transactions were gathered.", len(matching_lines)
                ),
                "type": "success",
                "sticky": False,
            },
        }

    @api.constrains("manual_account_id", "company_id")
    def _check_manual_account_company(self):
        for wizard in self:
            if (
                wizard.manual_account_id
                and wizard.company_id not in wizard.manual_account_id.company_ids
            ):
                raise ValidationError(
                    _("The selected account cannot be used for this company.")
                )
            if wizard.manual_account_id.account_type in (
                "asset_receivable",
                "liability_payable",
                "off_balance",
            ):
                raise ValidationError(
                    _(
                        "Select a regular chart of accounts account; receivable, payable, "
                        "and off-balance accounts cannot be used as a manual counterpart."
                    )
                )
            if wizard.manual_account_id.deprecated:
                raise ValidationError(
                    _("The selected chart of accounts account is deprecated.")
                )

    def _get_suspense_line(self, statement_line):
        # Odoo 18's standard `_seek_for_lines` classifies the existing, balanced
        # statement move.  Reclassifying its suspense line is the same primitive
        # used by a manual counterpart and preserves Odoo's currency amounts.
        _liquidity, suspense_lines, _other = statement_line._seek_for_lines()
        if len(suspense_lines) != 1:
            raise UserError(
                _(
                    "Transaction %s does not have exactly one suspense line and cannot be processed automatically.",
                    statement_line.display_name,
                )
            )
        return suspense_lines

    def action_mass_reconcile(self):
        self.ensure_one()
        if not self.env.user.has_group(
            "primetech_mass_bank_reconcile.group_mass_bank_reconcile_user"
        ):
            raise AccessError(
                _("You are not allowed to perform mass bank reconciliation.")
            )
        if not self.manual_account_id:
            raise UserError(_("The counterpart account is required."))
        lines = self.statement_line_ids.exists().with_company(self.company_id)
        lines.check_access_rights("write")
        lines.check_access_rule("write")
        self.manual_account_id.check_access_rights("read")
        self.manual_account_id.check_access_rule("read")
        lines._validate_mass_reconcile_compatibility()
        self._check_manual_account_company()

        # No savepoint and no commit: any exception rolls the whole RPC transaction back.
        for statement_line in lines:
            if self.match_partner:
                if not self.matching_partner_id:
                    raise UserError(_("Select the partner to apply."))
                statement_line.partner_id = self.matching_partner_id
            suspense_line = self._get_suspense_line(statement_line)
            values = {
                "account_id": self.manual_account_id.id,
                "name": self.label or statement_line.payment_ref or statement_line.name,
            }
            partner = (
                self.matching_partner_id
                if self.match_partner
                else statement_line.partner_id
            )
            if partner:
                values["partner_id"] = partner.id
            if self.analytic_distribution:
                values["analytic_distribution"] = self.analytic_distribution
            suspense_line.with_context(check_move_validity=False).write(values)

        still_open = lines.filtered(lambda line: not line.is_reconciled)
        if still_open:
            raise UserError(
                _(
                    "Transaction %s could not be marked as reconciled.",
                    still_open[0].display_name,
                )
            )
        self.env["primetech.mass.bank.reconcile.log"].create(
            {
                "user_id": self.env.user.id,
                "company_id": self.company_id.id,
                "journal_id": self.journal_id.id,
                "manual_account_id": self.manual_account_id.id,
                "statement_line_ids": [(6, 0, lines.ids)],
                "line_count": len(lines),
                "total_amount": self.total_amount,
                "currency_id": self.currency_id.id,
                "state": "done",
                "message": self.notes
                or _("%s transactions processed successfully.", len(lines)),
            }
        )
        message = _("%s bank transactions were reconciled successfully.", len(lines))
        if self.auto_validate:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Mass reconciliation"),
                    "message": message,
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        return {"type": "ir.actions.act_window_close"}
