from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        store=True,
        readonly=False,
    )

    # =====================================================
    # 🔥 MÉTHODE CENTRALE OPTIMISÉE
    # =====================================================
    def _get_best_warehouse(self):
        self.ensure_one()

        if not self.product_id or not self.order_id.company_id:
            return False

        company = self.order_id.company_id

        # 🔹 Lecture groupée optimisée (1 seule requête SQL)
        grouped_quants = self.env["stock.quant"].read_group(
            domain=[
                ("product_id", "=", self.product_id.id),
                ("location_id.usage", "=", "internal"),
                ("company_id", "=", company.id),
            ],
            fields=["quantity:sum", "reserved_quantity:sum", "location_id"],
            groupby=["location_id"],
        )

        if not grouped_quants:
            return False

        # 🔹 Stock dispo par location
        location_available = {
            g["location_id"][0]: g["quantity"] - g["reserved_quantity"]
            for g in grouped_quants
            if (g["quantity"] - g["reserved_quantity"]) > 0
        }

        if not location_available:
            return False

        # 🔹 Mapping location → warehouse (optimisé)
        warehouses = self.env["stock.warehouse"].search([
            ("company_id", "=", company.id)
        ])

        location_obj = self.env["stock.location"]

        best_wh = False
        best_qty = 0

        for wh in warehouses:
            child_locations = location_obj.search([
                ("id", "child_of", wh.lot_stock_id.id)
            ]).ids

            total = sum(
                qty for loc_id, qty in location_available.items()
                if loc_id in child_locations
            )

            if total > best_qty:
                best_qty = total
                best_wh = wh

        return best_wh

    # =====================================================
    # 🔥 ONCHANGE (UI)
    # =====================================================
    @api.onchange("product_id")
    def _onchange_product_set_best_warehouse(self):
        for line in self:
            best = line._get_best_warehouse()
            if best:
                line.warehouse_id = best

    # =====================================================
    # 🔥 CREATE (catalogue inclus)
    # =====================================================
    @api.model
    def create(self, vals):
        line = super().create(vals)

        if line.product_id and not vals.get("warehouse_id"):
            best = line._get_best_warehouse()
            if best:
                line.warehouse_id = best.id

        return line

    # =====================================================
    # 🔥 WRITE (évite reset après modif quantité)
    # =====================================================
    def write(self, vals):
        res = super().write(vals)

        if "product_id" in vals or "product_uom_qty" in vals:
            for line in self:
                if not line.warehouse_id:
                    best = line._get_best_warehouse()
                    if best:
                        line.warehouse_id = best.id

        return res

    # =====================================================
    # 🔥 Neutralise recalcul auto Odoo
    # =====================================================
    @api.depends_context("company")
    def _compute_warehouse_id(self):
        for line in self:
            if not line.warehouse_id:
                line.warehouse_id = line.order_id.warehouse_id

    # =====================================================
    # 🔥 Sécurisation livraison
    # =====================================================
    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id)

        if self.warehouse_id:
            values["warehouse_id"] = self.warehouse_id
            values["location_id"] = self.warehouse_id.lot_stock_id.id

        return values
