from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestMassBankReconcile(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.bank_account = cls.env["account.account"].create(
            {
                "name": "Test Bank",
                "code": "101990",
                "account_type": "asset_cash",
                "company_ids": [(6, 0, cls.company.ids)],
            }
        )
        cls.suspense_account = cls.env["account.account"].create(
            {
                "name": "Test Suspense",
                "code": "101991",
                "account_type": "asset_current",
                "company_ids": [(6, 0, cls.company.ids)],
            }
        )
        cls.counterpart_account = cls.env["account.account"].create(
            {
                "name": "Bank Fees",
                "code": "627990",
                "account_type": "expense",
                "company_ids": [(6, 0, cls.company.ids)],
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Mass reconcile bank",
                "code": "MRB1",
                "type": "bank",
                "company_id": cls.company.id,
                "default_account_id": cls.bank_account.id,
                "suspense_account_id": cls.suspense_account.id,
            }
        )
        cls.env.user.groups_id += cls.env.ref(
            "primetech_mass_bank_reconcile.group_mass_bank_reconcile_user"
        )

    def _make_line(
        self,
        amount,
        journal=None,
        payment_ref="Bank fee",
        date="2026-08-01",
        partner=None,
    ):
        return self.env["account.bank.statement.line"].create(
            {
                "date": date,
                "payment_ref": payment_ref,
                "amount": amount,
                "journal_id": (journal or self.journal).id,
                "partner_id": partner and partner.id,
            }
        )

    def _wizard(self, lines, account=None):
        return self.env["primetech.mass.bank.reconcile.wizard"].create(
            {
                "statement_line_ids": [(6, 0, lines.ids)],
                "reference_line_id": lines[0].id,
                "manual_account_id": (account or self.counterpart_account).id,
            }
        )

    def test_single_line_rejected(self):
        with self.assertRaisesRegex(UserError, "at least two"):
            self._make_line(-10)._validate_mass_reconcile_compatibility()

    def test_different_journals_rejected(self):
        other = self.journal.copy({"name": "Other bank", "code": "MRB2"})
        lines = self._make_line(-10) | self._make_line(-20, other)
        with self.assertRaisesRegex(UserError, "same bank journal"):
            lines._validate_mass_reconcile_compatibility()

    def test_mixed_debit_credit_directions_rejected(self):
        lines = self._make_line(-10) | self._make_line(20)
        with self.assertRaisesRegex(UserError, "same debit/credit direction"):
            lines._validate_mass_reconcile_compatibility()

    def test_invalid_company_account_rejected(self):
        other_company = self.env["res.company"].create({"name": "Other company"})
        account = self.counterpart_account.copy(
            {"code": "627991", "company_ids": [(6, 0, other_company.ids)]}
        )
        with self.assertRaises(ValidationError):
            self._wizard(self._make_line(-10) | self._make_line(-20), account)

    def test_manual_account_is_a_chart_of_accounts_field(self):
        field = self.env["primetech.mass.bank.reconcile.wizard"]._fields[
            "manual_account_id"
        ]
        self.assertEqual(field.comodel_name, "account.account")
        self.assertTrue(field.required)
        self.assertTrue(field.check_company)

    def test_receivable_manual_account_rejected(self):
        receivable = self.env["account.account"].create(
            {
                "name": "Invalid reconciliation receivable",
                "code": "411990",
                "account_type": "asset_receivable",
                "reconcile": True,
                "company_ids": [(6, 0, self.company.ids)],
            }
        )
        with self.assertRaisesRegex(ValidationError, "regular chart of accounts"):
            self._wizard(self._make_line(-10) | self._make_line(-20), receivable)

    def test_multiple_debits_and_credits_summary(self):
        debit_wizard = self._wizard(self._make_line(30) | self._make_line(20))
        self.assertEqual(debit_wizard.total_debit, 50)
        self.assertEqual(debit_wizard.total_credit, 0)
        credit_wizard = self._wizard(self._make_line(-30) | self._make_line(-20))
        self.assertEqual(credit_wizard.total_credit, 50)
        self.assertEqual(credit_wizard.total_debit, 0)

    def test_find_matching_lines_by_selected_partner(self):
        partner = self.env["res.partner"].create({"name": "Matching Partner"})
        reference = self._make_line(-25)
        matching = self._make_line(-25, partner=partner)
        self._make_line(-30, partner=partner)
        self._make_line(-25, payment_ref="Another label", partner=partner)
        self._make_line(-25, date="2026-08-02", partner=partner)
        self._make_line(-25)
        wizard = self._wizard(reference)
        wizard.write({"match_partner": True, "matching_partner_id": partner.id})

        wizard.action_find_matching_lines()

        self.assertIn(matching, wizard.statement_line_ids)
        self.assertNotIn(reference, wizard.statement_line_ids)

    def test_find_matching_lines_requires_partner_option(self):
        wizard = self._wizard(self._make_line(-10))
        with self.assertRaisesRegex(UserError, "Enable partner matching"):
            wizard.action_find_matching_lines()

    def test_selected_partner_is_applied_to_every_line(self):
        partner = self.env["res.partner"].create({"name": "Applied Partner"})
        lines = self._make_line(-10) | self._make_line(-20)
        wizard = self._wizard(lines)
        wizard.write({"match_partner": True, "matching_partner_id": partner.id})

        wizard.action_mass_reconcile()

        self.assertEqual(lines.partner_id, partner)
        for line in lines:
            _liquidity, _suspense, counterpart = line._seek_for_lines()
            self.assertEqual(counterpart.partner_id, partner)

    def test_reconcile_keeps_each_move_balanced_and_logs(self):
        lines = self._make_line(-30) | self._make_line(-20)
        result = self._wizard(lines).action_mass_reconcile()
        self.assertEqual(result["tag"], "display_notification")
        self.assertTrue(all(lines.mapped("is_reconciled")))
        for move in lines.move_id:
            self.assertEqual(sum(move.line_ids.mapped("balance")), 0)
            self.assertIn(self.counterpart_account, move.line_ids.account_id)
        log = self.env["primetech.mass.bank.reconcile.log"].search([], limit=1)
        self.assertEqual(log.statement_line_ids, lines)
        self.assertEqual(log.line_count, 2)

    def test_already_reconciled_rejected(self):
        lines = self._make_line(-10) | self._make_line(-20)
        self._wizard(lines).action_mass_reconcile()
        with self.assertRaisesRegex(UserError, "already reconciled"):
            lines._validate_mass_reconcile_compatibility()

    def test_unauthorized_user_rejected(self):
        user = self.env["res.users"].create(
            {
                "name": "Basic accountant",
                "login": "basic-mass-test",
                "company_id": self.company.id,
                "company_ids": [(6, 0, self.company.ids)],
                "groups_id": [(6, 0, [self.env.ref("account.group_account_user").id])],
            }
        )
        wizard = self._wizard(self._make_line(-10) | self._make_line(-20))
        with self.assertRaises(AccessError):
            wizard.with_user(user).action_mass_reconcile()
