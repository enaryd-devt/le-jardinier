/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

patch(ProductCard.prototype, {

    setup() {
        super.setup();

        this.pos = usePos();
        this.orm = useService("orm");

        // STATE (hover stock refresh)
        this.state = useState({
            stockHovered: false,
        });
    },

    // =========================================================
    // HOVER EVENTS
    // =========================================================

    onStockEnter() {
        this.state.stockHovered = true;
    },

    onStockLeave() {
        this.state.stockHovered = false;
    },

    // =========================================================
    // APRES RECHARGEMENT DU POS
    // =========================================================

    async afterLoadServerData() {
        await super.afterLoadServerData(...arguments);

        const products = this.models["product.product"].getAll();
        const productIds = products.map(p => p.id);

        const data = await this.env.services.orm.read(
            "product.product",
            productIds,
            ["qty_available", "virtual_available"]
        );

        const map = new Map(data.map(p => [p.id, p]));

        for (const product of products) {
            const stock = map.get(product.id);
            if (stock) {
                product.qty_available = stock.qty_available;
                product.virtual_available = stock.virtual_available;
            }
        }
    },

    // =========================================================
    // REFRESH STOCK
    // =========================================================

    async refreshStock(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        ev.stopImmediatePropagation(); 

        const result = await this.orm.read(
            "product.product",
            [this.props.product.id],
            ["qty_available", "virtual_available"]
        );

        if (result?.length) {
            this.props.product.qty_available = result[0].qty_available;
            this.props.product.virtual_available = result[0].virtual_available;
        }

        this.state.stockHovered = false;
    },

    // =========================================================
    // PRODUCT
    // =========================================================

    get product() {
        return this.props.product || {};
    },

    // =========================================================
    // STOCK
    // =========================================================

    get qtyAvailable() {
        return this.product.qty_available ?? 0;
    },

    get virtualAvailable() {
        return this.product.virtual_available ?? 0;
    },

    get isOutOfStock() {
        return this.qtyAvailable <= 0;
    },

    get isLowStock() {
        return this.qtyAvailable > 0 && this.qtyAvailable <= 5;
    },

    get stockClass() {
        if (this.isOutOfStock) return "pt-stock-danger";
        if (this.isLowStock) return "pt-stock-warning";
        return "pt-stock-success";
    },

    // =========================================================
    // PRICE
    // =========================================================

    get formattedPrice() {
        const price = this.product.lst_price || 0;

        return this.env?.utils?.formatCurrency
            ? this.env.utils.formatCurrency(price)
            : price;
    },

    // =========================================================
    // COST
    // =========================================================

    get productCost() {
        const cost = this.product.standard_price || 0;

        return this.env?.utils?.formatCurrency
            ? this.env.utils.formatCurrency(cost)
            : cost;
    },

    // =========================================================
    // MARGIN
    // =========================================================

    get marginValue() {
        return (this.product.lst_price || 0) - (this.product.standard_price || 0);
    },

    get marginAmount() {
        return this.env?.utils?.formatCurrency
            ? this.env.utils.formatCurrency(this.marginValue)
            : this.marginValue;
    },

    get marginPercent() {
        const sale = this.product.lst_price || 0;
        if (!sale) return 0;

        return ((this.marginValue / sale) * 100).toFixed(1);
    },

    // =========================================================
    // TRACKING
    // =========================================================

    get hasTracking() {
        return ["lot", "serial"].includes(this.product.tracking);
    },

    // =========================================================
    // LOTS / WAREHOUSES
    // =========================================================

    get lots() {
        return this.product.pos_lots || [];
    },

    get warehouses() {
        return this.product.pos_warehouses || [];
    },

});

