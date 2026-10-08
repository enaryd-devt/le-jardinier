/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    get product() {
        return this.props.product || {};
    },

    get isStockTracked() {
        return Boolean(this.product.is_storable);
    },

    get warehouseQty() {
        return Number(this.product.primetech_pos_qty || 0);
    },

    get totalWarehouseQty() {
        return Number(this.product.primetech_pos_total_qty || 0);
    },

    get productQtyInCurrentOrder() {
        // `productCartQty` is calculated by Odoo per product template.  Stock,
        // however, is loaded per product variant.  Use the exact product here
        // so another variant cannot consume the last displayed unit.
        return (this.pos.get_order()?.lines || [])
            .filter((line) => line.product_id?.id === this.product.id)
            .reduce((total, line) => total + Math.max(0, Number(line.qty || 0)), 0);
    },

    get remainingQty() {
        return this.totalWarehouseQty - this.productQtyInCurrentOrder;
    },

    get isOutOfStock() {
        return this.isStockTracked && this.remainingQty <= 0 && !this.canSellNegativeStock;
    },

    get isStockEmpty() {
        return this.isStockTracked && this.remainingQty <= 0;
    },

    get canSellNegativeStock() {
        const allowedUsers = this.pos.config.raw?.primetech_negative_stock_user_ids || [];
        return Boolean(this.pos.config.primetech_allow_negative_stock && allowedUsers.includes(this.pos.user?.id));
    },

    get isLowStock() {
        return this.isStockTracked && this.remainingQty > this.criticalStockLevel && this.remainingQty <= this.warningStockLevel;
    },

    get criticalStockLevel() {
        return Number(this.pos.config.primetech_stock_critical_level ?? 0);
    },

    get warningStockLevel() {
        return Number(this.pos.config.primetech_stock_warning_level ?? 5);
    },

    get stockClass() {
        if (!this.isStockTracked) return "pt-stock-not-tracked";
        if (this.remainingQty <= 0) return "pt-stock-danger";
        if (this.isLowStock) return "pt-stock-warning";
        return "pt-stock-success";
    },

    get formattedWarehouseQty() {
        return this.env.utils.formatProductQty(Math.max(0, this.remainingQty), false);
    },

    get formattedSalesPrice() {
        const price = this.product.get_price?.(this.pos.config.pricelist_id, 1) ?? this.product.lst_price ?? 0;
        return this.env.utils.formatCurrency(price);
    },

    onProductClick(event) {
        if (this.isOutOfStock) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        this.props.onClick(event);
    },

    onProductKeypress(event) {
        if (this.isOutOfStock) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        if (event.code === "Space") {
            this.props.onClick(event);
        }
    },
});
