# Part of Wicoders Solutions
# copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, values):
        result = super(SaleOrder, self).write(values)

        if "pricelist_id" in values:
            self.order_line.filtered(lambda line: line.update_unit_price())
        return result


class SaleOrderline(models.Model):
    _inherit = "sale.order.line"

    def update_unit_price(self):
        message = ""
        if self.order_id.pricelist_id:
            unit_price = self.price_unit
            if (
                self.order_id.pricelist_id
                and self.product_id
                and not self.env.user.has_groups(
                    "wi_restrict_saleprice_change.groups_restrict_change_price"
                )
            ):
                product_context = dict(
                    self.env.context,
                    partner_id=self.order_id.partner_id.id,
                    date=self.order_id.date_order,
                    uom=self.product_uom_id.id,
                )
                price, rule_id = self.order_id.pricelist_id.with_context(
                    product_context
                )._get_product_price_rule(
                    self.product_id,
                    self.product_uom_qty or 1.0,
                )
                price = "%.2f" % price
                if (unit_price < float(price)) and rule_id:
                    self.price_unit = price
                    message = _(
                        "You don’t have permission to decrease the price."
                        + str(price)
                    )
        return message

    @api.constrains("price_unit")
    def change_constrains_price_unit(self):
        self.mapped(lambda line: line.update_unit_price())

    @api.onchange("price_unit")
    def change_price_unit(self):
        message = self.update_unit_price()
        if message:
            raise UserError(message)
