/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PaymentScreen.prototype, {

    setup() {
        super.setup();
        this.pos = usePos();
    },

    async validateOrder(isForceValidate) {

        const order = this.pos.get_order();
        if (!order) {
            return await super.validateOrder(isForceValidate);
        }

        // sauvegarder les lignes avant validation
        const lines = order.get_orderlines().map(line => ({
            product: line.product,
            qty: line.quantity
        }));

        await super.validateOrder(isForceValidate);

        // mise à jour du stock local
        for (const line of lines) {

            const product = line.product;
            if (!product) continue;

            if (product.qty_local === undefined) {
                product.qty_local = product.qty_available ?? 0;
            }

            product.qty_local -= line.qty;

            if (product.qty_local < 0) {
                product.qty_local = 0;
            }
        }

        // forcer rafraîchissement écran produits
        this.render();

    },
});