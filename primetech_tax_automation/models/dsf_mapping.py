"""DSF cell-to-account mappings for the official DGI workbook."""

from openpyxl import load_workbook

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource


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
    account_ids = fields.Many2many("account.account", string="Comptes sources", required=True)
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
        domain = [
            ("company_id", "=", self.company_id.id),
            ("account_id", "in", self.account_ids.ids),
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

    @api.constrains("cell_address")
    def _check_cell_address(self):
        for record in self:
            cell = (record.cell_address or "").replace("$", "").upper()
            # Letter(s) followed by a row number, e.g. E11 or AA102.
            column = cell.rstrip("0123456789")
            if not cell or not column.isalpha() or not cell[-1:].isdigit():
                raise ValidationError(_("La cellule Excel doit respecter le format E11 ou AA102."))
