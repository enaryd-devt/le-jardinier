"""DSF cell-to-account mappings for the official DGI workbook."""

from openpyxl import load_workbook

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource


# Les préfixes couvrent les sous-comptes : « 411 » inclut par exemple 411100,
# 411200, etc. Les colonnes N du modèle officiel sont alimentées; les colonnes
# N-1 restent comparatives et ne doivent pas être écrasées par l'exercice en cours.
OHADA_DSF_DEFAULTS = [
    # Bilan - actif immobilisé
    ("BILAN PAYSAGE", "F13", "Frais de développement et prospection", "211,2811,2911", 1),
    ("BILAN PAYSAGE", "F14", "Brevets, licences, logiciels et droits similaires", "212,213,214,2812,2813,2814,2912,2913,2914", 1),
    ("BILAN PAYSAGE", "F15", "Fonds commercial et droit au bail", "215,2815,2915", 1),
    ("BILAN PAYSAGE", "F16", "Autres immobilisations incorporelles", "218,2818,2918", 1),
    ("BILAN PAYSAGE", "F18", "Terrains", "22,282,292", 1),
    ("BILAN PAYSAGE", "F19", "Bâtiments", "23,283,293", 1),
    ("BILAN PAYSAGE", "F20", "Aménagements et installations", "24,284,294", 1),
    ("BILAN PAYSAGE", "F21", "Matériel, mobilier et actifs biologiques", "241,242,243,246,247,2841,2842,2843,2846,2847,2941,2942,2943,2946,2947", 1),
    ("BILAN PAYSAGE", "F22", "Matériel de transport", "245,2845,2945", 1),
    ("BILAN PAYSAGE", "F23", "Avances et acomptes versés sur immobilisations", "25", 1),
    ("BILAN PAYSAGE", "F25", "Titres de participation", "26,296", 1),
    ("BILAN PAYSAGE", "F26", "Autres immobilisations financières", "27,297", 1),
    ("BILAN PAYSAGE", "F28", "Actif circulant HAO", "485", 1),
    ("BILAN PAYSAGE", "F29", "Stocks et encours", "3,39", 1),
    ("BILAN PAYSAGE", "F31", "Fournisseurs avances versées", "409", 1),
    ("BILAN PAYSAGE", "F32", "Clients", "411,412", 1),
    ("BILAN PAYSAGE", "F33", "Autres créances", "42,43,44,45,46,47,488", 1),
    ("BILAN PAYSAGE", "F35", "Titres de placement", "50,590", 1),
    ("BILAN PAYSAGE", "F36", "Valeurs à encaisser", "51", 1),
    ("BILAN PAYSAGE", "F37", "Banques, chèques postaux, caisse", "52,53,54,57,58", 1),
    ("BILAN PAYSAGE", "F39", "Écart de conversion actif", "478", 1),
    # Bilan - passif (solde créditeur affiché positivement)
    ("BILAN PAYSAGE", "K12", "Capital", "101,102,103,104", -1),
    ("BILAN PAYSAGE", "K13", "Capital souscrit non appelé", "109", -1),
    ("BILAN PAYSAGE", "K14", "Primes liées au capital", "105", -1),
    ("BILAN PAYSAGE", "K15", "Écarts de réévaluation", "106", -1),
    ("BILAN PAYSAGE", "K16", "Réserves indisponibles", "111,112,113", -1),
    ("BILAN PAYSAGE", "K17", "Réserves libres", "118", -1),
    ("BILAN PAYSAGE", "K18", "Report à nouveau", "12", -1),
    ("BILAN PAYSAGE", "K19", "Résultat net de l'exercice", "13", -1),
    ("BILAN PAYSAGE", "K20", "Subventions d'investissement", "14", -1),
    ("BILAN PAYSAGE", "K21", "Provisions réglementées", "15", -1),
    ("BILAN PAYSAGE", "K23", "Emprunts et dettes financières diverses", "16", -1),
    ("BILAN PAYSAGE", "K24", "Dettes de location acquisition", "17", -1),
    ("BILAN PAYSAGE", "K25", "Provisions pour risques et charges", "19", -1),
    ("BILAN PAYSAGE", "K28", "Dettes circulantes HAO", "481", -1),
    ("BILAN PAYSAGE", "K29", "Clients, avances reçues", "419", -1),
    ("BILAN PAYSAGE", "K30", "Fournisseurs d'exploitation", "401,402,403", -1),
    ("BILAN PAYSAGE", "K31", "Dettes fiscales et sociales", "42,43,44,45", -1),
    ("BILAN PAYSAGE", "K32", "Autres dettes", "404,405,406,407,408,46,47,488", -1),
    ("BILAN PAYSAGE", "K33", "Provisions pour risques à court terme", "499", -1),
    ("BILAN PAYSAGE", "K36", "Banques, crédits d'escompte", "519", -1),
    ("BILAN PAYSAGE", "K37", "Banques et crédits de trésorerie", "56", -1),
    ("BILAN PAYSAGE", "K39", "Écart de conversion passif", "479", -1),
    # Compte de résultat - produits (créditeurs) et charges (débiteurs)
    ("COMPTE DE RESULTAT", "E11", "Ventes de marchandises", "701", -1),
    ("COMPTE DE RESULTAT", "E12", "Achats de marchandises", "601", 1),
    ("COMPTE DE RESULTAT", "E13", "Variation de stock de marchandises", "6031", 1),
    ("COMPTE DE RESULTAT", "E15", "Ventes de produits fabriqués", "702", -1),
    ("COMPTE DE RESULTAT", "E16", "Travaux et services vendus", "703", -1),
    ("COMPTE DE RESULTAT", "E17", "Produits accessoires", "704", -1),
    ("COMPTE DE RESULTAT", "E19", "Production stockée ou déstockage", "73", -1),
    ("COMPTE DE RESULTAT", "E20", "Production immobilisée", "72", -1),
    ("COMPTE DE RESULTAT", "E21", "Subventions d'exploitation", "71", -1),
    ("COMPTE DE RESULTAT", "E22", "Autres produits", "75", -1),
    ("COMPTE DE RESULTAT", "E23", "Transferts de charges d'exploitation", "78", -1),
    ("COMPTE DE RESULTAT", "E24", "Achats de matières et fournitures", "602", 1),
    ("COMPTE DE RESULTAT", "E25", "Variation de stocks de matières", "6032", 1),
    ("COMPTE DE RESULTAT", "E26", "Autres achats", "604,605,608", 1),
    ("COMPTE DE RESULTAT", "E27", "Variation de stocks autres approvisionnements", "6033", 1),
    ("COMPTE DE RESULTAT", "E28", "Transports", "61", 1),
    ("COMPTE DE RESULTAT", "E29", "Services extérieurs", "62", 1),
    ("COMPTE DE RESULTAT", "E30", "Impôts et taxes", "63", 1),
    ("COMPTE DE RESULTAT", "E31", "Autres charges", "64,65", 1),
    ("COMPTE DE RESULTAT", "E33", "Charges de personnel", "66", 1),
    ("COMPTE DE RESULTAT", "E35", "Reprises d'amortissements et provisions", "79", -1),
    ("COMPTE DE RESULTAT", "E36", "Dotations aux amortissements et provisions", "68,69", 1),
    ("COMPTE DE RESULTAT", "E38", "Revenus financiers", "77", -1),
    ("COMPTE DE RESULTAT", "E39", "Reprises financières", "798", -1),
    ("COMPTE DE RESULTAT", "E40", "Transferts de charges financières", "78", -1),
    ("COMPTE DE RESULTAT", "E41", "Frais financiers", "67", 1),
    ("COMPTE DE RESULTAT", "E42", "Dotations financières", "697", 1),
    ("COMPTE DE RESULTAT", "E45", "Produits de cession d'immobilisations", "82", -1),
    ("COMPTE DE RESULTAT", "E46", "Autres produits HAO", "84", -1),
    ("COMPTE DE RESULTAT", "E47", "Valeurs comptables des cessions", "81", 1),
    ("COMPTE DE RESULTAT", "E48", "Autres charges HAO", "83", 1),
    ("COMPTE DE RESULTAT", "E50", "Participation des travailleurs", "87", 1),
    ("COMPTE DE RESULTAT", "E51", "Impôt sur le résultat", "89", 1),
]


