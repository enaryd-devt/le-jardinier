"""Déclaration DGI TVA/IR limitée aux rubriques applicables L45 à L76.

Le document source du client ne couvre que les rubriques 9 à 14.  Ce module
ne cherche donc pas à reproduire les pages TVA ou les autres obligations du
formulaire DGI. Les montants restent traçables vers les écritures, factures,
paiements, bulletins de paie et précomptes configurés dans Odoo.
"""

from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


SECTION_TITLES = {
    '9': '9 - ACOMPTES ET PRÉCOMPTES À DÉDUIRE',
    '10': "10 - LIQUIDATION DE L’ACOMPTE D’IMPÔT SUR LE REVENU",
    '11': '11 - RETENUES SUR REVENUS DE CAPITAUX MOBILIERS',
    '12': '12 - RETENUES SUR LA RÉMUNÉRATION DES AGENTS COMMERCIAUX',
    '13': '13 - RETENUES SUR LES REVENUS NON COMMERCIAUX',
    '14': '14 - IMPÔTS RETENUS SUR SALAIRES',
}


# ``calculation_mode`` describes the normal source. It can be replaced by a
# company-specific mapping in the configuration menu. Formula lines remain
# protected from mapping so that the legal arithmetic cannot be changed by a
# user entry.
LINE_DEFINITIONS = (
    {'code': 'L45', 'section': '9', 'sequence': 45,
     'label': 'Acompte sur chiffre d’affaires retenu à la source',
     'calculation_mode': 'prepayment', 'amount_mode': 'source_amount', 'cac_rate': 0.0},
    {'code': 'L46', 'section': '9', 'sequence': 46,
     'label': 'Précomptes sur achats',
     'calculation_mode': 'prepayment', 'amount_mode': 'source_amount', 'cac_rate': 0.0},
    {'code': 'L47', 'section': '9', 'sequence': 47,
     'label': 'Précomptes de 15 % sur loyers déductibles sur IR',
     'calculation_mode': 'prepayment', 'amount_mode': 'source_amount', 'cac_rate': 0.0},
    {'code': 'L48', 'section': '9', 'sequence': 48,
     'label': 'Précomptes sur rémunérations et honoraires',
     'calculation_mode': 'prepayment', 'amount_mode': 'source_amount', 'cac_rate': 0.0},
    {'code': 'L49', 'section': '9', 'sequence': 49,
     'label': 'TOTAL (somme L45 à L48)', 'calculation_mode': 'formula', 'formula_code': 'sum_45_48'},

    {'code': 'L50', 'section': '10', 'sequence': 50,
     'label': 'Acompte sur chiffre d’affaires déclaré',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L51', 'section': '10', 'sequence': 51,
     'label': 'Acompte de 15 % sur loyers perçus',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L52', 'section': '10', 'sequence': 52,
     'label': 'Déductions à opérer (L49)', 'calculation_mode': 'formula', 'formula_code': 'copy_l49'},
    {'code': 'L53', 'section': '10', 'sequence': 53,
     'label': 'Crédit antérieur (L55 de la déclaration précédente)',
     'calculation_mode': 'formula', 'formula_code': 'previous_credit'},
    {'code': 'L54', 'section': '10', 'sequence': 54,
     'label': 'Acompte à payer : (L50 + L51) - (L52 + L53)',
     'calculation_mode': 'formula', 'formula_code': 'payable_balance'},
    {'code': 'L55', 'section': '10', 'sequence': 55,
     'label': 'Crédit d’impôt à reporter (solde négatif L54)',
     'calculation_mode': 'formula', 'formula_code': 'credit_balance'},

    {'code': 'L56', 'section': '11', 'sequence': 56,
     'label': 'Revenus des actions, parts et obligations',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L57', 'section': '11', 'sequence': 57,
     'label': 'Dividendes distribués hors du Cameroun',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L58', 'section': '11', 'sequence': 58,
     'label': 'Rémunérations de dirigeants et jetons de présence',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L59', 'section': '11', 'sequence': 59,
     'label': 'Revenus des obligations',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L60', 'section': '11', 'sequence': 60,
     'label': 'Revenus des créances, dépôts et cautionnements',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L61', 'section': '11', 'sequence': 61,
     'label': 'Gains sur cession d’actions et obligations',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L62', 'section': '11', 'sequence': 62,
     'label': 'TOTAL retenues sur revenus de capitaux mobiliers',
     'calculation_mode': 'formula', 'formula_code': 'sum_56_61'},

    {'code': 'L63', 'section': '12', 'sequence': 63,
     'label': 'Mandataires et agents commerciaux non salariés',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L64', 'section': '12', 'sequence': 64,
     'label': 'Ventes directes',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L65', 'section': '12', 'sequence': 65,
     'label': 'TOTAL retenues sur agents commerciaux',
     'calculation_mode': 'formula', 'formula_code': 'sum_63_64'},

    {'code': 'L66', 'section': '13', 'sequence': 66,
     'label': 'Sessions de conseil d’administration',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L67', 'section': '13', 'sequence': 67,
     'label': 'Primes, gratifications, indemnités, per diem et commissions',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L68', 'section': '13', 'sequence': 68,
     'label': 'Artistes et sportifs',
     'calculation_mode': 'tax_rule', 'amount_mode': 'base_times_rate', 'cac_rate': 10.0},
    {'code': 'L69', 'section': '13', 'sequence': 69,
     'label': 'TOTAL retenues sur revenus non commerciaux',
     'calculation_mode': 'formula', 'formula_code': 'sum_66_68'},

    {'code': 'L70', 'section': '14', 'sequence': 70,
     'label': 'IRPP sur traitements et salaires',
     'calculation_mode': 'tax_rule', 'amount_mode': 'source_amount', 'cac_rate': 10.0, 'absolute_source': True},
    {'code': 'L71', 'section': '14', 'sequence': 71,
     'label': 'Crédit Foncier du Cameroun - part salariale',
     'calculation_mode': 'tax_rule', 'amount_mode': 'source_amount', 'cac_rate': 0.0, 'absolute_source': True},
    {'code': 'L72', 'section': '14', 'sequence': 72,
     'label': 'Crédit Foncier du Cameroun - part patronale',
     'calculation_mode': 'tax_rule', 'amount_mode': 'source_amount', 'cac_rate': 0.0, 'absolute_source': True},
    {'code': 'L73', 'section': '14', 'sequence': 73,
     'label': 'Fonds National de l’Emploi',
     'calculation_mode': 'tax_rule', 'amount_mode': 'source_amount', 'cac_rate': 0.0, 'absolute_source': True},
    {'code': 'L74', 'section': '14', 'sequence': 74,
     'label': 'Redevance audiovisuelle',
     'calculation_mode': 'tax_rule', 'amount_mode': 'source_amount', 'cac_rate': 0.0, 'absolute_source': True},
    {'code': 'L75', 'section': '14', 'sequence': 75,
     'label': 'Taxe de développement local',
     'calculation_mode': 'tax_rule', 'amount_mode': 'source_amount', 'cac_rate': 0.0, 'absolute_source': True},
    {'code': 'L76', 'section': '14', 'sequence': 76,
     'label': 'TOTAL impôts retenus sur salaires',
     'calculation_mode': 'formula', 'formula_code': 'sum_70_75'},
)

