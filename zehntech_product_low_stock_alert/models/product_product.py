 
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    alert_quantity = fields.Float(string='Alert Quantity')

    show_alert_quantity = fields.Boolean(
        compute='_compute_show_alert_quantity',
        string="Show Alert Quantity Field"
    )

    def _compute_show_alert_quantity(self):
        method = self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.method', 'global')
        for rec in self:
            rec.show_alert_quantity = (method == 'individual')
      
    @api.model
    def _get_alert_quantity(self, product):
        method = self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.method', 'global')
        if method == 'global':
            global_qty = float(self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.global_minimum_qty', 0))
            product.alert_quantity = global_qty
            return float(self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.global_minimum_qty', 0))
        
        elif method == 'individual': 
            return product.alert_quantity 
        
        elif method == 'category':

            product.alert_quantity = product.categ_id.alert_quantity
            return product.categ_id.alert_quantity or 0
        return 0
    
    # ====================================================================
    
    # Add this inside ProductProduct class

    @api.model
    def create(self, vals):
        product = super(ProductProduct, self).create(vals)

        method = self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.method', 'global')
        alert_qty = product._get_alert_quantity(product)

        if method in ['global', 'category']:
            product.alert_quantity = alert_qty  

       
        if alert_qty and product.qty_available <= alert_qty:
            message = f"Low stock alert for {product.display_name}: Only {product.qty_available} units left (Threshold: {alert_qty})"
            product._notify_low_stock(product, message)

        return product
    
    
    
    def write(self, vals):
        result = super(ProductProduct, self).write(vals)

        method = self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.method', 'global')
        
        if method == 'individual' and 'alert_quantity' in vals:
           
            for product in self:
                alert_qty = product._get_alert_quantity(product)
                if alert_qty and product.qty_available <= alert_qty:
                    message = f"Low stock alert for {product.display_name}: Only {product.qty_available} units left (Threshold: {alert_qty})"
                    product._notify_low_stock(product, message)
                    
        
        return result


    def _notify_low_stock(self, product, message):
        user_ids_str = self.env['ir.config_parameter'].sudo().get_param('zehntech_product_low_stock_alert.notify_user_ids', '')
        user_ids = [int(uid) for uid in user_ids_str.split(',') if uid]
        users = self.env['res.users'].browse(user_ids)
        for user in users:
            self.env['mail.message'].create({
                'model': 'product.product',
                'res_id': product.id,
                'author_id': self.env.user.partner_id.id,
                'partner_ids': [(4, user.partner_id.id)],
                'message_type': 'notification',
                'subtype_id': self.env.ref('mail.mt_note').id,
                'body': message,
            })


 
     