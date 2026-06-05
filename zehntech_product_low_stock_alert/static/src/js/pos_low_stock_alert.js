/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { _t } from "@web/core/l10n/translation";
function injectCustomStyle() {
    if (document.getElementById("low_stock_style")) return;

    const style = document.createElement("style");
    style.id = "low_stock_style";

    style.innerHTML = `
    
    /* ===================== */
    /* STOCK BADGES */
    /* ===================== */

    .stock-ok {
        color: #198754 !important;
        background: rgba(25, 135, 84, 0.12) !important;
        padding: 4px 10px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        border-radius: 999px;
    }

    .stock-warning {
        color: #fd7e14 !important;
        background: rgba(253, 126, 20, 0.12) !important;
        padding: 4px 10px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        border-radius: 999px;
        animation: pulseWarning 1.8s infinite;
    }

    .stock-critical {
        color: #dc3545 !important;
        background: rgba(220, 53, 69, 0.12) !important;
        padding: 4px 10px !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        border-radius: 999px;
        animation: pulseCritical 1.2s infinite;
    }

    /* ===================== */
    /* ANIMATIONS */
    /* ===================== */

    @keyframes pulseWarning {
        0% { box-shadow: 0 0 0 0 rgba(253, 126, 20, 0.35); }
        70% { box-shadow: 0 0 0 8px rgba(253, 126, 20, 0); }
        100% { box-shadow: 0 0 0 0 rgba(253, 126, 20, 0); }
    }

    @keyframes pulseCritical {
        0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.45); }
        70% { box-shadow: 0 0 0 10px rgba(220, 53, 69, 0); }
        100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
    }
    `;

    document.head.appendChild(style);
}

patch(ProductCard.prototype, {
    async setup() {
        super.setup();
        this.orm = useService("orm");
        await this._computeLowStockStatus();
    },

async _computeLowStockStatus() {

    const productId = this.props.productId;
    if (!productId) return;

    const [product] = await this.orm.call(
        "product.product",
        "search_read",
        [[["id", "=", productId]], ["alert_quantity", "qty_available"]]
    );

    if (!product) return;

    const alertQty = product.alert_quantity || 0;
    const qty = product.qty_available || 0;

    let stockClass = "stock-ok";
    let message = `Stock OK: ${qty}`;

    // =========================
    // LOGIQUE 3 NIVEAUX
    // =========================

    if (qty <= alertQty) {
        stockClass = "stock-critical";
        message = `CRITICAL: ${qty} (Alert: ${alertQty})`;

    } else if (qty <= alertQty * 1.5) {
        stockClass = "stock-warning";
        message = `LOW STOCK: ${qty} (Alert: ${alertQty})`;
    }

    injectCustomStyle();

    setTimeout(() => {

        const article = document.querySelector(
            `article[data-product-id="${productId}"]`
        );

        if (!article) return;

        const tag = article.querySelector(".product-information-tag");

        if (!tag) return;

        // reset classes propres
        tag.classList.remove("stock-ok", "stock-warning", "stock-critical");
        tag.classList.add(stockClass);

        tag.setAttribute("data-tooltip", _t(message));

    }, 80);
}
});







 