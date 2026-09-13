from odoo import models, fields, api
from datetime import datetime
import json


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # =====================================================
    # CHAMPS LIES A LA VARIANTE
    # =====================================================

    discount_percent = fields.Float(
        related="product_variant_id.discount_percent",
        string="Remise (%)",
        readonly=False,
        store=True,
    )

    alert_quantity = fields.Float(
        related="product_variant_id.alert_quantity",
        string="Quantité d'alerte",
        readonly=False,
        store=True,
    )

    optimal_quantity = fields.Float(
        related="product_variant_id.optimal_quantity",
        string="Stock optimal",
        readonly=False,
        store=True,
    )

    discount_display = fields.Char(
        string="Remise",
        compute="_compute_discount_display",
    )

    # =====================================================
    # COULEUR KANBAN
    # =====================================================

    color_field = fields.Char(
        string="Color",
        compute="_compute_color_field",
        store=False,
    )

    # =====================================================
    # ALERTES LOTS
    # =====================================================

    lot_alert_ids = fields.Text(
        string="Lot Alerts",
        compute="_compute_lot_alert_ids",
        store=False,
    )

    # =====================================================
    # MARGE
    # =====================================================

    margin_amount = fields.Float(
        string="Marge",
        compute="_compute_margin_amount",
        store=False,
    )

    # =====================================================
    # CALCUL MARGE
    # =====================================================

    @api.depends('list_price', 'standard_price')
    def _compute_margin_amount(self):
        for product in self:
            product.margin_amount = (
                product.list_price - product.standard_price
            )

    # =====================================================
    # AFFICHAGE REMISE
    # =====================================================

    @api.depends('discount_percent')
    def _compute_discount_display(self):
        for product in self:
            product.discount_display = (
                f"{product.discount_percent:.0f}%"
                if product.discount_percent
                else "0%"
            )

    # =====================================================
    # COULEUR STOCK
    # =====================================================

    @api.depends('qty_available', 'alert_quantity')
    def _compute_color_field(self):
        for product in self:

            if (
                product.alert_quantity > 0
                and product.qty_available <= product.alert_quantity
            ):
                product.color_field = '#f08080'
            else:
                product.color_field = ''

    # =====================================================
    # ALERTES D'EXPIRATION DES LOTS
    # =====================================================

    @api.depends('product_variant_ids')
    def _compute_lot_alert_ids(self):

        today = fields.Date.context_today(self)

        for template in self:

            alerts = []

            if template.tracking != 'lot':
                template.lot_alert_ids = json.dumps([])
                continue

            lots = self.env['stock.lot'].search([
                ('product_id.product_tmpl_id', '=', template.id),
                ('expiration_date', '!=', False),
            ])

            lots = lots.filtered(
                lambda lot: lot.product_qty > 0
            )

            for lot in lots:

                expiration_date = lot.expiration_date
                alert_date = lot.alert_date

                if not expiration_date:
                    continue

                if isinstance(expiration_date, datetime):
                    expiration_date = expiration_date.date()

                if alert_date and isinstance(alert_date, datetime):
                    alert_date = alert_date.date()

                if not alert_date:
                    continue

                if today < alert_date:
                    continue

                days_left = (
                    expiration_date - today
                ).days

                if days_left < 0:
                    status = "expired"
                    days_display = 0
                else:
                    status = "warning"
                    days_display = days_left

                alerts.append({
                    'name': lot.name,
                    'expiration_date':
                        expiration_date.strftime('%Y-%m-%d'),
                    'expiration_date_display':
                        expiration_date.strftime('%d/%m/%Y'),
                    'alert_date':
                        alert_date.strftime('%d/%m/%Y'),
                    'product_qty':
                        round(lot.product_qty, 2),
                    'days_left':
                        days_display,
                    'status':
                        status,
                    'is_expired':
                        status == 'expired',
                })

            template.lot_alert_ids = json.dumps(alerts)