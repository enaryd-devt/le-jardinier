/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.ptStockOrm = useService("orm");
    },

    async _finalizeValidation() {
        const result = await super._finalizeValidation(...arguments);
        await this._primetechReloadStockQuantities();
        return result;
    },

    async _primetechReloadStockQuantities() {
        const sessionId = this.pos.session?.id;
        if (!sessionId) {
            return;
        }

        try {
            const data = await this.ptStockOrm.call(
                "pos.session",
                "primetech_reload_products",
                [sessionId]
            );
            const products = data?.["product.product"]?.data;
            if (Array.isArray(products)) {
                this.pos.data.models.loadData({ "product.product": products }, [], false);
            }
        } catch (error) {
            console.warn("PrimeTech POS stock reload after payment", error);
        }
    },
});
