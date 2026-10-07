from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    primetech_order_sequence_id = fields.Many2one(
        "ir.sequence", string="Séquence des commandes POS", copy=False,
        help="Numéro des commandes POS : COM + année/mois/jour + compteur.",
    )
    primetech_order_padding = fields.Integer(
        string="Nombre de chiffres de la séquence", default=4,
        help="Exemple avec 4 chiffres : COM2609120001.",
    )
    primetech_stock_location_name = fields.Char(
        string="Entrepôt de déstockage", compute="_compute_primetech_stock_location_name"
    )

    primetech_stock_critical_level = fields.Float(string="Seuil critique (rouge)", default=0.0)
    primetech_stock_warning_level = fields.Float(string="Seuil d'alerte (orange)", default=5.0)
    primetech_allow_negative_stock = fields.Boolean(
        string="Autoriser les ventes à stock négatif", default=False,
        help="Les utilisateurs autorisés peuvent vendre un produit stockable même si son stock est nul.",
    )
    primetech_negative_stock_user_ids = fields.Many2many(
        "res.users", string="Utilisateurs autorisés à vendre en stock négatif",
    )

    primetech_stock_operation_name = fields.Char(
        string="Type d'opération POS", compute="_compute_primetech_stock_location_name"
    )

    @api.depends("picking_type_id.warehouse_id", "picking_type_id.default_location_src_id")
    def _compute_primetech_stock_location_name(self):
        for config in self:
            warehouse = config.picking_type_id.warehouse_id
            config.primetech_stock_location_name = (
                warehouse.name
                or config.picking_type_id.default_location_src_id.display_name
                or ""
            )
            config.primetech_stock_operation_name = config.picking_type_id.display_name or ""

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        configs._primetech_ensure_order_sequence()
        return configs

    def _primetech_ensure_order_sequence(self):
        for config in self.filtered(lambda c: not c.primetech_order_sequence_id):
            sequence = self.env["ir.sequence"].create({
                "name": "Commandes POS - %s" % config.name,
                "code": "primetech.pos.order.%s" % config.id,
                "prefix": "COM%(y)s%(month)s%(day)s",
                "padding": config.primetech_order_padding or 4,
                "company_id": config.company_id.id,
            })
            config.primetech_order_sequence_id = sequence
        return self.primetech_order_sequence_id

    def write(self, vals):
        result = super().write(vals)
        if "primetech_order_padding" in vals:
            for config in self.filtered("primetech_order_sequence_id"):
                config.primetech_order_sequence_id.write({"padding": max(1, config.primetech_order_padding or 4)})
        return result

    @api.constrains("primetech_stock_critical_level", "primetech_stock_warning_level")
    def _check_primetech_stock_levels(self):
        for config in self:
            if config.primetech_stock_critical_level > config.primetech_stock_warning_level:
                raise ValidationError("Le seuil critique ne peut pas dépasser le seuil d'alerte.")

    @api.model
    def _load_pos_data_fields(self, config_id):
        loaded_fields = super()._load_pos_data_fields(config_id)

        # In this Odoo version, pos.config inherits the POS loading mixin,
        # whose default list is empty. Returning only our custom field would
        # omit core fields such as use_pricelist and break POS initialization.
        if not loaded_fields:
            loaded_fields = [
                "id", "name", "display_name", "company_id", "currency_id",
                "current_session_id",
                "picking_type_id", "pricelist_id", "available_pricelist_ids",
                "use_pricelist", "payment_method_ids", "fiscal_position_ids",
                "default_fiscal_position_id", "default_bill_ids", "tip_product_id",
                "iface_tipproduct", "iface_tax_included", "iface_cashdrawer",
                "iface_electronic_scale", "iface_print_via_proxy",
                "iface_scan_via_proxy", "iface_big_scrollbars", "iface_print_auto",
                "iface_print_skip_screen", "iface_available_categ_ids",
                "limit_categories", "customer_display_type", "access_token",
                "proxy_ip", "cash_control", "cash_rounding", "rounding_method",
                "only_round_cash_method", "manual_discount", "restrict_price_control",
                "is_margins_costs_accessible_to_every_user", "module_pos_restaurant",
                "module_pos_hr", "show_product_images", "show_category_images",
                "receipt_header", "receipt_footer", "basic_receipt", "note_ids",
                "trusted_config_ids", "orderlines_sequence_in_cart_by_category",
                "ship_later", "picking_policy", "warehouse_id", "route_id",
                "is_posbox", "auto_validate_terminal_payment", "printer_ids",
                "floor_ids", "advanced_employee_ids", "group_pos_manager_id",
                "self_ordering_mode", "takeaway_fp_id", "_product_default_values",
            ]
        # La séquence reste côté serveur : ne pas charger le modèle ir.sequence
        # dans le cache relationnel du POS.
        for name in (
            "primetech_stock_location_name",
            "primetech_stock_operation_name",
            "primetech_stock_critical_level",
            "primetech_stock_warning_level",
            "primetech_allow_negative_stock",
            "primetech_negative_stock_user_ids",
        ):
            if name not in loaded_fields:
                loaded_fields.append(name)
        # Some POS extensions (restaurant, self-order, HR, ...) add their own
        # configuration fields. Keep only fields present in this database so a
        # feature that is not installed cannot abort the whole POS bootstrap.
        return [name for name in loaded_fields if name in self._fields]
