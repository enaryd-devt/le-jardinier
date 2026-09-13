from odoo import models, api

class ProductProduct(models.Model):
    _inherit = "product.product"

    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)

        extra_fields = [
            "qty_available",
            "virtual_available",
            "type",
            "standard_price",
            "lst_price",
            "tracking",
        ]

        for f in extra_fields:
            if f not in fields:
                fields.append(f)

        return fields