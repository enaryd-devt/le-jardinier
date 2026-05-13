from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    low_stock_alert_method = fields.Selection([
        ('global', 'Global'),
        ('individual', 'Individual Product'),
        ('category', 'Product Category')
    ], string="Low Stock Alert Method", config_parameter='zehntech_product_low_stock_alert.method', default='global')
   

    global_minimum_qty = fields.Float(string="Global Minimum Quantity")
    notify_user_ids = fields.Many2many('res.users', string="Notify Users")

 

    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        user_ids_str = params.get_param('zehntech_product_low_stock_alert.notify_user_ids', '')
        user_ids = [int(uid) for uid in user_ids_str.split(',') if uid]
        res.update({
            'low_stock_alert_method': params.get_param('zehntech_product_low_stock_alert.method'),
            'global_minimum_qty': float(params.get_param('zehntech_product_low_stock_alert.global_minimum_qty', 0)),
            'notify_user_ids': [(6, 0, user_ids)]
        })
        return res
# ====================================================================


    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()

        params.set_param('zehntech_product_low_stock_alert.method', self.low_stock_alert_method)
        user_ids_str = ','.join(map(str, self.notify_user_ids.ids))
        params.set_param('zehntech_product_low_stock_alert.notify_user_ids', user_ids_str)

        products = self.env['product.product'].search([])
        categories = self.env['product.category'].search([])  # 🔥 NEW LINE


        if self.low_stock_alert_method in ['individual', 'category']:
            self.global_minimum_qty = 0
            params.set_param('zehntech_product_low_stock_alert.global_minimum_qty', 0)

            # Set alert_quantity = 0 for all products
            for product in products:
                product.write({'alert_quantity': 0})
            
            for cat in categories:
                cat.write({'alert_quantity': 0})

        else:
            # Save the global minimum and update all product.alert_quantity
            params.set_param('zehntech_product_low_stock_alert.global_minimum_qty', self.global_minimum_qty)

          
            global_qty = self.global_minimum_qty

            for product in products:
                product.write({'alert_quantity': global_qty})

                if global_qty and product.qty_available <= global_qty:
                    message = f"Low stock alert for {product.display_name}: Only {product.qty_available} units left (Threshold: {global_qty})"
                    product._notify_low_stock(product, message)
                    
            for cat in categories:
                cat.write({'alert_quantity': global_qty})

        return res
    
    
    
    
    
    