class PrimetechDsfMapping(models.Model):
    _name = "primetech.dsf.mapping"
    _description = "Correspondance DSF"
    _order = "sheet_name, cell_address, id"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    sheet_name = fields.Selection(selection="_selection_sheet_name", string="Feuille DSF", required=True)
    template_cell_id = fields.Many2one(
        "primetech.dsf.template.cell",
        string="Cellule Excel",
        domain="[('sheet_name', '=', sheet_name)]",
        ondelete="restrict",
    )
    cell_address = fields.Char(string="Cellule Excel", required=True, help="Ex. E11 ou K22")
    account_ids = fields.Many2many("account.account", string="Comptes sources complémentaires")
    account_prefixes = fields.Char(
        string="Préfixes SYSCOHADA",
        help="Préfixes séparés par des virgules. Ex. 411, 412 inclut tous leurs sous-comptes.",
    )
    amount_type = fields.Selection([
        ("balance", "Solde (Débit - Crédit)"),
        ("debit", "Mouvements débiteurs"),
        ("credit", "Mouvements créditeurs"),
    ], string="Montant", required=True, default="balance")
    multiplier = fields.Float(string="Coefficient", default=1.0)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("dsf_mapping_unique_cell", "unique(company_id, sheet_name, cell_address)",
         "Une seule correspondance est autorisée par cellule DSF et par société."),
    ]

    @api.model
    def _selection_sheet_name(self):
        template_path = get_module_resource("primetech_tax_automation", "data", "dsf_normal_dgiformat.xlsx")
        workbook = load_workbook(template_path, read_only=True)
        return [(sheet_name, sheet_name) for sheet_name in workbook.sheetnames]

    @api.onchange("sheet_name")
    def _onchange_sheet_name(self):
        for record in self:
            record.template_cell_id = False
            record.cell_address = False
            if record.sheet_name:
                self.env["primetech.dsf.template.cell"].sudo().ensure_sheet_cells(record.sheet_name)

    @api.onchange("template_cell_id")
    def _onchange_template_cell_id(self):
        for record in self:
            record.cell_address = record.template_cell_id.cell_address or False

    def _amount_for_period(self, date_from, date_to):
        self.ensure_one()
        account_ids = self.account_ids | self._accounts_from_prefixes()
        if not account_ids:
            return 0.0
        domain = [
            ("company_id", "=", self.company_id.id),
            ("account_id", "in", account_ids.ids),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("move_id.state", "=", "posted"),
        ]
        grouped = self.env["account.move.line"].read_group(
            domain, ["debit:sum", "credit:sum"], []
        )
        debit = grouped[0].get("debit", 0.0) if grouped else 0.0
        credit = grouped[0].get("credit", 0.0) if grouped else 0.0
        amount = {
            "balance": debit - credit,
            "debit": debit,
            "credit": credit,
        }[self.amount_type]
        return amount * self.multiplier

    def _accounts_from_prefixes(self):
        self.ensure_one()
        prefixes = [prefix.strip() for prefix in (self.account_prefixes or "").split(",") if prefix.strip()]
        if not prefixes:
            return self.env["account.account"]
        domain = [("company_ids", "in", self.company_id.id)]
        domain += ["|"] * (len(prefixes) - 1)
        domain += [("code", "=like", "%s%%" % prefix) for prefix in prefixes]
        return self.env["account.account"].search(domain)

    @api.model
    def ensure_ohada_defaults(self, company):
        """Create once the standard DSF mapping; local overrides are preserved."""
        for sheet_name, cell_address, name, prefixes, multiplier in OHADA_DSF_DEFAULTS:
            if not self.search_count([
                ("company_id", "=", company.id), ("sheet_name", "=", sheet_name), ("cell_address", "=", cell_address),
            ]):
                self.create({
                    "name": name,
                    "company_id": company.id,
                    "sheet_name": sheet_name,
                    "cell_address": cell_address,
                    "account_prefixes": prefixes,
                    "multiplier": multiplier,
                })

    @api.constrains("cell_address")
    def _check_cell_address(self):
        for record in self:
            cell = (record.cell_address or "").replace("$", "").upper()
            # Letter(s) followed by a row number, e.g. E11 or AA102.
            column = cell.rstrip("0123456789")
            if not cell or not column.isalpha() or not cell[-1:].isdigit():
                raise ValidationError(_("La cellule Excel doit respecter le format E11 ou AA102."))

    @api.constrains("account_ids", "account_prefixes")
    def _check_account_source(self):
        for record in self:
            if not record.account_ids and not record.account_prefixes:
                raise ValidationError(_("Sélectionnez des comptes ou renseignez au moins un préfixe SYSCOHADA."))
