from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


'''Ancien moteur de règles, périodes, crédits et précomptes.

Il est désactivé afin que le module ne propose plus que le cycle DGI TVA/IR
fondé sur les correspondances avec le plan comptable.

SOURCE_TYPES = [
    ('accounting', 'Écritures comptables'),
    ('invoice', 'Facturation'),
    ('pos', 'Point de Vente'),
    ('payment', 'Journaux de règlement'),
    ('payroll', 'Paie'),
]


class TaxRule(models.Model):
    _name = 'primetech.tax.rule'
    _description = 'Règle fiscale'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'obligation_type, name'

    name = fields.Char(string='Nom de la règle', required=True, tracking=True)
    code = fields.Char(string='Code de la règle', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    obligation_type = fields.Selection([
        ('turnover', 'Chiffre d’affaires'),
        ('withholding', 'Précompte'),
        ('salary', 'Retenue salariale'),
        ('rent', 'Retenue sur loyer'),
        ('annual', 'Obligation annuelle'),
        ('other', 'Autre'),
    ], string='Type d’obligation', required=True, default='other', tracking=True)
    source_type = fields.Selection(SOURCE_TYPES, string='Source de calcul', required=True, default='accounting', tracking=True)
    source_description = fields.Text(string='Périmètre de la source')
    account_ids = fields.Many2many('account.account', string='Comptes sources', check_company=True)
    journal_ids = fields.Many2many('account.journal', string='Journaux inclus', check_company=True)
    excluded_journal_ids = fields.Many2many(
        'account.journal', 'pt_tax_excluded_journal_rel', string='Journaux exclus', check_company=True,
    )
    pos_config_ids = fields.Many2many('pos.config', string='Points de vente inclus', check_company=True)
    payroll_rule_code = fields.Char(
        string='Code de règle de paie',
        help='Code de ligne du bulletin à utiliser. Laissez vide pour la ligne NET.',
    )
    period_type = fields.Selection([('month', 'Mensuelle'), ('year', 'Annuelle')], string='Périodicité', default='month', required=True)
    date_criterion = fields.Selection([
        ('accounting', 'Date comptable'),
        ('payment', 'Date de règlement'),
        ('document', 'Date du document'),
    ], string='Critère de date', default='accounting', required=True)
    aggregation = fields.Selection([
        ('debit', 'Somme des débits'),
        ('credit', 'Somme des crédits'),
        ('credit_debit', 'Crédits moins débits'),
        ('debit_credit', 'Débits moins crédits'),
        ('movement', 'Mouvements de période'),
    ], string='Méthode d’agrégation', default='credit_debit', required=True)
    rate = fields.Float(string='Taux (%)', digits=(16, 4), tracking=True)
    tax_liability_account_id = fields.Many2one('account.account', string='Compte de dette fiscale', check_company=True)
    withholding_account_id = fields.Many2one('account.account', string='Compte de précompte', check_company=True)
    credit_account_id = fields.Many2one('account.account', string='Compte de crédit fiscal', check_company=True)
    deadline_days = fields.Integer(
        string='Délai après fin de période (jours)', default=15,
        help='Nombre de jours calendaires après la fin de la période.',
    )
    responsible_id = fields.Many2one('res.users', string='Responsable du contrôle')
    eligibility_note = fields.Text(string='Conditions d’admissibilité')
    reference = fields.Char(string='Référence réglementaire')
    evidence = fields.Binary(string='Justificatif', attachment=True)
    state = fields.Selection([
        ('draft', 'Brouillon'), ('approved', 'Approuvée'), ('archived', 'Archivée'),
    ], string='Statut', default='draft', tracking=True)
    active = fields.Boolean(string='Actif', default=True)

    _sql_constraints = [
        ('rule_company_code', 'unique(company_id,code)', 'Le code doit être unique par société.'),
        ('rate_valid', 'check(rate >= 0)', 'Le taux ne peut pas être négatif.'),
        ('deadline_valid', 'check(deadline_days >= 0)', 'Le délai ne peut pas être négatif.'),
    ]

    def action_approve(self):
        self.write({'state': 'approved'})

    def _account_move_line_domain(self, date_from, date_to, simulation=False):
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('account_id', 'in', self.account_ids.ids),
            ('date', '>=', date_from), ('date', '<=', date_to),
            ('move_id.state', 'in', ['posted', 'draft'] if simulation else ['posted']),
        ]
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.excluded_journal_ids:
            domain.append(('journal_id', 'not in', self.excluded_journal_ids.ids))
        return domain if self.account_ids else [('id', '=', 0)]

    # Kept as a public compatibility method for existing report actions.
    def line_domain(self, date_from, date_to, simulation=False):
        return self._account_move_line_domain(date_from, date_to, simulation)

    def _journal_domain(self):
        domain = []
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.excluded_journal_ids:
            domain.append(('journal_id', 'not in', self.excluded_journal_ids.ids))
        return domain


class TaxPeriod(models.Model):
    _name = 'primetech.tax.period'
    _description = 'Période fiscale'
    _order = 'date_from desc'

    name = fields.Char(string='Période', compute='_compute_name', store=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(string='Date de début', required=True)
    date_to = fields.Date(string='Date de fin', required=True)
    state = fields.Selection([('open', 'Ouverte'), ('closed', 'Clôturée')], string='Statut', default='open')

    _sql_constraints = [
        ('tax_period_date', 'check(date_to >= date_from)', 'La date de fin doit être postérieure à la date de début.'),
    ]

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for record in self:
            record.name = '%s — %s' % (record.date_from or '', record.date_to or '')


class TaxDeclaration(models.Model):
    _name = 'primetech.tax.declaration'
    _description = 'Déclaration fiscale préparatoire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_id desc, id desc'

    name = fields.Char(string='Référence', default='Nouveau', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    period_id = fields.Many2one('primetech.tax.period', string='Période fiscale', required=True, check_company=True)
    rule_id = fields.Many2one('primetech.tax.rule', string='Règle fiscale', required=True, check_company=True)
    state = fields.Selection([
        ('draft', 'Brouillon'), ('calculated', 'Calculée'), ('review', 'En vérification'),
        ('validated', 'Validée'), ('filed', 'Déclarée'), ('cancelled', 'Annulée'),
    ], string='Statut', default='draft', tracking=True)
    payment_state = fields.Selection([
        ('unpaid', 'Non payé'), ('partial', 'Partiellement payé'), ('paid', 'Payé'),
    ], string='Statut du règlement', compute='_compute_payment_state', store=True, tracking=True)
    due_date = fields.Date(string='Date d’échéance', compute='_compute_due_date', store=True, index=True)
    is_overdue = fields.Boolean(string='En retard', compute='_compute_is_overdue')
    simulation = fields.Boolean(string='Simulation')
    simulation_percentage = fields.Float(default=100, string='Coefficient de simulation (%)')
    line_ids = fields.One2many('primetech.tax.declaration.line', 'declaration_id', string='Lignes de calcul')
    adjustment_ids = fields.One2many('primetech.tax.adjustment', 'declaration_id', string='Ajustements')
    credit_allocation_ids = fields.One2many('primetech.tax.credit.allocation', 'declaration_id', string='Crédits imputés')
    prepayment_allocation_ids = fields.One2many('primetech.tax.prepayment.allocation', 'declaration_id', string='Précomptes imputés')
    payment_ids = fields.Many2many('account.payment', string='Règlements de cette obligation', check_company=True)
    currency_id = fields.Many2one(string='Devise', related='company_id.currency_id', store=True)
    base_amount = fields.Monetary(string='Base fiscale', compute='_compute_totals', store=True, currency_field='currency_id')
    gross_tax = fields.Monetary(string='Impôt brut', compute='_compute_totals', store=True, currency_field='currency_id')
    prepayment_amount = fields.Monetary(string='Précomptes imputés', compute='_compute_totals', store=True, currency_field='currency_id')
    credit_amount = fields.Monetary(string='Crédits imputés', compute='_compute_totals', store=True, currency_field='currency_id')
    net_amount = fields.Monetary(string='Net à payer', compute='_compute_totals', store=True, currency_field='currency_id')
    balance_to_carry = fields.Monetary(string='Solde à reporter', compute='_compute_totals', store=True, currency_field='currency_id')
    paid_amount = fields.Monetary(string='Montant réglé', compute='_compute_payment_state', store=True, currency_field='currency_id')
    snapshot = fields.Json(string='Instantané du calcul', readonly=True, copy=False)
    prepared_by_id = fields.Many2one('res.users', string='Préparée par', default=lambda self: self.env.user, readonly=True)
    approved_by_id = fields.Many2one('res.users', string='Validée par', readonly=True)
    filing_reference = fields.Char(string='Référence de dépôt')
    filing_evidence = fields.Binary(string='Justificatif de dépôt', attachment=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('primetech.tax.declaration') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('period_id.date_to', 'rule_id.deadline_days')
    def _compute_due_date(self):
        for record in self:
            record.due_date = record.period_id.date_to + timedelta(days=record.rule_id.deadline_days or 0) if record.period_id.date_to else False

    @api.depends('due_date', 'state')
    def _compute_is_overdue(self):
        """Expose the deadline status as a boolean usable by list decorations.

        Odoo 18 evaluates list decoration expressions in JavaScript; Python
        helpers such as ``context_today`` are therefore not available there.
        """
        today = fields.Date.context_today(self)
        for record in self:
            record.is_overdue = bool(
                record.due_date
                and record.due_date < today
                and record.state not in ('filed', 'cancelled')
            )

    @api.depends(
        'line_ids.base_amount', 'line_ids.tax_amount', 'adjustment_ids.amount', 'adjustment_ids.state',
        'credit_allocation_ids.amount', 'prepayment_allocation_ids.amount', 'simulation', 'simulation_percentage',
    )
    def _compute_totals(self):
        for record in self:
            adjustments = sum(record.adjustment_ids.filtered(lambda item: item.state == 'approved').mapped('amount'))
            coefficient = record.simulation_percentage / 100 if record.simulation else 1
            base = (sum(record.line_ids.mapped('base_amount')) + adjustments) * coefficient
            gross = sum(record.line_ids.mapped('tax_amount')) * coefficient + adjustments * record.rule_id.rate / 100
            prepayments = sum(record.prepayment_allocation_ids.mapped('amount'))
            credits = sum(record.credit_allocation_ids.mapped('amount'))
            record.base_amount = base
            record.gross_tax = gross
            record.prepayment_amount = prepayments
            record.credit_amount = credits
            record.net_amount = max(gross - prepayments - credits, 0)
            record.balance_to_carry = max(prepayments + credits - gross, 0)

    @api.depends('payment_ids.amount', 'payment_ids.state', 'net_amount')
    def _compute_payment_state(self):
        for record in self:
            paid = sum(record.payment_ids.filtered(lambda payment: payment.state == 'paid').mapped('amount'))
            record.paid_amount = paid
            record.payment_state = 'paid' if record.net_amount and paid >= record.net_amount else ('partial' if paid else 'unpaid')

    def _apply_aggregation(self, debit, credit):
        self.ensure_one()
        return {
            'debit': debit,
            'credit': credit,
            'credit_debit': credit - debit,
            'debit_credit': debit - credit,
            'movement': debit + credit,
        }[self.rule_id.aggregation]

    def _new_line_values(self, label, amount, source_model, source_domain, journal=False, account=False):
        base = self._apply_aggregation(max(-amount, 0), max(amount, 0))
        return {
            'declaration_id': self.id,
            'name': label,
            'account_id': account or False,
            'journal_id': journal or False,
            'source_model': source_model,
            'source_domain': source_domain,
            'source_count': self.env[source_model].search_count(source_domain),
            'base_amount': base,
            'tax_amount': base * self.rule_id.rate / 100,
        }

    def _calculation_lines_from_accounting(self):
        rule, period = self.rule_id, self.period_id
        domain = rule._account_move_line_domain(period.date_from, period.date_to, self.simulation)
        groups = self.env['account.move.line'].read_group(
            domain, ['debit:sum', 'credit:sum'], ['account_id', 'journal_id'], lazy=False,
        )
        lines = []
        for group in groups:
            account = group.get('account_id') and group['account_id'][0]
            journal = group.get('journal_id') and group['journal_id'][0]
            label = '%s · %s' % (group.get('account_id', [''])[1], group.get('journal_id', [''])[1])
            source_domain = domain + ([('account_id', '=', account)] if account else []) + ([('journal_id', '=', journal)] if journal else [])
            amount = (group.get('credit', 0) or 0) - (group.get('debit', 0) or 0)
            lines.append(self._new_line_values(label, amount, 'account.move.line', source_domain, journal, account))
        return lines

    def _invoice_domain(self):
        period, rule = self.period_id, self.rule_id
        date_field = 'invoice_date' if rule.date_criterion != 'accounting' else 'date'
        domain = [
            ('company_id', '=', self.company_id.id), ('state', 'in', ['posted', 'draft'] if self.simulation else ['posted']),
            ('move_type', 'in', ['out_invoice', 'out_refund']), (date_field, '>=', period.date_from), (date_field, '<=', period.date_to),
        ] + rule._journal_domain()
        # A POS order already supplies its own amount: exclude linked invoice to prevent double counting.
        pos_model = self.env.registry.models.get('pos.order')
        if pos_model:
            pos_orders = self.env['pos.order'].search([
                ('company_id', '=', self.company_id.id), ('account_move', '!=', False),
                ('state', 'in', ['paid', 'done', 'invoiced']),
            ])
            if pos_orders.account_move:
                domain.append(('id', 'not in', pos_orders.account_move.ids))
        return domain

    def _calculation_lines_from_invoices(self):
        invoices = self.env['account.move'].search(self._invoice_domain())
        groups = defaultdict(lambda: {'amount': 0.0, 'ids': []})
        for invoice in invoices:
            key = invoice.journal_id.id
            amount = invoice.amount_untaxed_signed
            groups[key]['amount'] += amount
            groups[key]['ids'].append(invoice.id)
        return [
            self._new_line_values(
                self.env['account.journal'].browse(journal).display_name,
                values['amount'], 'account.move', [('id', 'in', values['ids'])], journal,
            ) for journal, values in groups.items()
        ]

    def _pos_domain(self):
        rule, period = self.rule_id, self.period_id
        domain = [
            ('company_id', '=', self.company_id.id), ('state', 'in', ['paid', 'done', 'invoiced']),
            ('date_order', '>=', fields.Datetime.to_datetime(period.date_from)),
            ('date_order', '<', fields.Datetime.to_datetime(period.date_to + timedelta(days=1))),
        ]
        if rule.pos_config_ids:
            domain.append(('config_id', 'in', rule.pos_config_ids.ids))
        if rule.journal_ids:
            domain.append(('sale_journal', 'in', rule.journal_ids.ids))
        return domain

    def _calculation_lines_from_pos(self):
        orders = self.env['pos.order'].search(self._pos_domain())
        groups = defaultdict(lambda: {'amount': 0.0, 'ids': []})
        for order in orders:
            key = order.config_id.id
            groups[key]['amount'] += order.amount_total - order.amount_tax
            groups[key]['ids'].append(order.id)
        return [
            self._new_line_values(
                self.env['pos.config'].browse(config).display_name,
                values['amount'], 'pos.order', [('id', 'in', values['ids'])],
            ) for config, values in groups.items()
        ]

    def _payment_domain(self):
        rule, period = self.rule_id, self.period_id
        return [
            ('company_id', '=', self.company_id.id), ('state', '=', 'paid'),
            ('date', '>=', period.date_from), ('date', '<=', period.date_to),
        ] + rule._journal_domain()

    def _calculation_lines_from_payments(self):
        payments = self.env['account.payment'].search(self._payment_domain())
        groups = defaultdict(lambda: {'amount': 0.0, 'ids': []})
        for payment in payments:
            sign = 1 if payment.payment_type == 'inbound' else -1
            groups[payment.journal_id.id]['amount'] += payment.amount * sign
            groups[payment.journal_id.id]['ids'].append(payment.id)
        return [
            self._new_line_values(
                self.env['account.journal'].browse(journal).display_name,
                values['amount'], 'account.payment', [('id', 'in', values['ids'])], journal,
            ) for journal, values in groups.items()
        ]

    def _payroll_model(self):
        return self.env.registry.models.get('hr.payslip') and self.env['hr.payslip']

    def _calculation_lines_from_payroll(self):
        if not self.env.user.has_group('primetech_tax_automation.group_tax_payroll'):
            raise AccessError(_('Votre utilisateur ne dispose pas de l’accès fiscal aux données de paie.'))
        payroll = self._payroll_model()
        if not payroll:
            raise UserError(_("Le module de paie n’est pas disponible. Installez-le avant de calculer une règle de paie."))
        period, rule = self.period_id, self.rule_id
        date_field = 'date_to' if 'date_to' in payroll._fields else 'date_from'
        domain = [
            ('company_id', '=', self.company_id.id), (date_field, '>=', period.date_from), (date_field, '<=', period.date_to),
            ('state', 'in', ['done', 'paid']),
        ]
        slips = payroll.search(domain)
        groups = defaultdict(lambda: {'amount': 0.0, 'ids': []})
        for slip in slips:
            if 'line_ids' not in slip._fields:
                raise UserError(_("Le modèle de paie installé ne fournit pas les lignes de bulletin attendues."))
            selected = slip.line_ids.filtered(lambda line: line.code == rule.payroll_rule_code) if rule.payroll_rule_code else slip.line_ids.filtered(lambda line: line.code == 'NET')
            amount = sum(selected.mapped('total'))
            employee = getattr(slip, 'employee_id', False)
            key = employee.id if employee else 0
            groups[key]['amount'] += amount
            groups[key]['ids'].append(slip.id)
        return [
            self._new_line_values(
                self.env['hr.employee'].browse(employee).display_name if employee else _('Paie sans salarié'),
                values['amount'], 'hr.payslip', [('id', 'in', values['ids'])],
            ) for employee, values in groups.items()
        ]

    def _calculation_values(self):
        self.ensure_one()
        return {
            'accounting': self._calculation_lines_from_accounting,
            'invoice': self._calculation_lines_from_invoices,
            'pos': self._calculation_lines_from_pos,
            'payment': self._calculation_lines_from_payments,
            'payroll': self._calculation_lines_from_payroll,
        }[self.rule_id.source_type]()

    def action_calculate(self):
        for record in self:
            if record.state not in ('draft', 'calculated'):
                raise UserError(_('Une déclaration validée doit être rectifiée, pas recalculée.'))
            record.line_ids.unlink()
            values = record._calculation_values()
            if values:
                self.env['primetech.tax.declaration.line'].create(values)
            record.state = 'calculated'

    def action_review(self):
        self.write({'state': 'review'})

    def action_validate(self):
        if not self.env.user.has_group('primetech_tax_automation.group_tax_manager'):
            raise AccessError(_('Validation réservée au responsable fiscal.'))
        for record in self:
            record.write({
                'state': 'validated', 'approved_by_id': self.env.user.id,
                'snapshot': {
                    'period': [str(record.period_id.date_from), str(record.period_id.date_to)],
                    'rule': record.rule_id.read(['code', 'name', 'source_type', 'rate', 'aggregation'])[0],
                    'base': record.base_amount, 'gross_tax': record.gross_tax,
                    'prepayments': record.prepayment_amount, 'credits': record.credit_amount,
                    'net': record.net_amount,
                },
            })

    def action_file(self):
        self.write({'state': 'filed'})

    def action_import_prepayments(self):
        """Collect accounting prepayments but leave their tax admissibility to a user."""
        for record in self:
            account = record.rule_id.withholding_account_id
            if not account:
                raise UserError(_('Configurez d’abord le compte de précompte de la règle fiscale.'))
            domain = [
                ('company_id', '=', record.company_id.id), ('account_id', '=', account.id),
                ('date', '>=', record.period_id.date_from), ('date', '<=', record.period_id.date_to),
                ('move_id.state', '=', 'posted'),
            ]
            source_lines = self.env['account.move.line'].search(domain)
            existing = self.env['primetech.tax.prepayment'].search([
                ('company_id', '=', record.company_id.id), ('account_move_line_id', 'in', source_lines.ids),
            ]).mapped('account_move_line_id')
            values = []
            for line in source_lines - existing:
                values.append({
                    'name': line.move_name or line.name or _('Précompte comptable'),
                    'company_id': record.company_id.id, 'rule_id': record.rule_id.id,
                    'partner_id': line.partner_id.id, 'date': line.date,
                    'amount_initial': abs(line.balance), 'account_move_line_id': line.id,
                    'reference': line.move_id.name,
                })
            if values:
                self.env['primetech.tax.prepayment'].create(values)
            record.message_post(body=_('%s précompte(s) comptable(s) ont été collectés et restent à contrôler.') % len(values))
        return True

    def action_open_export_csv(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/primetech_tax_automation/export/declaration/%s' % self.id,
            'target': 'self',
        }


class TaxDeclarationLine(models.Model):
    _name = 'primetech.tax.declaration.line'
    _description = 'Ligne de calcul fiscal'
    _order = 'id'

    declaration_id = fields.Many2one('primetech.tax.declaration', string='Déclaration fiscale', required=True, ondelete='cascade')
    name = fields.Char(string='Libellé', required=True)
    account_id = fields.Many2one('account.account', string='Compte comptable', check_company=True)
    journal_id = fields.Many2one('account.journal', string='Journal', check_company=True)
    source_model = fields.Char(string='Modèle source', required=True, readonly=True)
    source_domain = fields.Json(string='Filtre des éléments sources', readonly=True)
    source_count = fields.Integer(string='Nombre d’éléments sources', readonly=True)
    base_amount = fields.Monetary(string='Base fiscale', currency_field='currency_id')
    tax_amount = fields.Monetary(string='Montant de l’impôt', currency_field='currency_id')
    currency_id = fields.Many2one(string='Devise', related='declaration_id.currency_id')

    def action_sources(self):
        self.ensure_one()
        model = self.source_model
        if model not in self.env.registry.models:
            raise UserError(_('La source de cette ligne n’est plus disponible.'))
        return {
            'type': 'ir.actions.act_window', 'name': _('Éléments sources'),
            'res_model': model, 'view_mode': 'list,form', 'domain': self.source_domain or [],
        }


class TaxAdjustment(models.Model):
    _name = 'primetech.tax.adjustment'
    _description = 'Ajustement fiscal'
    _inherit = ['mail.thread']

    declaration_id = fields.Many2one('primetech.tax.declaration', string='Déclaration fiscale', required=True, ondelete='cascade')
    amount = fields.Monetary(string='Montant', required=True, currency_field='currency_id')
    reason = fields.Text(string='Motif', required=True)
    evidence = fields.Binary(string='Justificatif', attachment=True)
    state = fields.Selection([('draft', 'Brouillon'), ('approved', 'Approuvé'), ('rejected', 'Refusé')], string='Statut', default='draft')
    approved_by_id = fields.Many2one('res.users', string='Approuvé par', readonly=True)
    currency_id = fields.Many2one(string='Devise', related='declaration_id.currency_id')

    def action_approve(self):
        self.write({'state': 'approved', 'approved_by_id': self.env.user.id})


class TaxCredit(models.Model):
    _name = 'primetech.tax.credit'
    _description = 'Crédit fiscal'
    _inherit = ['mail.thread']

    name = fields.Char(string='Libellé', required=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    rule_id = fields.Many2one('primetech.tax.rule', string='Règle fiscale', required=True, check_company=True)
    amount_initial = fields.Monetary(string='Montant initial', required=True, currency_field='currency_id')
    reference = fields.Char(string='Référence')
    evidence = fields.Binary(string='Justificatif', attachment=True)
    state = fields.Selection([('draft', 'Brouillon'), ('approved', 'Admissible'), ('rejected', 'Refusé')], string='Statut', default='draft', tracking=True)
    allocation_ids = fields.One2many('primetech.tax.credit.allocation', 'credit_id', string='Imputations')
    amount_used = fields.Monetary(string='Montant imputé', compute='_compute_amounts', store=True, currency_field='currency_id')
    amount_available = fields.Monetary(string='Montant disponible', compute='_compute_amounts', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(string='Devise', related='company_id.currency_id')

    @api.depends('allocation_ids.amount')
    def _compute_amounts(self):
        for record in self:
            record.amount_used = sum(record.allocation_ids.mapped('amount'))
            record.amount_available = record.amount_initial - record.amount_used

    def action_approve(self):
        self.write({'state': 'approved'})


class TaxCreditAllocation(models.Model):
    _name = 'primetech.tax.credit.allocation'
    _description = 'Imputation de crédit fiscal'

    credit_id = fields.Many2one('primetech.tax.credit', string='Crédit fiscal', required=True, ondelete='cascade')
    declaration_id = fields.Many2one('primetech.tax.declaration', string='Déclaration fiscale', required=True, ondelete='cascade')
    amount = fields.Monetary(string='Montant imputé', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(string='Devise', related='credit_id.currency_id')

    @api.constrains('amount', 'credit_id')
    def _check_available(self):
        for record in self:
            already_used = sum(record.credit_id.allocation_ids.filtered(lambda allocation: allocation != record).mapped('amount'))
            if record.credit_id.state != 'approved' or record.amount <= 0 or record.amount > record.credit_id.amount_initial - already_used:
                raise ValidationError(_('Crédit disponible insuffisant.'))


class TaxPrepayment(models.Model):
    _name = 'primetech.tax.prepayment'
    _description = 'Précompte fiscal'
    _inherit = ['mail.thread']

    name = fields.Char(string='Libellé', required=True, default=lambda self: _('Nouveau précompte'))
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    rule_id = fields.Many2one('primetech.tax.rule', string='Règle fiscale', required=True, check_company=True)
    partner_id = fields.Many2one('res.partner', string='Tiers')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount_initial = fields.Monetary(string='Montant initial', required=True, currency_field='currency_id')
    account_move_line_id = fields.Many2one('account.move.line', string='Écriture source', check_company=True)
    reference = fields.Char(string='Référence')
    evidence = fields.Binary(string='Justificatif', attachment=True)
    state = fields.Selection([('draft', 'À contrôler'), ('approved', 'Admissible'), ('rejected', 'Refusé')], string='Statut', default='draft', tracking=True)
    allocation_ids = fields.One2many('primetech.tax.prepayment.allocation', 'prepayment_id', string='Imputations')
    amount_used = fields.Monetary(string='Montant imputé', compute='_compute_amounts', store=True, currency_field='currency_id')
    amount_available = fields.Monetary(string='Montant disponible', compute='_compute_amounts', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(string='Devise', related='company_id.currency_id')

    @api.depends('allocation_ids.amount')
    def _compute_amounts(self):
        for record in self:
            record.amount_used = sum(record.allocation_ids.mapped('amount'))
            record.amount_available = record.amount_initial - record.amount_used

    def action_approve(self):
        self.write({'state': 'approved'})


class TaxPrepaymentAllocation(models.Model):
    _name = 'primetech.tax.prepayment.allocation'
    _description = 'Imputation de précompte fiscal'

    prepayment_id = fields.Many2one('primetech.tax.prepayment', string='Précompte fiscal', required=True, ondelete='cascade')
    declaration_id = fields.Many2one('primetech.tax.declaration', string='Déclaration fiscale', required=True, ondelete='cascade')
    amount = fields.Monetary(string='Montant imputé', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(string='Devise', related='prepayment_id.currency_id')

    @api.constrains('amount', 'prepayment_id')
    def _check_available(self):
        for record in self:
            already_used = sum(record.prepayment_id.allocation_ids.filtered(lambda allocation: allocation != record).mapped('amount'))
            if record.prepayment_id.state != 'approved' or record.amount <= 0 or record.amount > record.prepayment_id.amount_initial - already_used:
                raise ValidationError(_('Précompte disponible insuffisant.'))


'''


