from odoo import api, models


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def primetech_reload_products(self, session_id):
        """Reload the POS catalogue without reloading the complete POS interface."""
        session = self.browse(session_id).exists()
        if not session:
            return {"product.product": []}
        config = session.config_id
        Product = self.env["product.product"]
        products = Product._load_product_with_domain(config._get_available_product_domain(), config.id)
        Product._process_pos_ui_product_product(products, config)
        return {
            "product.product": {
                "data": products,
                "fields": Product._load_pos_data_fields(config.id),
            }
        }