LINE_BY_CODE = {definition['code']: definition for definition in LINE_DEFINITIONS}
LINE_CODE_SELECTION = [(definition['code'], '%s - %s' % (definition['code'], definition['label'])) for definition in LINE_DEFINITIONS]
MAPPING_LINE_CODE_SELECTION = [
    (definition['code'], '%s - %s' % (definition['code'], definition['label']))
    for definition in LINE_DEFINITIONS if definition['calculation_mode'] != 'formula'
]

# In the Cameroonian chart of accounts, as in standard double-entry
# accounting, assets and expenses normally carry a debit balance; liabilities,
# equity and income normally carry a credit balance.  This lets the mapping
# remain as simple as selecting the source accounts.
DEBIT_NORMAL_ACCOUNT_TYPES = frozenset({
    'asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current',
    'asset_prepayments', 'asset_fixed', 'expense', 'expense_depreciation',
    'expense_direct_cost',
})


class DgiTvaIrSection(models.Model):
    _name = 'primetech.dgi.tva.ir.section'
    _description = 'Rubrique DGI TVA/IR'
    _order = 'sequence, code, id'
    _rec_name = 'display_name'

    code = fields.Char(string='Identifiant technique', required=True, index=True, readonly=True, copy=False)
    name = fields.Char(string='Libellé', required=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    sequence = fields.Integer(string='Ordre technique', required=True, default=100, readonly=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('dgi_tva_ir_section_code_unique', 'unique(code)',
         'Le code de rubrique DGI doit être unique.'),
    ]

    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name or ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('primetech.dgi.tva.ir.section')
        return super().create(vals_list)

    def write(self, vals):
        previous_codes = {section.id: section.code for section in self} if 'code' in vals else {}
        result = super().write(vals)
        if previous_codes:
            line_definitions = self.env['primetech.dgi.tva.ir.line.definition']
            declaration_lines = self.env['primetech.dgi.tva.ir.line']
            for section in self:
                previous_code = previous_codes[section.id]
                if previous_code == section.code:
                    continue
                line_definitions.search([('section_id', '=', section.id)]).write({
                    'section_code': section.code,
                })
                declaration_lines.search([('section_code', '=', previous_code)]).write({
                    'section_code': section.code,
                })
        return result

    @api.model
    def _load_default_sections(self):
        """Create the current DGI sections once, without overwriting user edits."""
        for code, name in SECTION_TITLES.items():
            if not self.search_count([('code', '=', code)]):
                self.create({
                    'code': code,
                    'name': name,
                    'sequence': int(code) if code.isdigit() else 100,
                })


class DgiTvaIrLineDefinition(models.Model):
    _name = 'primetech.dgi.tva.ir.line.definition'
    _description = 'Ligne DGI TVA/IR'
    _order = 'sequence, code, id'
    _rec_name = 'display_name'

    code = fields.Char(string='Code DGI', required=True, index=True)
    name = fields.Char(string='Libellé', required=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    section_id = fields.Many2one(
        'primetech.dgi.tva.ir.section', string='Rubrique DGI', ondelete='restrict',
    )
    section_code = fields.Selection(selection='_selection_section_code', string='Code rubrique', required=True, default='9')
    sequence = fields.Integer(string='Ordre', required=True, default=100)
    calculation_mode = fields.Selection([
        ('accounts', 'Depuis les comptes comptables'),
        ('formula', 'Calcul DGI automatique'),
    ], string='Type de ligne', required=True, default='accounts')
    formula_code = fields.Char(string='Formule technique', readonly=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('dgi_tva_ir_line_definition_code_unique', 'unique(code)',
         'Le code DGI doit être unique.'),
    ]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = '%s - %s' % (record.code or '', record.name or '')

    @api.model
    def _selection_section_code(self):
        sections = self.env['primetech.dgi.tva.ir.section'].search([])
        return [(section.code, section.display_name) for section in sections]

    @api.onchange('section_id')
    def _onchange_section_id(self):
        for record in self:
            if record.section_id:
                record.section_code = record.section_id.code

    @api.onchange('calculation_mode')
    def _onchange_calculation_mode(self):
        for record in self:
            # A user-created automatic line becomes the total of its
            # rubrique.  Legal formulas already configured on the standard
            # lines (L49, L54, etc.) are deliberately preserved.
            if record.calculation_mode == 'formula' and not record.formula_code:
                record.formula_code = 'section_total'

    @api.model
    def _automatic_sequence(self, code):
        """Derive the display order from a standard DGI line code (L44, L77)."""
        code = (code or '').strip().upper()
        if code.startswith('L') and code[1:].isdigit():
            return int(code[1:])
        return 1000

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sequence' not in vals:
                vals['sequence'] = self._automatic_sequence(vals.get('code'))
            if vals.get('calculation_mode') == 'formula' and not vals.get('formula_code'):
                vals['formula_code'] = 'section_total'
            if vals.get('section_id'):
                section = self.env['primetech.dgi.tva.ir.section'].browse(vals['section_id']).exists()
                if section:
                    vals['section_code'] = section.code
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if 'code' in vals and 'sequence' not in vals:
            vals['sequence'] = self._automatic_sequence(vals['code'])
        if vals.get('calculation_mode') == 'formula' and not vals.get('formula_code'):
            vals['formula_code'] = 'section_total'
        if vals.get('section_id'):
            section = self.env['primetech.dgi.tva.ir.section'].browse(vals['section_id']).exists()
            if section:
                vals['section_code'] = section.code
        return super().write(vals)

    @api.model
    def _load_default_line_definitions(self):
        """Create the editable client defaults L45 to L75 without overwriting changes."""
        sections_by_code = {
            section.code: section
            for section in self.env['primetech.dgi.tva.ir.section'].search([])
        }
        for definition in LINE_DEFINITIONS:
            if not 45 <= definition['sequence'] <= 75:
                continue
            line_definition = self.search([('code', '=', definition['code'])], limit=1)
            if line_definition:
                if not line_definition.section_id and sections_by_code.get(definition['section']):
                    line_definition.write({'section_id': sections_by_code[definition['section']].id})
                continue
            self.create({
                'code': definition['code'],
                'name': definition['label'],
                'section_id': sections_by_code.get(definition['section']).id if sections_by_code.get(definition['section']) else False,
                'section_code': definition['section'],
                'sequence': definition['sequence'],
                'calculation_mode': 'formula' if definition['calculation_mode'] == 'formula' else 'accounts',
                'formula_code': definition.get('formula_code'),
            })

        # Link historical records created before the configurable line model
        # was introduced.  Their code and accounting amounts remain intact.
        for line_definition in self.search([]):
            self.env['primetech.dgi.tva.ir.mapping'].search([
                ('line_definition_id', '=', False), ('line_code', '=', line_definition.code),
            ]).write({'line_definition_id': line_definition.id})
            self.env['primetech.dgi.tva.ir.line'].search([
                ('line_definition_id', '=', False), ('line_code', '=', line_definition.code),
            ]).write({'line_definition_id': line_definition.id})


class DgiTvaIrMapping(models.Model):
    _name = 'primetech.dgi.tva.ir.mapping'
    _description = 'Correspondance DGI TVA/IR'
    _order = 'line_code'
    _rec_name = 'line_code'

    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    line_definition_id = fields.Many2one(
        'primetech.dgi.tva.ir.line.definition', string='Ligne DGI',
        ondelete='restrict',
        domain="[('active', '=', True), ('calculation_mode', '!=', 'formula')]",
    )
    line_code = fields.Selection(
        selection='_selection_line_code', string='Code DGI', required=True,
        index=True, readonly=True,
    )
    account_ids = fields.Many2many(
        'account.account', 'primetech_dgi_tva_ir_mapping_account_rel', 'mapping_id', 'account_id',
        string='Comptes comptables sources', check_company=True,
        help='Comptes du plan comptable dont les écritures alimentent cette ligne DGI.',
    )
    calculation_mode = fields.Selection([
        ('accounts', 'Écritures des comptes comptables'),
    ], string='Mode de calcul', required=True, default='accounts')
    amount_mode = fields.Selection([
        ('base_times_rate', 'Base × taux'),
        ('source_amount', 'Montant provenant directement de la source'),
        ('fixed_amount', 'Montant fixe'),
    ], string='Origine du principal', required=True, default='base_times_rate')
    fixed_amount = fields.Monetary(
        string='Montant fixe à déclarer', currency_field='currency_id',
        help='Montant principal appliqué à chaque calcul de la déclaration, sans lecture des comptes comptables.',
    )
    currency_id = fields.Many2one(related='company_id.currency_id', string='Devise')
    rate = fields.Float(string='Taux (%)', digits=(16, 4), help='Vide : le taux de la règle fiscale est utilisé.')
    cac_rate = fields.Float(string='Taux CAC (%)', digits=(16, 4), default=10.0)
    absolute_source = fields.Boolean(
        string='Utiliser la valeur absolue',
        help='À utiliser notamment lorsque la règle de paie restitue une retenue avec un signe négatif.',
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string='Note de paramétrage')

    _sql_constraints = [
        ('dgi_tva_ir_mapping_company_line_unique', 'unique(company_id, line_code)',
         'Une seule correspondance est autorisée par société et ligne DGI.'),
        ('dgi_tva_ir_mapping_rates_non_negative', 'check(rate >= 0 and cac_rate >= 0 and fixed_amount >= 0)',
         'Les taux et le montant fixe ne peuvent pas être négatifs.'),
    ]

    @api.model
    def _selection_line_code(self):
        definitions = self.env['primetech.dgi.tva.ir.line.definition'].search([])
        return [(definition.code, definition.display_name) for definition in definitions]

    @api.onchange('line_definition_id')
    def _onchange_line_definition_id(self):
        for record in self:
            line_definition = record.line_definition_id
            definition = LINE_BY_CODE.get(line_definition.code, {}) if line_definition else {}
            if line_definition:
                record.line_code = line_definition.code
                # The operational setup is deliberately account based: the
                # accountant only selects the chart-of-accounts sources.
                record.calculation_mode = 'accounts'
                record.amount_mode = definition.get('amount_mode', 'source_amount')
                record.cac_rate = definition.get('cac_rate', 0.0)
                record.absolute_source = definition.get('absolute_source', False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            line_definition_id = vals.get('line_definition_id')
            if line_definition_id:
                line_definition = self.env['primetech.dgi.tva.ir.line.definition'].browse(line_definition_id).exists()
                if line_definition:
                    vals['line_code'] = line_definition.code
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('line_definition_id'):
            line_definition = self.env['primetech.dgi.tva.ir.line.definition'].browse(vals['line_definition_id']).exists()
            if line_definition:
                vals = dict(vals, line_code=line_definition.code)
        return super().write(vals)

    @api.constrains('line_definition_id', 'line_code', 'account_ids', 'amount_mode', 'fixed_amount')
    def _check_formula_lines_are_not_mapped(self):
        for record in self:
            if not record.line_definition_id:
                raise ValidationError(_('Veuillez sélectionner une ligne DGI.'))
            if record.line_definition_id.calculation_mode == 'formula':
                raise ValidationError(_('Les lignes de total et de liquidation sont calculées automatiquement et ne peuvent pas être paramétrées.'))
            if record.amount_mode != 'fixed_amount' and not record.account_ids:
                raise ValidationError(_('Sélectionnez au moins un compte comptable source pour cette ligne DGI.'))
            if record.amount_mode == 'fixed_amount' and record.fixed_amount <= 0:
                raise ValidationError(_('Indiquez un montant fixe strictement positif.'))


class DgiTvaIrDeclaration(models.Model):
    _name = 'primetech.dgi.tva.ir.declaration'
    _description = 'Déclaration DGI TVA/IR - rubriques L45 à L76'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(string='Référence', default='Nouveau', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(string='Du', index=True)
    date_to = fields.Date(string='Au', index=True)
    period_end_date = fields.Date(
        string='Fin de période', related='date_to', store=True, index=True, readonly=True,
        help='Champ technique utilisé pour retrouver de manière fiable la déclaration DGI précédente.',
    )
    tax_center = fields.Char(string='Centre des impôts')
    niu = fields.Char(string='NIU', related='company_id.vat', readonly=True)
    form_version = fields.Char(
        string='Version du formulaire DGI', compute='_compute_form_version', store=True, readonly=True,
    )
    due_date = fields.Date(string='Échéance', compute='_compute_due_date', store=True)
    previous_declaration_id = fields.Many2one(
        'primetech.dgi.tva.ir.declaration', string='Déclaration précédente', check_company=True,
        domain="[('company_id', '=', company_id), ('id', '!=', id), ('state', 'in', ['validated', 'filed'])]",
    )
    state = fields.Selection([
        ('draft', 'Brouillon'), ('calculated', 'Calculée'), ('review', 'En vérification'),
        ('validated', 'Validée'), ('filed', 'Déclarée'), ('cancelled', 'Annulée'),
    ], string='Statut', required=True, default='draft', tracking=True)
    line_ids = fields.One2many('primetech.dgi.tva.ir.line', 'declaration_id', string='Rubriques DGI', copy=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Devise', store=True)
    amount_payable = fields.Monetary(string='Acompte à payer (L54)', compute='_compute_summary', store=True, currency_field='currency_id')
    credit_to_carry = fields.Monetary(string='Crédit à reporter (L55)', compute='_compute_summary', store=True, currency_field='currency_id')
    salary_withholdings = fields.Monetary(string='Retenues sur salaires (L76)', compute='_compute_summary', store=True, currency_field='currency_id')
    snapshot = fields.Json(string='Instantané de validation', readonly=True, copy=False)
    prepared_by_id = fields.Many2one('res.users', string='Préparée par', default=lambda self: self.env.user, readonly=True)
    approved_by_id = fields.Many2one('res.users', string='Validée par', readonly=True)
    filing_reference = fields.Char(string='Référence de télédéclaration')
    filing_evidence = fields.Binary(string='Justificatif de dépôt', attachment=True)
    note = fields.Text(string='Observations')

    _sql_constraints = [
        ('dgi_tva_ir_declaration_company_dates_unique', 'unique(company_id, date_from, date_to)',
         'Une seule déclaration DGI TVA/IR est autorisée par société et période.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('primetech.dgi.tva.ir.declaration') or 'Nouveau'
        declarations = super().create(vals_list)
        for declaration in declarations:
            if not declaration.line_ids:
                self.env['primetech.dgi.tva.ir.line'].create(declaration._default_line_values())
            if not declaration.previous_declaration_id:
                declaration.previous_declaration_id = declaration._find_previous_declaration()
        return declarations

    def write(self, vals):
        return super().write(vals)

    @api.onchange('company_id', 'date_from', 'date_to')
    def _onchange_period_or_company(self):
        for record in self:
            record.previous_declaration_id = record._find_previous_declaration()

    @api.constrains('date_from', 'date_to')
    def _check_declaration_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_to < record.date_from:
                raise ValidationError(_('La date de fin doit être postérieure ou égale à la date de début.'))

    @api.depends('date_to')
    def _compute_due_date(self):
        for record in self:
            record.due_date = record.date_to + timedelta(days=15) if record.date_to else False

    @api.depends('line_ids.line_code')
    def _compute_form_version(self):
        """Describe the actual DGI line range included in each declaration."""
        for record in self:
            numbers = []
            for code in record.line_ids.mapped('line_code'):
                digits = ''.join(character for character in (code or '') if character.isdigit())
                if digits:
                    numbers.append(int(digits))
            record.form_version = (
                _('Rubriques DGI L%s à L%s') % (min(numbers), max(numbers))
                if numbers else _('Rubriques DGI')
            )

    @api.depends('line_ids.total_amount', 'line_ids.line_code')
    def _compute_summary(self):
        for record in self:
            line_values = {line.line_code: line.total_amount for line in record.line_ids}
            record.amount_payable = line_values.get('L54', 0.0)
            record.credit_to_carry = line_values.get('L55', 0.0)
            # L76 is a printed total only.  It is kept for historical
            # declarations, while new declarations contain only L45 to L75.
            record.salary_withholdings = line_values.get(
                'L76', sum(line_values.get(code, 0.0) for code in ('L70', 'L71', 'L72', 'L73', 'L74', 'L75')),
            )

    def _find_previous_declaration(self):
        self.ensure_one()
        date_from = self.date_from
        if not self.company_id or not date_from:
            return False
        return self.search([
            ('company_id', '=', self.company_id.id),
            ('period_end_date', '<', date_from),
            ('state', 'in', ['validated', 'filed']),
        ], order='period_end_date desc, id desc', limit=1)

    def _default_line_values(self):
        self.ensure_one()
        mappings = self.env['primetech.dgi.tva.ir.mapping'].search([
            ('company_id', '=', self.company_id.id), ('active', '=', True),
        ])
        mappings_by_code = {mapping.line_code: mapping for mapping in mappings}
        values = []
        definitions = self.env['primetech.dgi.tva.ir.line.definition'].search([('active', '=', True)])
        for line_definition in definitions:
            definition = LINE_BY_CODE.get(line_definition.code, {})
            mapping = mappings_by_code.get(line_definition.code)
            line_values = {
                'declaration_id': self.id,
                'line_definition_id': line_definition.id,
                'line_code': line_definition.code,
                'section_code': line_definition.section_code,
                'sequence': line_definition.sequence,
                'name': line_definition.name,
                'calculation_mode': line_definition.calculation_mode,
                'amount_mode': definition.get('amount_mode', 'source_amount'),
                'cac_rate': definition.get('cac_rate', 0.0),
                'absolute_source': definition.get('absolute_source', False),
                'formula_code': line_definition.formula_code,
            }
            if mapping and line_definition.calculation_mode != 'formula':
                line_values.update({
                    'mapping_id': mapping.id,
                    # A configured chart-of-accounts source always takes
                    # precedence over the legacy rule/prepayment modes.
                    'calculation_mode': 'fixed' if mapping.amount_mode == 'fixed_amount' else 'accounts',
                    'amount_mode': mapping.amount_mode,
                    'source_account_ids': [(6, 0, mapping.account_ids.ids)],
                    'rate': mapping.rate,
                    'cac_rate': mapping.cac_rate,
                    'fixed_amount': mapping.fixed_amount,
                    'absolute_source': mapping.absolute_source,
                })
            values.append(line_values)
        return values

    def _sync_mapping_values(self):
        """Apply the current line type and active account mappings to declaration lines."""
        for declaration in self:
            mappings = self.env['primetech.dgi.tva.ir.mapping'].search([
                ('company_id', '=', declaration.company_id.id), ('active', '=', True),
            ])
            mapping_by_code = {mapping.line_code: mapping for mapping in mappings}
            for line in declaration.line_ids:
                line_definition = line.line_definition_id
                if line_definition and line_definition.calculation_mode == 'formula':
                    line.write({
                        'mapping_id': False,
                        'calculation_mode': 'formula',
                        'formula_code': line_definition.formula_code or 'section_total',
                        'source_account_ids': [(5, 0, 0)],
                        'source_count': 0,
                    })
                    continue
                mapping = mapping_by_code.get(line.line_code)
                if not mapping:
                    if line_definition:
                        line.write({
                            'calculation_mode': 'accounts',
                            'formula_code': False,
                        })
                    continue
                line.write({
                    'mapping_id': mapping.id,
                    # Existing mappings created before the simplified setup
                    # can still carry a legacy mode.  Once accounts are
                    # selected, calculations must read those accounts.
                    'calculation_mode': 'fixed' if mapping.amount_mode == 'fixed_amount' else 'accounts',
                    'amount_mode': mapping.amount_mode,
                    'source_account_ids': [(6, 0, mapping.account_ids.ids)],
                    'rate': mapping.rate,
                    'cac_rate': mapping.cac_rate,
                    'fixed_amount': mapping.fixed_amount,
                    'absolute_source': mapping.absolute_source,
                    'formula_code': False,
                })

    @staticmethod
    def _aggregate_value(aggregation, debit, credit):
        return {
            'debit': debit,
            'credit': credit,
            'credit_debit': credit - debit,
            'debit_credit': debit - credit,
            'movement': debit + credit,
        }[aggregation]

    @staticmethod
    def _account_type_aggregation(account_type):
        """Return the normal balance direction for an Odoo account type."""
        return 'debit_credit' if account_type in DEBIT_NORMAL_ACCOUNT_TYPES else 'credit_debit'

    @classmethod
    def _aggregate_rule_value(cls, rule, debit, credit):
        return cls._aggregate_value(rule.aggregation, debit, credit)

    @staticmethod
    def _json_value(value):
        if isinstance(value, datetime):
            return fields.Datetime.to_string(value)
        if isinstance(value, date):
            return fields.Date.to_string(value)
        if isinstance(value, tuple):
            return [DgiTvaIrDeclaration._json_value(item) for item in value]
        if isinstance(value, list):
            return [DgiTvaIrDeclaration._json_value(item) for item in value]
        return value

    @classmethod
    def _json_domain(cls, domain):
        return [
            [item[0], item[1], cls._json_value(item[2])] if isinstance(item, (list, tuple)) and len(item) == 3 else item
            for item in domain
        ]

    def _invoice_domain_from_rule(self, rule):
        date_from, date_to = self.date_from, self.date_to
        date_field = 'invoice_date' if rule.date_criterion != 'accounting' else 'date'
        domain = [
            ('company_id', '=', self.company_id.id), ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            (date_field, '>=', date_from), (date_field, '<=', date_to),
        ] + rule._journal_domain()
        if self.env.registry.models.get('pos.order'):
            pos_orders = self.env['pos.order'].search([
                ('company_id', '=', self.company_id.id), ('account_move', '!=', False),
                ('state', 'in', ['paid', 'done', 'invoiced']),
            ])
            if pos_orders.account_move:
                domain.append(('id', 'not in', pos_orders.account_move.ids))
        return domain

    def _source_from_accounts(self, line):
        """Read the selected chart-of-accounts balances for one DGI line."""
        self.ensure_one()
        if not line.source_account_ids:
            return 0.0, 'account.move.line', [('id', '=', 0)], 0, False
        domain = [
            ('company_id', '=', self.company_id.id),
            ('move_id.state', '=', 'posted'),
            ('account_id', 'in', line.source_account_ids.ids),
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
        ]
        grouped = self.env['account.move.line'].read_group(
            domain, ['debit:sum', 'credit:sum'], ['account_id'], lazy=False,
        )
        accounts_by_id = {account.id: account for account in line.source_account_ids}
        amount = 0.0
        for values in grouped:
            account_value = values.get('account_id')
            account_id = account_value[0] if isinstance(account_value, (list, tuple)) else account_value
            account = accounts_by_id.get(account_id)
            if not account:
                continue
            amount += self._aggregate_value(
                self._account_type_aggregation(account.account_type),
                values.get('debit', 0.0) or 0.0,
                values.get('credit', 0.0) or 0.0,
            )
        return amount, 'account.move.line', domain, self.env['account.move.line'].search_count(domain), False

    '''Anciennes sources fondées sur les règles fiscales et les précomptes.

    def _source_from_rule(self, rule):
        """Return source amount and a drill-down domain for a fiscal rule."""
        self.ensure_one()
        period = self.period_id
        if rule.source_type == 'accounting':
            domain = rule._account_move_line_domain(period.date_from, period.date_to, False)
            grouped = self.env['account.move.line'].read_group(domain, ['debit:sum', 'credit:sum'], [], lazy=False)
            values = grouped[0] if grouped else {}
            amount = self._aggregate_rule_value(rule, values.get('debit', 0.0) or 0.0, values.get('credit', 0.0) or 0.0)
            return amount, 'account.move.line', domain, self.env['account.move.line'].search_count(domain), False

        if rule.source_type == 'invoice':
            domain = self._invoice_domain_from_rule(rule)
            invoices = self.env['account.move'].search(domain)
            return sum(invoices.mapped('amount_untaxed_signed')), 'account.move', domain, len(invoices), False

        if rule.source_type == 'pos':
            domain = [
                ('company_id', '=', self.company_id.id), ('state', 'in', ['paid', 'done', 'invoiced']),
                ('date_order', '>=', fields.Datetime.to_datetime(period.date_from)),
                ('date_order', '<', fields.Datetime.to_datetime(period.date_to + timedelta(days=1))),
            ]
            if rule.pos_config_ids:
                domain.append(('config_id', 'in', rule.pos_config_ids.ids))
            if rule.journal_ids:
                domain.append(('sale_journal', 'in', rule.journal_ids.ids))
            orders = self.env['pos.order'].search(domain)
            return sum(order.amount_total - order.amount_tax for order in orders), 'pos.order', domain, len(orders), False

        if rule.source_type == 'payment':
            domain = [
                ('company_id', '=', self.company_id.id), ('state', '=', 'paid'),
                ('date', '>=', period.date_from), ('date', '<=', period.date_to),
            ] + rule._journal_domain()
            payments = self.env['account.payment'].search(domain)
            amount = sum(payment.amount if payment.payment_type == 'inbound' else -payment.amount for payment in payments)
            payment_date = payments.date if len(payments) == 1 else False
            return amount, 'account.payment', domain, len(payments), payment_date

        if rule.source_type == 'payroll':
            if not self.env.user.has_group('primetech_tax_automation.group_tax_payroll'):
                raise AccessError(_('Votre utilisateur ne dispose pas de l’accès fiscal aux données de paie.'))
            if not self.env.registry.models.get('hr.payslip'):
                raise UserError(_('Le module de paie doit être installé pour calculer cette ligne DGI.'))
            payslip_model = self.env['hr.payslip']
            date_field = 'date_to' if 'date_to' in payslip_model._fields else 'date_from'
            domain = [
                ('company_id', '=', self.company_id.id), (date_field, '>=', period.date_from),
                (date_field, '<=', period.date_to), ('state', 'in', ['done', 'paid']),
            ]
            slips = payslip_model.search(domain)
            amount = 0.0
            for slip in slips:
                if 'line_ids' not in slip._fields:
                    raise UserError(_('Le modèle de paie ne fournit pas les lignes de bulletin attendues.'))
                selected = slip.line_ids.filtered(lambda item: item.code == rule.payroll_rule_code) if rule.payroll_rule_code else slip.line_ids.filtered(lambda item: item.code == 'NET')
                amount += sum(selected.mapped('total'))
            return amount, 'hr.payslip', domain, len(slips), False

        raise UserError(_('La source de la règle fiscale « %s » est inconnue.') % rule.display_name)

    def _source_from_prepayments(self, line):
        """Compute available approved prepayments without reserving them in draft.

        Reserving happens only on validation, preventing one draft declaration
        from blocking the accountant while avoiding double use once validated.
        """
        domain = [
            ('company_id', '=', self.company_id.id), ('state', '=', 'approved'),
            ('date', '>=', self.period_id.date_from), ('date', '<=', self.period_id.date_to),
        ]
        if line.tax_rule_id:
            domain.append(('rule_id', '=', line.tax_rule_id.id))
        prepayments = self.env['primetech.tax.prepayment'].search(domain)
        amount = 0.0
        used_by_others = 0.0
        for prepayment in prepayments:
            generic_used = sum(prepayment.allocation_ids.mapped('amount'))
            dgi_used_by_others = sum(prepayment.dgi_tva_ir_allocation_ids.filtered(
                lambda allocation: allocation.declaration_id != self
            ).mapped('amount'))
            used_by_others += generic_used + dgi_used_by_others
            amount += max(prepayment.amount_initial - generic_used - dgi_used_by_others, 0.0)
        return amount, 'primetech.tax.prepayment', domain, len(prepayments), False, used_by_others

    ''' 

    def _write_line_amounts(self, line, base=0.0, principal=0.0, cac=0.0, penalty=0.0, **extra):
        values = {
            'base_amount': base,
            'principal_amount': principal,
            'cac_amount': cac,
            'penalty_amount': penalty,
        }
        values.update(extra)
        line.write(values)

    def _calculate_source_lines(self):
        for declaration in self:
            for line in declaration.line_ids.filtered(lambda item: item.calculation_mode == 'accounts'):
                amount, model, domain, count, payment_date = declaration._source_from_accounts(line)
                if line.absolute_source:
                    amount = abs(amount)
                # The DGI grid does not accept negative declared bases. Credit
                # notes reduce the source total but cannot turn a line into a
                # negative amount; they are handled through the period balance.
                amount = max(amount, 0.0)
                if line.amount_mode == 'base_times_rate':
                    base = amount
                    principal = base * line.rate / 100.0
                else:
                    base = amount
                    principal = amount
                declaration._write_line_amounts(
                    line, base=base, principal=principal,
                    cac=principal * line.cac_rate / 100.0,
                    penalty=line.penalty_amount,
                    source_model=model, source_domain=declaration._json_domain(domain),
                    source_count=count, payment_date=payment_date or line.payment_date,
                )
            for line in declaration.line_ids.filtered(lambda item: item.calculation_mode == 'fixed'):
                principal = line.fixed_amount
                declaration._write_line_amounts(
                    line, base=0.0, principal=principal,
                    cac=principal * line.cac_rate / 100.0,
                    penalty=line.penalty_amount,
                    source_model=False, source_domain=[], source_count=0,
                )

    @staticmethod
    def _components(line):
        return line.principal_amount, line.cac_amount, line.penalty_amount

    def _calculate_formula_lines(self):
        for declaration in self:
            by_code = {line.line_code: line for line in declaration.line_ids}

            def amounts_sum(codes):
                source_lines = [by_code[code] for code in codes if by_code.get(code)]
                components = [self._components(line) for line in source_lines]
                return (
                    sum(line.base_amount for line in source_lines),
                    tuple(sum(item[index] for item in components) for index in range(3)),
                )

            totals = {
                'sum_45_48': amounts_sum(('L45', 'L46', 'L47', 'L48')),
                'sum_56_61': amounts_sum(('L56', 'L57', 'L58', 'L59', 'L60', 'L61')),
                'sum_63_64': amounts_sum(('L63', 'L64')),
                'sum_66_68': amounts_sum(('L66', 'L67', 'L68')),
                'sum_70_75': amounts_sum(('L70', 'L71', 'L72', 'L73', 'L74', 'L75')),
            }
            for formula, (base, components) in totals.items():
                formula_line = next((line for line in declaration.line_ids if line.formula_code == formula), False)
                if formula_line:
                    declaration._write_line_amounts(formula_line, base=base, principal=components[0], cac=components[1], penalty=components[2])

            # Formula lines added by the user provide a clear total for the
            # selected rubrique.  Only source lines are included, preventing
            # any double count of legal formulas or other total lines.
            for formula_line in declaration.line_ids.filtered(lambda line: line.formula_code == 'section_total'):
                source_lines = declaration.line_ids.filtered(
                    lambda line: line.section_code == formula_line.section_code
                    and line.calculation_mode != 'formula'
                )
                components = [self._components(line) for line in source_lines]
                declaration._write_line_amounts(
                    formula_line,
                    base=sum(source_lines.mapped('base_amount')),
                    principal=sum(item[0] for item in components),
                    cac=sum(item[1] for item in components),
                    penalty=sum(item[2] for item in components),
                )

            l49 = by_code.get('L49')
            l52 = by_code.get('L52')
            if l52:
                components = self._components(l49) if l49 else (0.0, 0.0, 0.0)
                declaration._write_line_amounts(l52, principal=components[0], cac=components[1], penalty=components[2])

            l53 = by_code.get('L53')
            if l53:
                credit = declaration.previous_declaration_id.credit_to_carry if declaration.previous_declaration_id else 0.0
                declaration._write_line_amounts(l53, principal=credit)

            _positive_base, positive = amounts_sum(('L50', 'L51'))
            _negative_base, negative = amounts_sum(('L52', 'L53'))
            l54 = by_code.get('L54')
            if l54:
                payable = tuple(max(positive[index] - negative[index], 0.0) for index in range(3))
                declaration._write_line_amounts(l54, principal=payable[0], cac=payable[1], penalty=payable[2])
            l55 = by_code.get('L55')
            if l55:
                credit = max(sum(negative) - sum(positive), 0.0)
                declaration._write_line_amounts(l55, principal=credit)

    def action_calculate(self):
        no_source_found = False
        for declaration in self:
            if declaration.state not in ('draft', 'calculated', 'review'):
                raise UserError(_('Une déclaration validée doit être rectifiée, pas recalculée.'))
            if not declaration.date_from or not declaration.date_to:
                raise UserError(_('Renseignez les dates « Du » et « Au » avant de lancer le calcul.'))
            declaration._sync_mapping_values()
            declaration._calculate_source_lines()
            declaration._calculate_formula_lines()
            declaration.state = 'calculated'
            declaration.message_post(body=_('Les rubriques DGI L45 à L76 ont été recalculées.'))
            account_lines = declaration.line_ids.filtered(
                lambda line: line.mapping_id and line.calculation_mode == 'accounts'
            )
            if account_lines and not any(account_lines.mapped('source_count')):
                no_source_found = True
        if no_source_found:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': _('Calcul terminé sans écriture source'),
                    'message': _(
                        'Aucune écriture comptabilisée n’a été trouvée dans les comptes configurés pour la période sélectionnée.'
                    ),
                    'sticky': False,
                },
            }
        return True

    def action_review(self):
        self.write({'state': 'review'})
        return True

    '''Ancienne réservation des précomptes, retirée du parcours DGI.

    def _sync_prepayment_allocations(self):
        for declaration in self:
            declaration.prepayment_allocation_ids.unlink()
            values = []
            for line in declaration.line_ids.filtered(lambda item: item.calculation_mode == 'prepayment'):
                domain = [
                    ('company_id', '=', declaration.company_id.id), ('state', '=', 'approved'),
                    ('date', '>=', declaration.date_from), ('date', '<=', declaration.date_to),
                ]
                if line.tax_rule_id:
                    domain.append(('rule_id', '=', line.tax_rule_id.id))
                for prepayment in self.env['primetech.tax.prepayment'].search(domain):
                    used = sum(prepayment.allocation_ids.mapped('amount')) + sum(prepayment.dgi_tva_ir_allocation_ids.filtered(
                        lambda allocation: allocation.declaration_id != declaration
                    ).mapped('amount'))
                    available = max(prepayment.amount_initial - used, 0.0)
                    if available:
                        values.append({
                            'declaration_id': declaration.id,
                            'line_id': line.id,
                            'prepayment_id': prepayment.id,
                            'amount': available,
                        })
            if values:
                self.env['primetech.dgi.tva.ir.prepayment.allocation'].create(values)

    ''' 

    def action_validate(self):
        if not self.env.user.has_group('primetech_tax_automation.group_tax_manager'):
            raise AccessError(_('La validation est réservée au responsable fiscal.'))
        for declaration in self:
            if declaration.state not in ('calculated', 'review'):
                raise UserError(_('Calculez la déclaration avant de la valider.'))
            declaration.write({
                'state': 'validated',
                'approved_by_id': self.env.user.id,
                'snapshot': {
                    'period': [str(declaration.date_from), str(declaration.date_to)],
                    'form_version': declaration.form_version,
                    'lines': [{
                        'code': line.line_code, 'base': line.base_amount, 'rate': line.rate,
                        'principal': line.principal_amount, 'cac': line.cac_amount,
                        'penalty': line.penalty_amount, 'total': line.total_amount,
                    } for line in declaration.line_ids],
                },
            })
        return True

    def action_file(self):
        for declaration in self:
            if declaration.state != 'validated':
                raise UserError(_('Validez la déclaration avant de la marquer comme déclarée.'))
            declaration.state = 'filed'
        return True

    def action_cancel(self):
        if not self.env.user.has_group('primetech_tax_automation.group_tax_manager'):
            raise AccessError(_('L’annulation est réservée au responsable fiscal.'))
        for declaration in self:
            declaration.state = 'cancelled'
        return True

    def action_reset_to_draft(self):
        """Reopen a calculated or cancelled declaration for a new calculation."""
        for declaration in self:
            if declaration.state not in ('calculated', 'cancelled'):
                raise UserError(_('Seules les déclarations calculées ou annulées peuvent être remises en brouillon.'))
            declaration.write({
                'state': 'draft',
                'approved_by_id': False,
                'snapshot': False,
                'filing_reference': False,
                'filing_evidence': False,
            })
            declaration.message_post(body=_('La déclaration a été remise en brouillon.'))
        return True

    def dgi_lines_for_section(self, section_code):
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.section_code == section_code).sorted('sequence')

    def dgi_sections(self):
        """Return configured sections in their display order for the report."""
        self.ensure_one()
        return self.env['primetech.dgi.tva.ir.section'].search([], order='sequence, code, id')

    def dgi_section_title(self, section_code):
        self.ensure_one()
        section = self.env['primetech.dgi.tva.ir.section'].search([('code', '=', section_code)], limit=1)
        return section.display_name if section else SECTION_TITLES.get(section_code, section_code)


class DgiTvaIrLine(models.Model):
    _name = 'primetech.dgi.tva.ir.line'
    _description = 'Ligne de déclaration DGI TVA/IR'
    _order = 'sequence, id'

    declaration_id = fields.Many2one('primetech.dgi.tva.ir.declaration', string='Déclaration DGI', required=True, ondelete='cascade')
    mapping_id = fields.Many2one('primetech.dgi.tva.ir.mapping', string='Correspondance fiscale', readonly=True)
    line_definition_id = fields.Many2one(
        'primetech.dgi.tva.ir.line.definition', string='Définition de ligne',
        readonly=True, ondelete='restrict',
    )
    line_code = fields.Selection(
        selection='_selection_line_code', string='Ligne', required=True, readonly=True,
    )
    section_code = fields.Selection(selection='_selection_section_code', string='Rubrique', required=True, readonly=True)
    sequence = fields.Integer(required=True, readonly=True)
    name = fields.Char(string='Libellé', required=True, readonly=True)
    calculation_mode = fields.Selection([
        ('accounts', 'Comptes comptables'), ('fixed', 'Montant fixe'), ('manual', 'Saisie manuelle'), ('formula', 'Formule DGI'),
    ], string='Mode de calcul', required=True, readonly=True)
    formula_code = fields.Char(readonly=True)
    source_account_ids = fields.Many2many(
        'account.account', 'primetech_dgi_tva_ir_line_account_rel', 'line_id', 'account_id',
        string='Comptes sources', readonly=True, check_company=True,
    )
    account_aggregation = fields.Selection([
        ('credit_debit', 'Crédit - débit'), ('debit_credit', 'Débit - crédit'),
        ('credit', 'Crédit'), ('debit', 'Débit'), ('movement', 'Débit + crédit'),
    ], string='Sens du montant', readonly=True, default='credit_debit')
    amount_mode = fields.Selection([
        ('base_times_rate', 'Base × taux'), ('source_amount', 'Montant source'), ('fixed_amount', 'Montant fixe'),
    ], string='Origine du principal', required=True, readonly=True)
    fixed_amount = fields.Monetary(string='Montant fixe', readonly=True, currency_field='currency_id')
    absolute_source = fields.Boolean(readonly=True)
    rate = fields.Float(string='Taux (%)', digits=(16, 4))
    cac_rate = fields.Float(string='CAC (%)', digits=(16, 4))
    payment_date = fields.Date(string='Date de paiement')
    base_amount = fields.Monetary(string='Base', currency_field='currency_id')
    principal_amount = fields.Monetary(string='Principal', currency_field='currency_id')
    cac_amount = fields.Monetary(string='CAC', currency_field='currency_id')
    penalty_amount = fields.Monetary(string='Pénalités', currency_field='currency_id')
    total_amount = fields.Monetary(string='Total', compute='_compute_total_amount', store=True, currency_field='currency_id')
    source_model = fields.Char(string='Modèle source', readonly=True)
    source_domain = fields.Json(string='Filtre source', readonly=True)
    source_count = fields.Integer(string='Éléments sources', readonly=True)
    currency_id = fields.Many2one(related='declaration_id.currency_id', string='Devise')
    is_total = fields.Boolean(compute='_compute_is_total')
    is_balance = fields.Boolean(compute='_compute_is_total')

    _sql_constraints = [
        ('dgi_tva_ir_line_declaration_code_unique', 'unique(declaration_id, line_code)',
         'Une ligne DGI ne peut apparaître qu’une fois dans une déclaration.'),
        ('dgi_tva_ir_line_rates_non_negative', 'check(rate >= 0 and cac_rate >= 0)',
         'Les taux ne peuvent pas être négatifs.'),
    ]

    @api.model
    def _selection_line_code(self):
        definitions = self.env['primetech.dgi.tva.ir.line.definition'].search([])
        values = [(definition.code, definition.display_name) for definition in definitions]
        # L76 remains available for declarations produced before the
        # configurable catalogue was introduced.  It is a printed total,
        # not a line that can be configured in mappings.
        if not any(code == 'L76' for code, _label in values):
            values.append(('L76', LINE_BY_CODE['L76']['label']))
        return values

    @api.model
    def _selection_section_code(self):
        sections = self.env['primetech.dgi.tva.ir.section'].search([])
        return [(section.code, section.display_name) for section in sections]

    @api.depends('principal_amount', 'cac_amount', 'penalty_amount')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.principal_amount + line.cac_amount + line.penalty_amount

    @api.depends('formula_code')
    def _compute_is_total(self):
        for line in self:
            line.is_total = line.formula_code in ('sum_45_48', 'sum_56_61', 'sum_63_64', 'sum_66_68', 'sum_70_75', 'section_total')
            line.is_balance = line.formula_code in ('payable_balance', 'credit_balance')

    @api.constrains('base_amount', 'principal_amount', 'cac_amount', 'penalty_amount')
    def _check_non_negative_amounts(self):
        for line in self:
            if any(value < 0 for value in (line.base_amount, line.principal_amount, line.cac_amount, line.penalty_amount)):
                raise ValidationError(_('Les montants de la déclaration DGI ne peuvent pas être négatifs.'))

    def action_sources(self):
        self.ensure_one()
        if not self.source_model or self.source_model not in self.env.registry.models:
            raise UserError(_('Cette ligne ne possède pas encore de source calculée.'))
        return {
            'type': 'ir.actions.act_window', 'name': _('Éléments sources %s') % self.line_code,
            'res_model': self.source_model, 'view_mode': 'list,form', 'domain': self.source_domain or [],
        }


"""Moteur historique de précomptes désactivé : ses modèles ne sont plus chargés.

class DgiTvaIrPrepaymentAllocation(models.Model):
    _name = 'primetech.dgi.tva.ir.prepayment.allocation'
    _description = 'Imputation de précompte dans une déclaration DGI TVA/IR'
    _order = 'id'

    declaration_id = fields.Many2one('primetech.dgi.tva.ir.declaration', string='Déclaration DGI', required=True, ondelete='cascade')
    line_id = fields.Many2one('primetech.dgi.tva.ir.line', string='Ligne DGI', required=True, ondelete='cascade')
    prepayment_id = fields.Many2one('primetech.tax.prepayment', string='Précompte fiscal', required=True, ondelete='restrict')
    amount = fields.Monetary(string='Montant imputé', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='prepayment_id.currency_id', string='Devise')

    _sql_constraints = [
        ('dgi_tva_ir_prepayment_once', 'unique(declaration_id, prepayment_id)',
         'Un précompte ne peut être imputé qu’une fois dans la même déclaration DGI.'),
        ('dgi_tva_ir_prepayment_amount_positive', 'check(amount > 0)',
         'Le montant imputé doit être strictement positif.'),
    ]

    @api.constrains('amount', 'prepayment_id')
    def _check_available(self):
        for allocation in self:
            generic_used = sum(allocation.prepayment_id.allocation_ids.mapped('amount'))
            dgi_used = sum(allocation.prepayment_id.dgi_tva_ir_allocation_ids.filtered(
                lambda item: item != allocation
            ).mapped('amount'))
            if allocation.prepayment_id.state != 'approved' or allocation.amount > allocation.prepayment_id.amount_initial - generic_used - dgi_used:
                raise ValidationError(_('Le précompte disponible est insuffisant.'))


class TaxPrepaymentDgiExtension(models.Model):
    _inherit = 'primetech.tax.prepayment'

    dgi_tva_ir_allocation_ids = fields.One2many(
        'primetech.dgi.tva.ir.prepayment.allocation', 'prepayment_id', string='Imputations DGI TVA/IR',
    )

    @api.depends('allocation_ids.amount', 'dgi_tva_ir_allocation_ids.amount')
    def _compute_amounts(self):
        for record in self:
            record.amount_used = sum(record.allocation_ids.mapped('amount')) + sum(record.dgi_tva_ir_allocation_ids.mapped('amount'))
            record.amount_available = record.amount_initial - record.amount_used


class TaxPrepaymentAllocationDgiExtension(models.Model):
    _inherit = 'primetech.tax.prepayment.allocation'

    @api.constrains('amount', 'prepayment_id')
    def _check_available(self):
        for record in self:
            generic_used = sum(record.prepayment_id.allocation_ids.filtered(lambda item: item != record).mapped('amount'))
            dgi_used = sum(record.prepayment_id.dgi_tva_ir_allocation_ids.mapped('amount'))
            if record.prepayment_id.state != 'approved' or record.amount <= 0 or record.amount > record.prepayment_id.amount_initial - generic_used - dgi_used:
                raise ValidationError(_('Précompte disponible insuffisant.'))
"""
