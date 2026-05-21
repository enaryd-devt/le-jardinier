from odoo import models, fields, api
from datetime import datetime, date
import json


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # =====================================================
    # STOCK ALERT
    # =====================================================

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

    # =====================================================
    # COLOR LOW STOCK
    # =====================================================

    color_field = fields.Char(
        string="Color",
        compute='_compute_color_field',
        store=False
    )

    # =====================================================
    # LOT EXPIRATION ALERT (KANBAN)
    # =====================================================

    lot_alert_ids = fields.Text(
        string="Lot Alerts",
        compute="_compute_lot_alert_ids",
        store=False
    )
    # =====================================================
    # MARGIN (KANBAN)
    # =====================================================
    margin_amount = fields.Float(
    string="Margin",
    compute="_compute_margin_amount",
    store=False
    )

    @api.depends('list_price', 'standard_price')
    def _compute_margin_amount(self):
        for product in self:
            product.margin_amount = product.list_price - product.standard_price

    # =====================================================
    # COLOR COMPUTE
    # =====================================================

    @api.depends('qty_available', 'alert_quantity')
    def _compute_color_field(self):
        for product in self:
            product.color_field = (
                '#f08080' if product.qty_available <= product.alert_quantity else ''
            )

    # =====================================================
    # ALERT QUANTITY
    # =====================================================

    @api.depends('product_variant_ids.alert_quantity')
    def _compute_alert_quantity(self):
        for template in self:
            template.alert_quantity = (
                template.product_variant_ids[0].alert_quantity
                if template.product_variant_ids
                else 0.0
            )

    def _inverse_alert_quantity(self):
        for template in self:
            if template.product_variant_ids:
                template.product_variant_ids[0].alert_quantity = template.alert_quantity

    # =====================================================
    # LOT EXPIRATION ALERT COMPUTE
    # =====================================================

    def _compute_lot_alert_ids(self):

        today = fields.Date.context_today(self)

        if isinstance(today, datetime):
            today = today.date()

        for template in self:

            alerts = []

            # =====================================================
            # CONDITION : tracking lot uniquement
            # =====================================================

            if template.tracking != 'lot':
                template.lot_alert_ids = json.dumps([])
                continue

            lots = self.env['stock.lot'].search([
                ('product_id', 'in', template.product_variant_ids.ids),
                ('expiration_date', '!=', False),
                ('product_qty', '>', 0),
            ])

            if not lots:
                template.lot_alert_ids = json.dumps([])
                continue

            for lot in lots:

                alert_date = lot.alert_date
                expiration_date = lot.expiration_date

                # ---------------- NORMALISATION ----------------

                if isinstance(alert_date, str):
                    alert_date = fields.Date.from_string(alert_date)
                elif isinstance(alert_date, datetime):
                    alert_date = alert_date.date()

                if isinstance(expiration_date, str):
                    expiration_date = fields.Date.from_string(expiration_date)
                elif isinstance(expiration_date, datetime):
                    expiration_date = expiration_date.date()

                if not alert_date or not expiration_date:
                    continue

                if not isinstance(alert_date, date) or not isinstance(expiration_date, date):
                    continue

                # =====================================================
                # CONDITION D’AFFICHAGE
                # =====================================================

                if alert_date <= today <= expiration_date:

                    alerts.append({
                        'name': lot.name or '',
                        'expiration_date': expiration_date.strftime('%d/%m/%Y'),
                        'product_qty': round(lot.product_qty, 2),
                    })

            template.lot_alert_ids = json.dumps(alerts)



