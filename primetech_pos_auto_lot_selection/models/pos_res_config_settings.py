# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_auto_lot_selection = fields.Boolean(string="Enable Auto Lot Selection", related='pos_config_id.enable_auto_lot_selection', readonly=False)