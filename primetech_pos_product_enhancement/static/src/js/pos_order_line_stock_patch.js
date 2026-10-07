/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrderline.prototype, {
    set_quantity(quantity, keep_price) {
        const requestedQty = typeof quantity === "number" ? quantity : Number.parseFloat(quantity);
        const product = this.product_id;
        const stockQty = Number(product?.primetech_pos_qty);
        const activeUserId = this.models["res.users"]?.getFirst()?.id;
        const allowedUsers = this.config.raw?.primetech_negative_stock_user_ids || [];
        const canSellNegativeStock = Boolean(
            this.config.primetech_allow_negative_stock && allowedUsers.includes(activeUserId)
        );

        if (
            !product?.is_storable &&
            ["consu", "service"].includes(product?.type) &&
            Number.isFinite(requestedQty) &&
            requestedQty > 0
        ) {
            const qtyOnOtherLines = this.order_id.lines
                .filter(
                    (line) =>
                        line !== this &&
                        line !== this._primetechMergingLine &&
                        line.product_id?.id === product.id
                )
                .reduce((total, line) => total + Math.max(0, line.get_quantity()), 0);
            const maxQty = Math.max(0, 1 - qtyOnOtherLines);

            if (requestedQty > maxQty) {
                if (maxQty === 0) {
                    this.delete();
                } else {
                    super.set_quantity(maxQty, keep_price);
                }
                return {
                    title: _t("Quantité maximale atteinte"),
                    body: _t("La quantité maximale autorisée pour un service ou un consommable est de 1."),
                };
            }
        }

        // Apply stock limits only to storable products.
        if (
            product?.is_storable && !canSellNegativeStock &&
            Number.isFinite(stockQty) &&
            Number.isFinite(requestedQty) &&
            requestedQty > 0
        ) {
            const qtyOnOtherLines = this.order_id.lines
                .filter(
                    (line) =>
                        line !== this &&
                        line !== this._primetechMergingLine &&
                        line.product_id?.id === product.id
                )
                .reduce((total, line) => total + Math.max(0, line.get_quantity()), 0);
            const availableQty = Math.max(0, stockQty - qtyOnOtherLines);

            if (requestedQty > availableQty) {
                super.set_quantity(availableQty, keep_price);
                return {
                    title: _t("Quantité indisponible"),
                    body: _t("Vous ne pouvez vendre que la quantité disponible : %s.", availableQty),
                };
            }
        }
        return super.set_quantity(...arguments);
    },

    merge(orderline) {
        // On a card click Odoo first creates a line with quantity 1, then
        // merges it into an existing line.  That temporary line must not be
        // deducted a second time while the destination line is validated.
        this._primetechMergingLine = orderline;
        try {
            return super.merge(...arguments);
        } finally {
            this._primetechMergingLine = undefined;
        }
    },
});
