/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ProductCard.prototype, {

    setup() {
        super.setup();

        this.pos = usePos();
        this.orm = useService("orm");
    },

    get formattedPrice() {
        const product = this.props.product;

        if (product && this.pos) {
            return this.pos.getProductPriceFormatted(product);
        }

        return "";
    },

});