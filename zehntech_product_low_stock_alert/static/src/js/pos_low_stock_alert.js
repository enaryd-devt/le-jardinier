/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { _t } from "@web/core/l10n/translation";
function injectCustomStyle() {
    const style = document.createElement("style");
    style.innerHTML = `
    .low-stock-warning {
        color: white !important;
        background-color: red !important;
        padding: 5px 10px !important;
        font-size: 12px !important;
        font-weight: bold !important;
        border-radius: 4px;
        position: relative;
    }
    .low-stock-warning::after {
        
        transition: opacity 0.3s;
        z-index: 10;
    }
    .low-stock-warning:hover::after {
        opacity: 1;
    }`;
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
       

        const [product] = await this.orm.call(
            "product.product",
            "search_read",
            [[["id", "=", productId]], ["id", "display_name", "alert_quantity", "qty_available"]]
        );

        if (!product) {
            
            return;
        }
       
        const alertQty = product.alert_quantity || 0;
        const availableQty = product.qty_available || 0;
        
        if (availableQty <= alertQty&& availableQty >= 0)  {
            injectCustomStyle();
            setTimeout(() => {
                const article = document.querySelector(`article[data-product-id="${productId}"]`);
                if (article) {
                    const infoTag = article.querySelector(".product-information-tag");
                    if (infoTag && !infoTag.classList.contains("low-stock-warning")) {
                        infoTag.classList.add("low-stock-warning");
                       infoTag.setAttribute("data-tooltip",  _t("Low Stock! Only %s left (Alert at %s)").replace("%s", availableQty).replace("%s", alertQty));

                    }
                }
            }, 100);
        }
    }
});







 