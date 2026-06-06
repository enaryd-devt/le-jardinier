from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # =====================================================
    # STOCK ALERT QUANTITY
    # =====================================================

    alert_quantity = fields.Float(
        string="Alert Quantity",
        compute="_compute_alert_quantity",
        inverse="_inverse_alert_quantity",
        store=False
    )

    # =====================================================
    # COLOR FIELD (KANBAN)
    # =====================================================

    color_field = fields.Char(
        string="Color",
        compute='_compute_color_field',
        store=False
    )

    # =====================================================
    # MARGIN
    # =====================================================

    margin_amount = fields.Float(
        string="Margin",
        compute="_compute_margin_amount",
        store=False
    )

    # =====================================================
    # COMPUTE METHODS
    # =====================================================

    @api.depends('list_price', 'standard_price')
    def _compute_margin_amount(self):
        for product in self:
            product.margin_amount = product.list_price - product.standard_price

    # -----------------------------------------------------

    @api.depends('qty_available', 'alert_quantity')
    def _compute_color_field(self):
        for product in self:
            product.color_field = (
                '#f08080' if product.qty_available <= product.alert_quantity else ''
            )

    # -----------------------------------------------------

    @api.depends('product_variant_ids.alert_quantity')
    def _compute_alert_quantity(self):
        for template in self:
            template.alert_quantity = (
                template.product_variant_ids[0].alert_quantity
                if template.product_variant_ids else 0.0
            )

    def _inverse_alert_quantity(self):
        for template in self:
            if template.product_variant_ids:
                template.product_variant_ids[0].alert_quantity = template.alert_quantity