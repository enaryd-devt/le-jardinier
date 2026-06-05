# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError



class StockLotFEFO(models.Model):
    _inherit = "stock.lot"

    @api.model
    def allocate_fefo_lots(self, product_id, requested_qty):
    

        lots = self.get_available_lots_for_pos_product(product_id) or []

        if not lots:
            return []

        # =========================================================
        # TRI FEFO
        # =========================================================
        lots.sort(
            key=lambda l: (
                l.get('expiration_date')
                or l.get('alert_date')
                or '9999-12-31'
            )
        )

        # =========================================================
        # STOCK TOTAL DISPONIBLE
        # =========================================================
        total_available = sum(lot.get('available_qty', 0) for lot in lots)

        # =========================================================
        # CONTRÔLE GLOBAL (anti négatif)
        # =========================================================
        if total_available < requested_qty:
            return []

        # =========================================================
        # ALLOCATION FEFO
        # =========================================================
        remaining_qty = requested_qty
        allocations = []

        for lot in lots:

            if remaining_qty <= 0:
                break

            available_qty = lot.get('available_qty', 0)

            if available_qty <= 0:
                continue

            # =====================================================
            # IMPORTANT :
            # sécurité anti dépassement lot individuel
            # =====================================================
            qty_to_take = min(available_qty, remaining_qty)

            allocations.append({
                'lot_id': lot['id'],
                'lot_name': lot['name'],
                'qty': qty_to_take,
                'available_qty': available_qty,
            })

            remaining_qty -= qty_to_take

        # =========================================================
        # DOUBLE CHECK FINAL (ANTI STOCK NEGATIF LOT)
        # =========================================================
        for alloc in allocations:
            if alloc['qty'] > alloc['available_qty']:
                return []  # sécurité absolue

        return allocations
    
    
    @api.model
    def check_global_stock(self, product_id, requested_qty, used_qty=0):

        product = self.env["product.product"].browse(product_id)

        available_qty = product.qty_available - used_qty

        if available_qty < requested_qty:
            return False

        return True