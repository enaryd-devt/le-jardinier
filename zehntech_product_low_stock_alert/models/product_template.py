from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
 
    alert_quantity = fields.Float(
        string="Alert Quantity",
        compute="_compute_alert_quantity",
        inverse="_inverse_alert_quantity",
        store=False
    )
   
    qty_available = fields.Float(
        string="Quantity On Hand",
         
        store=False
    )
    
    color_field = fields.Char(string="Color", compute='_compute_color_field', store=False)

    @api.depends('qty_available', 'alert_quantity')
    def _compute_color_field(self):
       
        for product in self:
          
            if product.qty_available <= product.alert_quantity:
                product.color_field = '#f08080'
            else:
                product.color_field = ''


    @api.depends('product_variant_ids.alert_quantity')
    def _compute_alert_quantity(self):
        for template in self:
            if template.product_variant_ids:
                template.alert_quantity = template.product_variant_ids[0].alert_quantity
            else:
                template.alert_quantity = 0.0

    def _inverse_alert_quantity(self):
        for template in self:
            if template.product_variant_ids:
                template.product_variant_ids[0].alert_quantity = template.alert_quantity

   

