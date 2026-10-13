"""Selectable cells of the official DGI DSF workbook."""

from odoo import api, fields, models

from .dsf_mapping import DSF_DEFAULT_MAPPINGS


class PrimetechDsfTemplateCell(models.Model):
    _name = "primetech.dsf.template.cell"
    _description = "Cellule disponible du modèle DSF"
    _order = "sheet_name, cell_address"

    name = fields.Char(required=True, readonly=True)
    sheet_name = fields.Char(required=True, readonly=True, index=True)
    cell_address = fields.Char(required=True, readonly=True, index=True)
    active = fields.Boolean(default=True, readonly=True)

    _sql_constraints = [
        ("dsf_template_cell_unique", "unique(sheet_name, cell_address)", "Cette cellule DSF existe déjà."),
    ]

    @api.model
    def ensure_sheet_cells(self, sheet_name):
        """Index only the DSF cells populated by the accounting extraction."""
        if not sheet_name:
            return self.browse()
        expected = {
            cell_address: name
            for target_sheet, cell_address, name, _prefixes, _multiplier, _amount_type, _calculation_scope in DSF_DEFAULT_MAPPINGS
            if target_sheet == sheet_name
        }
        existing = self.search([("sheet_name", "=", sheet_name)])
        existing.filtered(lambda cell: cell.cell_address not in expected).write({"active": False})
        indexed = {cell.cell_address: cell for cell in existing if cell.cell_address in expected}
        for cell_address, name in expected.items():
            values = {"name": "%s - %s" % (cell_address, name), "active": True}
            cell = indexed.get(cell_address)
            if cell:
                cell.write(values)
            else:
                self.create({**values, "sheet_name": sheet_name, "cell_address": cell_address})
        return self.search([("sheet_name", "=", sheet_name), ("active", "=", True)])
