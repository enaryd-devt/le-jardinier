from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    alert_quantity = fields.Float(string="Alert Quantity")

    show_alert_quantity = fields.Boolean(string="Show Alert Quantity", compute='_compute_show_alert_quantity')

    def _compute_show_alert_quantity(self):
        method = self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.method', 'global')
        for rec in self:
            rec.show_alert_quantity = (method == 'category')
# =====================================================================
 

    def write(self, vals):
        result = super(ProductCategory, self).write(vals)

        method = self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.method', 'global')
        
        if method == 'category' and 'alert_quantity' in vals:
           
            for category in self:
                products = self.env['product.product'].search([('categ_id', '=', category.id)])
                for product in products:
                    alert_qty = product._get_alert_quantity(product)
                    if alert_qty and product.qty_available <= alert_qty:
                        message = f"Low stock alert for {product.display_name}: Only {product.qty_available} units left (Threshold: {alert_qty})"
                        product._notify_low_stock(product, message)
        
        return result

                




 
