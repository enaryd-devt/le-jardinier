# -*- coding: utf-8 -*-

from odoo import api, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    @api.model
    def get_available_lots_for_pos_product(self, product_id):

        # ==========================================
        # POS LOCATION
        # ==========================================

        pos_config = self.env['pos.config'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        location = pos_config.picking_type_id.default_location_src_id

        # ==========================================
        # STOCK QUANTS
        # ==========================================

        quants = self.env['stock.quant'].read_group(
            [
                ('product_id', '=', product_id),
                ('location_id', 'child_of', location.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ],
            ['quantity:sum', 'lot_id'],
            ['lot_id']
        )

        # ==========================================
        # RESULT
        # ==========================================

        lots = []

        for q in quants:

            lot = self.env['stock.lot'].browse(q['lot_id'][0])

            lots.append({
                'id': lot.id,
                'name': lot.name,
                'available_qty': q['quantity'],
                'expiration_date': lot.expiration_date,
                'alert_date': lot.alert_date,
            })

        return lots