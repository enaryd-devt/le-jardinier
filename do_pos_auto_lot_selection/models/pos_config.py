# -*- coding: utf-8 -*-

from odoo import models, fields


class PosConfig(models.Model):
	_inherit = 'pos.config'

	enable_auto_lot_selection = fields.Boolean(string="Enable Auto Lot Selection")