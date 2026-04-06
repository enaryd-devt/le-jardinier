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

    async refreshProductStock() {

        const product = this.props.product;

        const result = await this.orm.call(
            "product.product",
            "read",
            [[product.id], ["qty_available"]]
        );

        if (result && result.length) {
            product.qty_available = result[0].qty_available;
        }
    },

});