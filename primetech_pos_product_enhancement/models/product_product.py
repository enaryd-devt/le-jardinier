from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Champ déclaré pour que le modèle relationnel du POS puisse le charger.
    # Sa valeur est remplacée, à chaque chargement POS, par celle de la
    # localisation source du point de vente.
    primetech_pos_qty = fields.Float(string="Quantité POS", readonly=True)

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        for name in ("standard_price", "qty_available", "virtual_available", "primetech_pos_qty"):
            if name not in fields:
                fields.append(name)
        return fields

    def _process_pos_ui_product_product(self, products, config):
        super()._process_pos_ui_product_product(products, config)
        # Sum every internal sub-location of the warehouse associated with the
        # POS operation type. Their complete name includes the warehouse short
        # name (for example WH/Stock/Shelf A), so all its locations are taken
        # into account rather than only the main Stock location.
        warehouse = config.picking_type_id.warehouse_id
        source_location = warehouse.view_location_id or config.picking_type_id.default_location_src_id
        ids = [product["id"] for product in products]
        quantities = dict.fromkeys(ids, 0.0)
        if source_location and ids:
            groups = self.env["stock.quant"].read_group(
                [
                    ("product_id", "in", ids),
                    ("location_id", "child_of", source_location.id),
                    ("location_id.usage", "=", "internal"),
                ],
                ["product_id", "quantity:sum", "reserved_quantity:sum"], ["product_id"], lazy=False,
            )
            for group in groups:
                product_id = group.get("product_id") and group["product_id"][0]
                if product_id:
                    quantities[product_id] = (group.get("quantity", 0.0) or 0.0) - (group.get("reserved_quantity", 0.0) or 0.0)
        for product in products:
            product["primetech_pos_qty"] = quantities.get(product["id"], 0.0)

    def get_product_info_pos(self, price, quantity, pos_config_id):
        """Expose stock only for companies the current user may access."""
        self.ensure_one()
        result = super().get_product_info_pos(price, quantity, pos_config_id)
        company_stock = []
        Warehouse = self.env["stock.warehouse"]
        pos_company = self.env["pos.config"].browse(pos_config_id).company_id
        # Do not filter on the company's active flag: access is determined by
        # the companies assigned to the current user.
        companies = self.env.user.company_ids.sorted(
            key=lambda company: company.id != pos_company.id
        )
        for company in companies:
            product_in_company = self.with_context(
                allowed_company_ids=[company.id],
                force_company=company.id,
            )
            show_warehouses = company == pos_company
            warehouse_stock = []
            if show_warehouses:
                warehouses = Warehouse.search([("company_id", "=", company.id)])
                warehouse_stock = [
                    {
                        "id": warehouse.id,
                        "name": warehouse.name,
                        "code": warehouse.code,
                        "available_quantity": product_in_company.with_context(
                            warehouse_id=warehouse.id
                        ).qty_available,
                        "forecasted_quantity": product_in_company.with_context(
                            warehouse_id=warehouse.id
                        ).virtual_available,
                        "uom": self.uom_name,
                    }
                    for warehouse in warehouses
                ]
            company_stock.append({
                "id": company.id,
                "name": company.name,
                "show_warehouses": show_warehouses,
                "available_quantity": product_in_company.qty_available,
                "uom": self.uom_name,
                "warehouses": warehouse_stock,
            })
        result["primetech_company_stock"] = company_stock
        return result