class TaxDashboard(models.AbstractModel):
    _name = 'primetech.tax.dashboard'
    _description = 'Tableau de bord fiscal'

    @api.model
    def _range(self, date_from=None, date_to=None):
        today = fields.Date.context_today(self)
        end = fields.Date.to_date(date_to) if date_to else today
        start = fields.Date.to_date(date_from) if date_from else end.replace(day=1)
        if start > end:
            raise ValidationError(_('La date de début doit être antérieure à la date de fin.'))
        return start, end

    @api.model
    def _invoice_sales(self, company, date_from, date_to):
        domain = [
            ('company_id', '=', company.id), ('state', '=', 'posted'), ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('invoice_date', '>=', date_from), ('invoice_date', '<=', date_to),
        ]
        if self.env.registry.models.get('pos.order'):
            pos_moves = self.env['pos.order'].search([
                ('company_id', '=', company.id), ('account_move', '!=', False),
                ('state', 'in', ['paid', 'done', 'invoiced']),
                ('account_move.invoice_date', '>=', date_from),
                ('account_move.invoice_date', '<=', date_to),
            ]).account_move.ids
            if pos_moves:
                domain.append(('id', 'not in', pos_moves))
        invoices = self.env['account.move'].search(domain)
        return sum(invoices.mapped('amount_untaxed_signed')), invoices

    @api.model
    def _pos_sales(self, company, date_from, date_to):
        if not self.env.registry.models.get('pos.order'):
            return 0.0, self.env['account.move']
        domain = [
            ('company_id', '=', company.id), ('state', 'in', ['paid', 'done', 'invoiced']),
            ('date_order', '>=', fields.Datetime.to_datetime(date_from)),
            ('date_order', '<', fields.Datetime.to_datetime(date_to + timedelta(days=1))),
        ]
        orders = self.env['pos.order'].search(domain)
        return sum(order.amount_total - order.amount_tax for order in orders), orders

    @api.model
    def _payment_total(self, company, date_from, date_to):
        payments = self.env['account.payment'].search([
            ('company_id', '=', company.id), ('state', '=', 'paid'), ('date', '>=', date_from), ('date', '<=', date_to),
            ('journal_id.type', 'in', ['cash', 'bank']),
        ])
        inbound_payments = payments.filtered(lambda payment: payment.payment_type == 'inbound')
        outbound_payments = payments.filtered(lambda payment: payment.payment_type == 'outbound')
        inbound = sum(inbound_payments.mapped('amount'))
        outbound = sum(outbound_payments.mapped('amount'))
        return inbound, outbound, len(inbound_payments), len(outbound_payments)

    @api.model
    def _payroll_total(self, company, date_from, date_to):
        if not self.env.registry.models.get('hr.payslip'):
            return 0.0, 'unavailable', 0
        if not self.env.user.has_group('primetech_tax_automation.group_tax_payroll'):
            return 0.0, 'restricted', 0
        payroll = self.env['hr.payslip']
        domain = [('company_id', '=', company.id), ('state', '=', 'done')]
        if 'date_from' in payroll._fields and 'date_to' in payroll._fields:
            domain += [('date_from', '<=', date_to), ('date_to', '>=', date_from)]
        else:
            date_field = 'date_to' if 'date_to' in payroll._fields else 'date_from'
            domain += [(date_field, '>=', date_from), (date_field, '<=', date_to)]
        slips = payroll.search(domain)
        total = 0.0
        for slip in slips:
            lines = slip.line_ids if 'line_ids' in slip._fields else self.env['hr.payslip.line']
            net_lines = lines.filtered(lambda line: (line.code or '').upper() in ('NET', 'SN', 'SAL_NET'))
            net_amount = sum(net_lines.mapped('total'))
            if company.currency_id.is_zero(net_amount):
                # Certaines structures personnalisées créent bien la ligne
                # « Salaire net » mais sans formule de total. Dans ce cas,
                # le net est reconstitué à partir des lignes réellement
                # calculées, sans recompter les lignes de sous-total.
                detail_lines = lines.filtered(lambda line: (
                    (line.code or '').upper() not in ('NET', 'SN', 'SAL_NET', 'GROSS')
                    and (
                        'category_id' not in line._fields
                        or (line.category_id.code or '').upper() not in ('NET', 'GROSS')
                    )
                ))
                net_amount = sum(detail_lines.mapped('total'))
            total += net_amount
        return total, 'available', len(slips)

    @api.model
    def _sales_timeline(self, invoices, orders, date_from, date_to, period='month'):
        values = defaultdict(float)
        for invoice in invoices:
            if invoice.invoice_date:
                values[invoice.invoice_date] += invoice.amount_untaxed_signed
        for order in orders:
            if order.date_order:
                local_datetime = fields.Datetime.context_timestamp(self, order.date_order)
                values[local_datetime.date()] += order.amount_total - order.amount_tax

        day_count = (date_to - date_from).days + 1
        if period in ('month', 'quarter'):
            granularity = 'day'
        elif period == 'semester':
            granularity = 'week'
        elif period == 'year':
            granularity = 'month'
        elif day_count <= 100:
            granularity = 'day'
        elif day_count <= 400:
            granularity = 'week'
        else:
            granularity = 'month'

        month_names = (
            '', 'Janv.', 'Févr.', 'Mars', 'Avr.', 'Mai', 'Juin',
            'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.',
        )
        buckets = []
        cursor = date_from
        while cursor <= date_to:
            if granularity == 'day':
                bucket_end = cursor
                label = cursor.strftime('%d/%m')
            elif granularity == 'week':
                # Le premier intervalle se termine le dimanche, puis chaque
                # intervalle couvre une semaine complète du lundi au dimanche.
                days_to_sunday = 6 - cursor.weekday()
                bucket_end = min(cursor + timedelta(days=days_to_sunday), date_to)
                label = '%s–%s' % (cursor.strftime('%d/%m'), bucket_end.strftime('%d/%m'))
            else:
                next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
                bucket_end = min(next_month - timedelta(days=1), date_to)
                label = '%s %s' % (month_names[cursor.month], cursor.year)

            value = sum(
                amount for sale_date, amount in values.items()
                if cursor <= sale_date <= bucket_end
            )
            buckets.append({
                'key': '%s:%s' % (cursor, bucket_end),
                'label': label,
                'value': value,
                'date_from': str(cursor),
                'date_to': str(bucket_end),
            })
            cursor = bucket_end + timedelta(days=1)

        titles = {
            'day': _('Ventes par jour'),
            'week': _('Ventes par semaine'),
            'month': _('Ventes par mois'),
        }
        return buckets, titles[granularity]

    @api.model
    def get_sales_detail(self, date_from, date_to):
        """Return one coherent list for invoiced and Point of Sale sales."""
        company = self.env.company
        date_from, date_to = self._range(date_from, date_to)
        _invoice_total, invoices = self._invoice_sales(company, date_from, date_to)
        _pos_total, orders = self._pos_sales(company, date_from, date_to)
        rows = []
        for invoice in invoices:
            rows.append({
                'key': 'account.move,%s' % invoice.id,
                'model': 'account.move',
                'res_id': invoice.id,
                'source': _('Facturation'),
                'date': str(invoice.invoice_date or ''),
                'reference': invoice.name or invoice.ref or '',
                'partner': invoice.partner_id.display_name or '',
                'amount': invoice.amount_untaxed_signed,
            })
        for order in orders:
            local_datetime = fields.Datetime.context_timestamp(self, order.date_order) if order.date_order else False
            rows.append({
                'key': 'pos.order,%s' % order.id,
                'model': 'pos.order',
                'res_id': order.id,
                'source': _('Point de Vente'),
                'date': str(local_datetime.date()) if local_datetime else '',
                'reference': order.name or order.pos_reference or '',
                'partner': order.partner_id.display_name or _('Client comptoir'),
                'amount': order.amount_total - order.amount_tax,
            })
        rows.sort(key=lambda row: (row['date'], row['reference']), reverse=True)
        return {
            'date_from': str(date_from),
            'date_to': str(date_to),
            'total': sum(row['amount'] for row in rows),
            'rows': rows,
        }

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, period='month'):
        company = self.env.company
        date_from, date_to = self._range(date_from, date_to)
        invoice_total, invoices = self._invoice_sales(company, date_from, date_to)
        pos_total, orders = self._pos_sales(company, date_from, date_to)
        inbound, outbound, inbound_count, outbound_count = self._payment_total(company, date_from, date_to)
        payroll_total, payroll_status, payroll_count = self._payroll_total(company, date_from, date_to)
        declarations = self.env['primetech.dgi.tva.ir.declaration'].search([
            ('company_id', '=', company.id), ('date_from', '<=', date_to), ('date_to', '>=', date_from),
            ('state', 'not in', ['cancelled']),
        ])
        today = fields.Date.context_today(self)
        pending = declarations.filtered(lambda declaration: declaration.state != 'filed')
        status_labels = {
            'draft': _('Brouillons'),
            'calculated': _('Calculées'),
            'review': _('À vérifier'),
            'validated': _('Validées'),
            'filed': _('Déclarées'),
        }
        status_counts = {
            state: len(declarations.filtered(lambda declaration, state=state: declaration.state == state))
            for state in status_labels
        }
        status_summary = [
            {'state': state, 'label': label, 'count': status_counts[state]}
            for state, label in status_labels.items()
        ]
        source_lines = declarations.mapped('line_ids').filtered(
            lambda line: line.calculation_mode != 'formula'
        )
        section_totals = defaultdict(float)
        for line in source_lines:
            section_totals[line.section_code] += line.total_amount
        sections = self.env['primetech.dgi.tva.ir.section'].search([])
        section_names = {section.code: section.display_name for section in sections}
        section_breakdown = [
            {
                'code': section_code,
                'name': section_names.get(section_code, section_code),
                'amount': amount,
            }
            for section_code, amount in section_totals.items() if amount
        ]
        section_breakdown.sort(key=lambda item: item['amount'], reverse=True)
        overdue_count = len(pending.filtered(
            lambda declaration: declaration.due_date and declaration.due_date < today
        ))
        payable_total = sum(pending.mapped('amount_payable'))
        tax_base = sum(source_lines.mapped('base_amount'))
        completion_count = status_counts['validated'] + status_counts['filed']
        compliance_rate = (completion_count / len(declarations) * 100.0) if declarations else 0.0
        deadlines = [{
            'id': declaration.id, 'name': declaration.name, 'rule': _('Déclaration DGI TVA/IR'),
            'due_date': str(declaration.due_date or ''), 'amount': declaration.amount_payable,
            'late': bool(declaration.due_date and declaration.due_date < today),
        } for declaration in pending.sorted(lambda declaration: declaration.due_date or date_to)[:6]]
        timeline, timeline_title = self._sales_timeline(invoices, orders, date_from, date_to, period)
        return {
            'company': company.display_name, 'currency': company.currency_id.name,
            'date_from': str(date_from), 'date_to': str(date_to),
            'payroll_status': payroll_status, 'payroll_count': payroll_count,
            'refresh_interval': company.tax_dashboard_refresh_interval,
            'kpis': {
                'sales': invoice_total + pos_total,
                'invoice_sales': invoice_total, 'pos_sales': pos_total,
                'tax_base': tax_base,
                'salary_withholdings': sum(declarations.mapped('salary_withholdings')),
                'amount_due': payable_total,
                'payments_in': inbound, 'payments_out': outbound,
            },
            'analysis': {
                'declaration_count': len(declarations),
                'pending_count': len(pending),
                'overdue_count': overdue_count,
                'compliance_rate': compliance_rate,
                'tax_pressure': (payable_total / (invoice_total + pos_total) * 100.0) if (invoice_total + pos_total) else 0.0,
                'credit_to_carry': sum(declarations.mapped('credit_to_carry')),
                'status_summary': status_summary,
                'section_breakdown': section_breakdown[:5],
                'section_maximum': max([item['amount'] for item in section_breakdown] or [1.0]),
            },
            'settlements': {
                'inbound_count': inbound_count,
                'outbound_count': outbound_count,
                'payment_count': inbound_count + outbound_count,
                'net_cash_flow': inbound - outbound,
                'collection_rate': (inbound / (invoice_total + pos_total) * 100.0) if (invoice_total + pos_total) else 0.0,
                'average_receipt': (inbound / inbound_count) if inbound_count else 0.0,
            },
            'timeline': timeline,
            'timeline_title': timeline_title,
            'deadlines': deadlines,
        }


class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_dashboard_refresh_interval = fields.Integer(
        string='Actualisation du tableau fiscal (secondes)', default=60,
        help='Fréquence minimale de rafraîchissement automatique du tableau de bord fiscal.',
    )

    @api.constrains('tax_dashboard_refresh_interval')
    def _check_refresh_interval(self):
        for company in self:
            if company.tax_dashboard_refresh_interval < 30:
                raise ValidationError(_('L’actualisation automatique ne peut pas être inférieure à 30 secondes.'))


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tax_dashboard_refresh_interval = fields.Integer(
        string='Actualisation du tableau fiscal (secondes)',
        related='company_id.tax_dashboard_refresh_interval', readonly=False,
    )
