from odoo import _, api, fields, models
from odoo.tools import float_compare
from odoo.exceptions import UserError, ValidationError


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_partner_global_balance(self, partner):
        """Return the partner's global customer and supplier position.

        A partner can be both customer and supplier.  The receipt must reflect
        the net of both ledgers, not just the account selected for a payment.
        ``amount_residual`` keeps partial reconciliations accurate.
        """
        self.ensure_one()
        commercial_partner = partner.commercial_partner_id
        lines = self.env["account.move.line"].search([
            ("partner_id", "child_of", commercial_partner.id),
            ("company_id", "=", self.company_id.id),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("account_id.account_type", "in", ("asset_receivable", "liability_payable")),
        ])
        signed_balance = sum(lines.mapped("amount_residual"))
        if not signed_balance:
            direction = "settled"
        else:
            direction = "partner_owes" if signed_balance > 0 else "company_owes"
        return abs(signed_balance), direction

    def _get_payment_method_line(self, journal, payment_type):
        lines = journal.inbound_payment_method_line_ids if payment_type == "inbound" else journal.outbound_payment_method_line_ids
        if not lines:
            raise UserError(_("Configurez une méthode de paiement entrant et sortant sur le journal sélectionné."))
        return lines[:1]

    def _set_payment_label(self, payment, label):
        """Keep the POS description on both the payment and partner entry."""
        partner_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id.account_type in (
                "asset_receivable",
                "liability_payable",
            )
        )
        payment.move_id.write({"ref": label})
        if partner_lines:
            partner_lines.write({"name": label})

    def _reconcile_pos_loan_repayment(self, payment):
        """Link an incoming partner payment to the customer's open POS loans."""
        self.ensure_one()
        if payment.payment_type != "inbound" or not payment.partner_id:
            return
        partner = payment.partner_id.commercial_partner_id
        repayment_line = payment.move_id.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and line.partner_id.commercial_partner_id == partner
            and line.amount_residual < 0
        )[:1]
        if not repayment_line:
            return
        loans = self.env["account.payment"].search([
            ("pos_customer_cash_payment", "=", True),
            ("payment_type", "=", "outbound"),
            ("pos_settlement_type", "=", "loan"),
            ("partner_type", "=", "customer"),
            ("partner_id", "=", partner.id),
            ("company_id", "=", payment.company_id.id),
            ("state", "in", ("posted", "paid")),
        ], order="date, id")
        loan_lines = self.env["account.move.line"]
        linked_loans = self.env["account.payment"]
        amount_left = abs(repayment_line.amount_residual)
        for loan in loans:
            loan_line = loan.move_id.line_ids.filtered(
                lambda line: line.account_id == repayment_line.account_id
                and line.partner_id.commercial_partner_id == partner
                and line.amount_residual > 0
                and not line.reconciled
            )[:1]
            if not loan_line:
                continue
            loan_lines |= loan_line
            linked_loans |= loan
            amount_left -= loan_line.amount_residual
            if amount_left <= 0:
                break
        if loan_lines:
            (repayment_line | loan_lines).reconcile()
            payment.pos_loan_payment_ids = [(4, loan.id) for loan in linked_loans]

    def _pos_open_loan_amount(self, partner):
        """Return the unreconciled amount of POS loans granted to a customer."""
        self.ensure_one()
        commercial_partner = partner.commercial_partner_id
        loans = self.env["account.payment"].search([
            ("pos_customer_cash_payment", "=", True),
            ("payment_type", "=", "outbound"),
            ("pos_settlement_type", "=", "loan"),
            ("partner_type", "=", "customer"),
            ("partner_id", "=", commercial_partner.id),
            ("company_id", "=", self.company_id.id),
            ("state", "in", ("posted", "paid")),
        ])
        amount = 0.0
        for loan in loans:
            line = loan.move_id.line_ids.filtered(
                lambda item: item.account_id.account_type == "asset_receivable"
                and item.partner_id.commercial_partner_id == commercial_partner
                and item.amount_residual > 0
                and not item.reconciled
            )[:1]
            amount += line.amount_residual
        return amount

    def _reconcile_pos_credit_sale_payment(self, payment):
        """Reconcile an incoming cash payment with open customer invoices."""
        self.ensure_one()
        partner = payment.partner_id.commercial_partner_id
        payment_line = payment.move_id.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and line.partner_id.commercial_partner_id == partner
            and line.amount_residual < 0
        )[:1]
        if not payment_line:
            return
        invoice_lines = self.env["account.move.line"].search([
            ("partner_id", "child_of", partner.id),
            ("company_id", "=", payment.company_id.id),
            ("parent_state", "=", "posted"),
            ("account_id", "=", payment_line.account_id.id),
            ("account_id.account_type", "=", "asset_receivable"),
            ("move_id.move_type", "in", ("out_invoice", "out_receipt")),
            ("amount_residual", ">", 0),
        ], order="date_maturity, date, id")
        selected_lines = self.env["account.move.line"]
        selected_invoices = self.env["account.move"]
        amount_left = abs(payment_line.amount_residual)
        for line in invoice_lines:
            selected_lines |= line
            selected_invoices |= line.move_id
            amount_left -= line.amount_residual
            if amount_left <= 0:
                break
        if selected_lines:
            (payment_line | selected_lines).reconcile()
            payment.pos_credit_invoice_ids = [(4, invoice.id) for invoice in selected_invoices]

    def _reconcile_pos_supplier_bill_payment(self, payment):
        """Apply a POS cash disbursement to the supplier's open bills."""
        self.ensure_one()
        partner = payment.partner_id.commercial_partner_id
        payment_line = payment.move_id.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable" and line.partner_id.commercial_partner_id == partner and line.amount_residual > 0)[:1]
        if not payment_line:
            return
        bill_lines = self.env["account.move.line"].search([
            ("partner_id", "child_of", partner.id), ("company_id", "=", payment.company_id.id),
            ("parent_state", "=", "posted"), ("account_id", "=", payment_line.account_id.id),
            ("move_id.move_type", "in", ("in_invoice", "in_receipt")), ("amount_residual", "<", 0),
        ], order="date_maturity, date, id")
        selected_lines = self.env["account.move.line"]
        selected_bills = self.env["account.move"]
        amount_left = payment_line.amount_residual
        for line in bill_lines:
            selected_lines |= line
            selected_bills |= line.move_id
            amount_left -= abs(line.amount_residual)
            if amount_left <= 0:
                break
        if selected_lines:
            (payment_line | selected_lines).reconcile()
            payment.pos_supplier_bill_ids = [(4, bill.id) for bill in selected_bills]

    def _reconcile_pos_supplier_refund(self, payment):
        """Apply supplier cash refund to posted supplier credit notes."""
        self.ensure_one()
        partner = payment.partner_id.commercial_partner_id
        payment_line = payment.move_id.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable" and line.partner_id.commercial_partner_id == partner and line.amount_residual < 0)[:1]
        if not payment_line:
            return
        refund_lines = self.env["account.move.line"].search([
            ("partner_id", "child_of", partner.id), ("company_id", "=", payment.company_id.id),
            ("parent_state", "=", "posted"), ("account_id", "=", payment_line.account_id.id),
            ("move_id.move_type", "=", "in_refund"), ("amount_residual", ">", 0),
        ], order="date_maturity, date, id")
        selected_lines = self.env["account.move.line"]
        selected_bills = self.env["account.move"]
        amount_left = abs(payment_line.amount_residual)
        for line in refund_lines:
            selected_lines |= line
            selected_bills |= line.move_id
            amount_left -= line.amount_residual
            if amount_left <= 0:
                break
        if selected_lines:
            (payment_line | selected_lines).reconcile()
            payment.pos_supplier_bill_ids = [(4, bill.id) for bill in selected_bills]

    def _reconcile_pos_supplier_advance_refund(self, payment):
        """Reconcile returned supplier advance with the original advance."""
        self.ensure_one()
        partner = payment.partner_id.commercial_partner_id
        refund_line = payment.move_id.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable" and line.partner_id.commercial_partner_id == partner and line.amount_residual < 0)[:1]
        if not refund_line:
            return
        advances = self.env["account.payment"].search([
            ("pos_customer_cash_payment", "=", True), ("pos_settlement_type", "=", "supplier_advance"),
            ("partner_type", "=", "supplier"), ("partner_id", "=", partner.id),
            ("company_id", "=", payment.company_id.id), ("state", "in", ("posted", "paid")),
        ], order="date, id")
        advance_lines = self.env["account.move.line"]
        amount_left = abs(refund_line.amount_residual)
        for advance in advances:
            advance_line = advance.move_id.line_ids.filtered(lambda line: line.account_id == refund_line.account_id and line.partner_id.commercial_partner_id == partner and line.amount_residual > 0 and not line.reconciled)[:1]
            if not advance_line:
                continue
            advance_lines |= advance_line
            amount_left -= advance_line.amount_residual
            if amount_left <= 0:
                break
        if advance_lines:
            (refund_line | advance_lines).reconcile()

    def _pos_available_deposit_amount(self, partner):
        """Return only the POS deposits still available for a customer."""
        self.ensure_one()
        commercial_partner = partner.commercial_partner_id
        deposits = self.env["account.payment"].search([
            ("pos_customer_cash_payment", "=", True),
            ("pos_settlement_type", "=", "deposit"),
            ("partner_type", "=", "customer"),
            ("partner_id", "=", commercial_partner.id),
            ("company_id", "=", self.company_id.id),
            ("state", "in", ("posted", "paid")),
        ])
        amount = 0.0
        for deposit in deposits:
            line = deposit.move_id.line_ids.filtered(
                lambda item: item.account_id.account_type == "asset_receivable"
                and item.partner_id.commercial_partner_id == commercial_partner
                and item.amount_residual < 0
                and not item.reconciled
            )[:1]
            amount += abs(line.amount_residual)
        return amount

    def _reconcile_pos_deposit_withdrawal(self, payment):
        """Use the partner's available deposits when cash is withdrawn."""
        self.ensure_one()
        partner = payment.partner_id.commercial_partner_id
        withdrawal_line = payment.move_id.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and line.partner_id.commercial_partner_id == partner
            and line.amount_residual > 0
        )[:1]
        if not withdrawal_line:
            return
        deposits = self.env["account.payment"].search([
            ("pos_customer_cash_payment", "=", True),
            ("pos_settlement_type", "=", "deposit"),
            ("partner_id", "=", partner.id),
            ("company_id", "=", payment.company_id.id),
            ("state", "in", ("posted", "paid")),
        ], order="date, id")
        deposit_lines = self.env["account.move.line"]
        linked_deposits = self.env["account.payment"]
        amount_left = withdrawal_line.amount_residual
        for deposit in deposits:
            deposit_line = deposit.move_id.line_ids.filtered(
                lambda line: line.account_id == withdrawal_line.account_id
                and line.partner_id.commercial_partner_id == partner
                and line.amount_residual < 0
                and not line.reconciled
            )[:1]
            if not deposit_line:
                continue
            deposit_lines |= deposit_line
            linked_deposits |= deposit
            amount_left -= abs(deposit_line.amount_residual)
            if amount_left <= 0:
                break
        if deposit_lines:
            (withdrawal_line | deposit_lines).reconcile()
            payment.pos_deposit_payment_ids = [(4, deposit.id) for deposit in linked_deposits]

    @api.model
    def pos_customer_payment_partners(self, session_id, search_term="", offset=0, limit=100, partner_type=False):
        """Search every active contact available to the POS user, by pages."""
        session = self.browse(session_id).exists()
        if not session:
            return {"partners": [], "has_more": False}
        # display_name is computed/non-stored in Odoo 18 and cannot be used
        # in a SQL ORDER BY.
        domain = [("active", "=", True)]
        if partner_type == "customer":
            domain.append(("customer_rank", ">", 0))
        elif partner_type == "supplier":
            domain.append(("supplier_rank", ">", 0))
        if search_term:
            domain += ["|", "|", "|", "|", ("name", "ilike", search_term), ("phone", "ilike", search_term), ("mobile", "ilike", search_term), ("email", "ilike", search_term), ("ref", "ilike", search_term)]
        partners = self.env["res.partner"].search(domain, order="name, id", offset=offset, limit=limit + 1)
        has_more = len(partners) > limit
        return {
            "partners": partners[:limit].read(["display_name", "name", "phone", "mobile", "email", "ref"]),
            "has_more": has_more,
        }

    @api.model
    def pos_partner_global_balance(self, session_id, partner_id):
        """Provide the live global partner position to the POS JavaScript UI."""
        session = self.browse(session_id).exists()
        partner = self.env["res.partner"].browse(partner_id).exists()
        if not session or not partner:
            raise ValidationError(_("Veuillez sélectionner un partenaire."))
        amount, direction = session._pos_partner_global_balance(partner)
        labels = {
            "partner_owes": _("Le partenaire nous doit"),
            "company_owes": _("Nous devons au partenaire"),
            "settled": _("Solde réglé"),
        }
        return {
            "partner_name": partner.commercial_partner_id.display_name,
            "amount": amount,
            "direction": labels[direction],
            "direction_code": direction,
        }

    @api.model
    def pos_loan_repayment_preview(self, session_id, partner_id, amount):
        """Prepare a transparent repayment/deposit split for the POS popup."""
        session = self.browse(session_id).exists()
        partner = self.env["res.partner"].browse(partner_id).exists()
        amount = float(amount or 0.0)
        if not session or not partner or amount <= 0:
            raise ValidationError(_("A valid partner and amount are required."))
        open_loan_amount = session._pos_open_loan_amount(partner)
        repayment_amount = min(amount, open_loan_amount)
        deposit_amount = max(0.0, amount - repayment_amount)
        return {
            "partner_name": partner.commercial_partner_id.display_name,
            "requested_amount": amount,
            "open_loan_amount": open_loan_amount,
            "repayment_amount": repayment_amount,
            "deposit_amount": deposit_amount,
            "has_open_loan": bool(open_loan_amount),
        }

    @api.model
    def create_customer_cash_payment(self, session_id, partner_id, payment_type, amount, reason="", settlement_type="credit_sale", partner_type="customer"):
        session = self.browse(session_id).exists()
        if not session or session.state not in ("opened", "opening_control"):
            raise UserError(_("La session du point de vente n'est plus ouverte."))
        if payment_type not in ("inbound", "outbound") or amount <= 0:
            raise ValidationError(_("Le montant du paiement doit être supérieur à zéro."))
        if partner_type == "customer" and payment_type == "inbound" and settlement_type not in ("credit_sale", "loan_repayment", "loan_repayment_plus_deposit", "deposit"):
            raise ValidationError(_("Choisissez le type de règlement entrant."))
        if partner_type == "customer" and payment_type == "outbound" and settlement_type not in ("loan", "deposit_withdrawal"):
            settlement_type = "loan"
        allowed_settlements = {
            "customer": {
                "inbound": ("credit_sale", "loan_repayment", "loan_repayment_plus_deposit", "deposit"),
                "outbound": ("loan", "deposit_withdrawal"),
            },
            "supplier": {
                "inbound": ("vendor_refund", "supplier_advance_refund"),
                "outbound": ("vendor_bill", "supplier_advance"),
            },
        }
        if partner_type not in allowed_settlements or settlement_type not in allowed_settlements[partner_type][payment_type]:
            raise ValidationError(_("Invalid partner payment type."))
        partner = self.env["res.partner"].browse(partner_id).exists()
        if not partner:
            raise ValidationError(_("Veuillez sélectionner un partenaire."))
        if partner_type == "customer" and settlement_type == "loan_repayment_plus_deposit":
            open_loan_amount = session._pos_open_loan_amount(partner)
            if open_loan_amount and float_compare(amount, open_loan_amount, precision_rounding=session.currency_id.rounding) <= 0:
                raise ValidationError(_(
                    "This split requires an amount greater than the outstanding POS loan balance: %(amount)s."
                ) % {"amount": open_loan_amount})
            repayment = False
            if open_loan_amount:
                repayment = self.create_customer_cash_payment(
                    session.id, partner.id, "inbound", open_loan_amount, reason,
                    "loan_repayment", "customer",
                )
            deposit = self.create_customer_cash_payment(
                session.id, partner.id, "inbound", amount - open_loan_amount, reason,
                "deposit", "customer",
            )
            deposit.update({
                "split_details": {
                    "repayment_amount": open_loan_amount,
                    "deposit_amount": amount - open_loan_amount,
                    "repayment_number": repayment["name"] if repayment else False,
                    "deposit_number": deposit["name"],
                },
                "amount": amount,
            })
            return deposit
        if partner_type == "customer" and settlement_type == "loan_repayment":
            open_loan_amount = session._pos_open_loan_amount(partner)
            if float_compare(amount, open_loan_amount, precision_rounding=session.currency_id.rounding) > 0:
                raise ValidationError(_("Loan repayment exceeds the outstanding POS loan balance."))
        if partner_type == "customer" and settlement_type == "deposit_withdrawal":
            available_deposit = session._pos_available_deposit_amount(partner)
            if float_compare(amount, available_deposit, precision_rounding=session.currency_id.rounding) > 0:
                raise ValidationError(_(
                    "Withdrawal exceeds the customer's available POS deposit balance: %(amount)s."
                ) % {"amount": available_deposit})
        journal = session.cash_journal_id
        if not journal:
            raise UserError(_("Aucun journal de caisse n'est configuré pour cette session POS."))
        suspense_account = journal.suspense_account_id
        if not suspense_account:
            raise UserError(_("Configurez un compte d'attente sur le journal de caisse du POS."))

        before, before_direction = session._pos_partner_global_balance(partner)
        # ``payment.name`` is allocated only when the payment is posted.  A
        # temporary value is used at creation and the final, human-readable
        # label is written immediately afterwards on the partner journal item.
        payment_label = reason or (
            _("Paiement POS %(session)s - %(partner)s")
            % {"session": session.name, "partner": partner.display_name}
        )
        payment = self.env["account.payment"].create({
            "payment_type": payment_type,
            # Loans and repayments are both carried by the customer's
            # receivable account so Odoo can reconcile them.
            "partner_type": partner_type,
            "partner_id": partner.commercial_partner_id.id,
            "amount": amount,
            "currency_id": session.currency_id.id,
            "date": fields.Date.context_today(session),
            "journal_id": journal.id,
            "payment_method_line_id": session._get_payment_method_line(journal, payment_type).id,
            "force_outstanding_account_id": suspense_account.id if suspense_account else False,
            "payment_reference": payment_label,
            "memo": payment_label,
            "pos_session_id": session.id,
            "pos_customer_cash_payment": True,
            "pos_settlement_type": settlement_type,
            "pos_balance_before": before,
            "pos_balance_before_direction": before_direction,
        })
        payment.action_post()
        payment_label = " - ".join(
            part for part in (session.name, payment.name, reason) if part
        )
        session._set_payment_label(payment, payment_label)
        if partner_type == "customer" and payment_type == "inbound":
            if settlement_type == "loan_repayment":
                session._reconcile_pos_loan_repayment(payment)
            elif settlement_type == "credit_sale":
                session._reconcile_pos_credit_sale_payment(payment)
        elif partner_type == "customer" and settlement_type == "deposit_withdrawal":
            session._reconcile_pos_deposit_withdrawal(payment)
        elif partner_type == "supplier" and settlement_type == "vendor_bill":
            session._reconcile_pos_supplier_bill_payment(payment)
        elif partner_type == "supplier" and settlement_type == "vendor_refund":
            session._reconcile_pos_supplier_refund(payment)
        elif partner_type == "supplier" and settlement_type == "supplier_advance_refund":
            session._reconcile_pos_supplier_advance_refund(payment)

        # This line is deliberately retained for the cash journal: POS closing uses it to calculate the
        # physical cash expected in the drawer.  It clears the payment's suspense
        # line, so the cash and receivable are each recorded exactly once.
        sign = 1 if payment_type == "inbound" else -1
        statement_line = self.env["account.bank.statement.line"].create({
            "pos_session_id": session.id, "journal_id": journal.id, "amount": sign * amount,
            "date": fields.Date.context_today(session), "payment_ref": payment_label,
            "partner_id": False,
            "counterpart_account_id": suspense_account.id,
            "pos_customer_cash_payment_id": payment.id,
        })
        suspense_lines = payment.move_id.line_ids.filtered(lambda line: line.account_id == suspense_account and not line.reconciled) | statement_line.move_id.line_ids.filtered(lambda line: line.account_id == suspense_account and not line.reconciled)
        if suspense_lines and not suspense_account.reconcile:
            suspense_account.sudo().write({"reconcile": True})
        if suspense_lines:
            suspense_lines.reconcile()
        # Every accounting entry of this operation now exists; the value shown
        # on the receipt is the real balance after this incoming/outgoing payment.
        after, after_direction = session._pos_partner_global_balance(partner)
        payment.write({
            "pos_balance_after": after,
            "pos_balance_after_direction": after_direction,
        })
        return self._payment_receipt_values(payment)

    @api.model
    def _payment_receipt_values(self, payment):
        payment.ensure_one()
        return {
            "id": payment.id,
            "name": payment.name,
            "partner_name": payment.partner_id.display_name,
            "amount": payment.amount,
            "balance_before": payment.pos_balance_before,
            "balance_after": payment.pos_balance_after,
            "balance_before_label": payment._pos_balance_direction_label(
                payment.pos_balance_before_direction
            ),
            "balance_after_label": payment._pos_balance_direction_label(
                payment.pos_balance_after_direction
            ),
            "partner_type": payment.partner_type,
            "payment_type": payment.payment_type,
            "reason": payment.payment_reference or "",
            # Keep the original payment timestamp when displaying or reprinting
            # an entry from the POS history.
            "date": fields.Datetime.context_timestamp(
                self, payment.create_date
            ).strftime("%d/%m/%Y %H:%M"),
        }

    @api.model
    def pos_customer_payment_list(self, session_id, offset=0, limit=50, search_term=""):
        """Return paginated partner payments from every POS session."""
        session = self.browse(session_id).exists()
        if not session:
            raise UserError(_("La session du point de vente n'est plus ouverte."))
        domain = [("pos_customer_cash_payment", "=", True)]
        search_term = (search_term or "").strip()
        if search_term:
            domain += [
                "|", "|",
                ("partner_id", "ilike", search_term),
                ("name", "ilike", search_term),
                ("payment_reference", "ilike", search_term),
            ]
        total = self.env["account.payment"].search_count(domain)
        offset = max(0, int(offset or 0))
        limit = max(1, min(int(limit or 50), 50))
        payments = self.env["account.payment"].search(domain, order="id desc", offset=offset, limit=limit)
        return {
            "payments": [self._payment_receipt_values(payment) for payment in payments],
            "total": total,
        }

    @api.model
    def pos_cash_move_list(self, session_id, offset=0, limit=50, search_term=""):
        """Return the cash entries and exits of the current POS session."""
        session = self.browse(session_id).exists()
        if not session:
            raise UserError(_("La session du point de vente n'est plus ouverte."))
        domain = [
            ("pos_session_id", "=", session.id),
            ("journal_id", "=", session.cash_journal_id.id),
        ]
        search_term = (search_term or "").strip()
        if search_term:
            domain += [
                "|", "|", "|",
                ("payment_ref", "ilike", search_term), ("ref", "ilike", search_term),
                ("name", "ilike", search_term),
                ("pos_customer_cash_payment_id.partner_id", "ilike", search_term),
            ]
        statement_lines = self.env["account.bank.statement.line"]
        total = statement_lines.search_count(domain)
        offset = max(0, int(offset or 0))
        limit = max(1, min(int(limit or 50), 50))
        moves = statement_lines.search(domain, order="date desc, id desc", offset=offset, limit=limit)
        inbound_group = statement_lines.read_group(domain + [("amount", ">", 0)], ["amount:sum"], [])
        outbound_group = statement_lines.read_group(domain + [("amount", "<", 0)], ["amount:sum"], [])
        result = []
        for move in moves:
            payment = move.pos_customer_cash_payment_id
            result.append({
                "id": move.id,
                "date": fields.Datetime.context_timestamp(self, move.create_date).strftime("%d/%m/%Y %H:%M"),
                "partner_name": payment.partner_id.display_name if payment else (move.partner_id.display_name or ""),
                "label": payment.payment_reference if payment else (move.payment_ref or move.ref or move.name or ""),
                "document_number": payment.name if payment else "",
                "amount": abs(move.amount),
                "direction": "inbound" if move.amount >= 0 else "outbound",
                "receipt": self._payment_receipt_values(payment) if payment else False,
            })
        return {
            "moves": result, "total": total,
            "inbound_total": inbound_group[0].get("amount", 0.0) if inbound_group else 0.0,
            "outbound_total": abs(outbound_group[0].get("amount", 0.0)) if outbound_group else 0.0,
        }
