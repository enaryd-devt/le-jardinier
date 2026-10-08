from collections import defaultdict

from odoo import api, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _primetech_notify_light_order_sync(self):
        """Broadcast only the changed order and its lines to devices of this POS."""
        self.ensure_one()
        self.config_id._notify(
            "PRIMETECH_ORDER_SYNC",
            {
                "origin_session_id": self.session_id.id,
                "login_number": self.env.context.get("login_number"),
                "records": self.read_pos_data([], self.config_id.id),
            },
        )

    def _primetech_get_source_locations(self, lines, picking_type):
        """Allocate each POS line to an internal location of the POS warehouse."""
        warehouse_root = (
            picking_type.warehouse_id.view_location_id
            or picking_type.default_location_src_id
        )
        source_by_line = {}
        if not warehouse_root:
            return source_by_line

        product_ids = lines.product_id.ids
        groups = self.env["stock.quant"].read_group(
            [
                ("product_id", "in", product_ids),
                ("location_id", "child_of", warehouse_root.id),
                ("location_id.usage", "=", "internal"),
            ],
            ["product_id", "location_id", "quantity:sum", "reserved_quantity:sum"],
            ["product_id", "location_id"],
            lazy=False,
        )
        available = defaultdict(list)
        for group in groups:
            product = group.get("product_id")
            location = group.get("location_id")
            qty = (group.get("quantity", 0.0) or 0.0) - (group.get("reserved_quantity", 0.0) or 0.0)
            if product and location and qty > 0:
                available[product[0]].append([location[0], qty])

        # Reserve the chosen quantity in memory so several lines of the same
        # product cannot be assigned twice to the same available stock.
        for line in lines.filtered(lambda line: line.qty > 0):
            candidates = sorted(available.get(line.product_id.id, []), key=lambda item: item[1], reverse=True)
            candidate = next((item for item in candidates if item[1] >= line.qty), None)
            if candidate:
                source_by_line[line.id] = candidate[0]
                candidate[1] -= line.qty
            else:
                source_by_line[line.id] = picking_type.default_location_src_id.id
        return source_by_line

    def _primetech_source_has_required_stock(self, lines, source_location_id):
        """Check whether a POS picking can be completed from its source location."""
        required_by_product = defaultdict(float)
        for line in lines:
            required_by_product[line.product_id.id] += line.qty

        groups = self.env["stock.quant"].read_group(
            [
                ("product_id", "in", list(required_by_product)),
                ("location_id", "child_of", source_location_id),
                ("location_id.usage", "=", "internal"),
            ],
            ["product_id", "quantity:sum", "reserved_quantity:sum"],
            ["product_id"],
            lazy=False,
        )
        available_by_product = {
            group["product_id"][0]: (group.get("quantity", 0.0) or 0.0)
            - (group.get("reserved_quantity", 0.0) or 0.0)
            for group in groups
            if group.get("product_id")
        }
        return all(
            available_by_product.get(product_id, 0.0) >= required_qty
            for product_id, required_qty in required_by_product.items()
        )

    def _create_order_picking(self):
        """Create POS deliveries and validate only those fully available at source."""
        self.ensure_one()
        if self.shipping_date or not self._should_create_picking_real_time():
            return super()._create_order_picking()

        picking_type = self.config_id.picking_type_id
        if not picking_type:
            return super()._create_order_picking()
        destination_id = (
            self.partner_id.property_stock_customer.id
            or picking_type.default_location_dest_id.id
            or self.env["stock.warehouse"]._get_partner_locations()[0].id
        )
        lines = self.lines.filtered(
            lambda line: line.product_id.type == "consu"
            and not float_is_zero(line.qty, precision_rounding=line.product_id.uom_id.rounding)
        )
        positive_lines = lines.filtered(lambda line: line.qty > 0)
        negative_lines = lines - positive_lines
        pickings = self.env["stock.picking"]

        lines_by_source = defaultdict(lambda: self.env["pos.order.line"])
        source_by_line = self._primetech_get_source_locations(positive_lines, picking_type)
        for line in positive_lines:
            source_id = source_by_line.get(line.id)
            lines_by_source[source_id] |= line

        for source_id, source_lines in lines_by_source.items():
            picking = self.env["stock.picking"].create(
                self.env["stock.picking"]._prepare_picking_vals(
                    self.partner_id, picking_type, source_id, destination_id
                )
            )
            picking._create_move_from_pos_order_lines(source_lines)
            self.env.flush_all()
            if self._primetech_source_has_required_stock(source_lines, source_id):
                try:
                    with self.env.cr.savepoint():
                        picking._action_done()
                except (UserError, ValidationError):
                    pass
            pickings |= picking

        if negative_lines:
            return_type = picking_type.return_picking_type_id or picking_type
            return_destination = (
                return_type.default_location_dest_id.id
                if picking_type.return_picking_type_id
                else picking_type.default_location_src_id.id
            )
            picking = self.env["stock.picking"].create(
                self.env["stock.picking"]._prepare_picking_vals(
                    self.partner_id, return_type, destination_id, return_destination
                )
            )
            picking._create_move_from_pos_order_lines(negative_lines)
            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    picking._action_done()
            except (UserError, ValidationError):
                pass
            pickings |= picking

        pickings.write({"pos_session_id": self.session_id.id, "pos_order_id": self.id, "origin": self.name})
        return pickings

    @api.model
    def _process_order(self, order, existing_order):
        pos_order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(pos_order_id)
        if not existing_order:
            sequence = pos_order.config_id._primetech_ensure_order_sequence()
            if sequence:
                number = sequence.with_company(pos_order.company_id).next_by_id()
                pos_order.write({"name": number, "pos_reference": number})
        if self.env.context.get("primetech_light_order_sync"):
            pos_order._primetech_notify_light_order_sync()
        return pos_order_id
