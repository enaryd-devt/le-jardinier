# -*- coding: utf-8 -*-

from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _load_pos_data(self, data):
        """Expose the current user's POS role without exposing group details."""
        result = super()._load_pos_data(data)
        if self.env.user.has_group("primetech_pos_product_enhancement.group_pos_cashier"):
            role = "cashier"
        elif self.env.user.has_group("primetech_pos_product_enhancement.group_pos_seller"):
            role = "seller"
        else:
            role = "manager"
        for user in result["data"]:
            user["role"] = role
        return result
