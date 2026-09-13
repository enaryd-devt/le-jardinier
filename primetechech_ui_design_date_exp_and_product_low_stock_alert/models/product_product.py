from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # =====================================================
    # REMISE
    # =====================================================

    discount_percent = fields.Float(
        string="Remise (%)",
        digits=(16, 2),
        default=0.0,
    )

    # =====================================================
    # STOCK
    # =====================================================

    alert_quantity = fields.Float(
        string="Quantité d'alerte",
        default=0.0,
    )

    optimal_quantity = fields.Float(
        string="Stock Optimal",
        default=0.0,
    )

    # =====================================================
    # AFFICHAGE CONDITIONNEL
    # =====================================================

    show_alert_quantity = fields.Boolean(
        compute='_compute_show_alert_quantity',
        string="Afficher le seuil d'alerte",
        store=False,
    )

    # =====================================================
    # CONTRAINTE REMISE
    # =====================================================

    @api.constrains('discount_percent')
    def _check_discount_percent(self):
        for rec in self:
            if rec.discount_percent < 0 or rec.discount_percent > 100:
                raise ValidationError(
                    "La remise doit être comprise entre 0 et 100 %."
                )

    # =====================================================
    # AFFICHAGE DU CHAMP ALERTE
    # =====================================================

    def _compute_show_alert_quantity(self):

        method = self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'zehntech_product_low_stock_alert.method',
            'global'
        )

        for rec in self:
            rec.show_alert_quantity = (
                method == 'individual'
            )

    # =====================================================
    # RECUPERATION SEUIL D'ALERTE
    # =====================================================

    @api.model
    def _get_alert_quantity(self, product):

        method = self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'zehntech_product_low_stock_alert.method',
            'global'
        )

        if method == 'global':

            global_qty = float(
                self.env[
                    'ir.config_parameter'
                ].sudo().get_param(
                    'zehntech_product_low_stock_alert.global_minimum_qty',
                    0
                )
            )

            return global_qty

        elif method == 'individual':

            return product.alert_quantity

        elif method == 'category':

            return (
                product.categ_id.alert_quantity
                if hasattr(product.categ_id, 'alert_quantity')
                else 0
            )

        return 0

    # =====================================================
    # CREATE
    # =====================================================

    @api.model
    def create(self, vals):

        product = super().create(vals)

        alert_qty = product._get_alert_quantity(product)

        if (
            alert_qty > 0
            and product.qty_available <= alert_qty
        ):

            message = (
                f"Stock faible : "
                f"{product.display_name} "
                f"({product.qty_available} restant(s), "
                f"seuil {alert_qty})"
            )

            product._notify_low_stock(
                product,
                message
            )

        return product

    # =====================================================
    # WRITE
    # =====================================================

    def write(self, vals):

        result = super().write(vals)

        for product in self:

            alert_qty = product._get_alert_quantity(
                product
            )

            if (
                alert_qty > 0
                and product.qty_available <= alert_qty
            ):

                message = (
                    f"Stock faible : "
                    f"{product.display_name} "
                    f"({product.qty_available} restant(s), "
                    f"seuil {alert_qty})"
                )

                product._notify_low_stock(
                    product,
                    message
                )

        return result

    # =====================================================
    # NOTIFICATION
    # =====================================================

    def _notify_low_stock(
        self,
        product,
        message
    ):

        user_ids_str = self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'zehntech_product_low_stock_alert.notify_user_ids',
            ''
        )

        user_ids = [
            int(uid)
            for uid in user_ids_str.split(',')
            if uid
        ]

        users = self.env[
            'res.users'
        ].browse(user_ids)

        for user in users:

            self.env[
                'mail.message'
            ].create({
                'model': 'product.product',
                'res_id': product.id,
                'author_id': self.env.user.partner_id.id,
                'partner_ids': [
                    (4, user.partner_id.id)
                ],
                'message_type': 'notification',
                'subtype_id': self.env.ref(
                    'mail.mt_note'
                ).id,
                'body': message,
            })