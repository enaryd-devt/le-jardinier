# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    credit_check = fields.Boolean('Active Credit', help='Activate the credit limit feature')
    credit_warning = fields.Monetary('Warning Amount')
    credit_blocking = fields.Monetary('Blocking Amount')
    amount_due = fields.Monetary('Due Amount', compute='_compute_amount_due')
    partner_balance_amount = fields.Monetary(
        string='Solde', compute='_compute_partner_balance'
    )
    partner_balance_direction = fields.Char(
        string='Situation', compute='_compute_partner_balance'
    )

    def _get_partner_balance(self):
        """Return the unsigned global balance and its direction.

        The balance includes open receivable and payable entries for the
        commercial partner and all of its contacts, as in the POS customer
        cash payment module.
        """
        self.ensure_one()
        commercial_partner = self.commercial_partner_id
        lines = self.env['account.move.line'].search([
            ('partner_id', 'child_of', commercial_partner.id),
            ('company_id', '=', self.env.company.id),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
        ])
        signed_balance = sum(lines.mapped('amount_residual'))
        if not signed_balance:
            direction = _('Solde réglé')
        elif signed_balance > 0:
            direction = _('Le partenaire nous doit')
        else:
            direction = _('Nous devons au partenaire')
        return abs(signed_balance), direction

    def _compute_partner_balance(self):
        for partner in self:
            partner.partner_balance_amount, partner.partner_balance_direction = (
                partner._get_partner_balance()
            )

    @api.depends('credit', 'debit')
    def _compute_amount_due(self):
        for rec in self:
            rec.amount_due = rec.credit - rec.debit
            partner_so = self.env['sale.order'].search([('partner_id', '=', rec.id), ('state', '=', 'sale')])
            for order in partner_so:
                if not order.invoice_ids:
                    rec.amount_due = rec.amount_due + order.amount_total
                else:
                    draft_invoice = order.invoice_ids.filtered(lambda x: x.state == 'draft')
                    rec.amount_due = rec.amount_due + sum(draft_invoice.mapped('amount_residual'))
                
    @api.constrains('credit_warning', 'credit_blocking')
    def _check_credit_amount(self):
        for credit in self:
            if credit.credit_warning > credit.credit_blocking:
                raise ValidationError(_('Warning amount should not be greater than blocking amount.'))
            if credit.credit_warning < 0 or credit.credit_blocking < 0:
                raise ValidationError(_('Warning amount or blocking amount should not be less than zero.'))


class ResCompany(models.Model):
    _inherit = 'res.company'

    accountant_email = fields.Char(string='Accountant email')
