/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    primetechIsSeller() {
        return this.user?.raw?.role === "seller";
    },

    showScreen(name, props) {
        if (name === "TicketScreen" && this.primetechIsSeller()) {
            this.env.services.notification.add(
                "Le rôle vendeur ne peut pas consulter les anciennes commandes ni effectuer de remboursement.",
                { type: "warning" }
            );
            return;
        }
        return super.showScreen(...arguments);
    },

    async pay() {
        if (this.primetechIsSeller()) {
            this.env.services.notification.add(
                "Le paiement est réservé au caissier POS.",
                { type: "warning" }
            );
            return false;
        }
        return super.pay(...arguments);
    },

    async primetechSendOrder() {
        const order = this.get_order();
        if (!order || order.is_empty()) {
            return false;
        }
        await this.syncAllOrders({ orders: [order], throw: true });
        this.env.services.notification.add(
            "Commande envoyée au caissier pour règlement.",
            { type: "success" }
        );
        this.add_new_order();
        return true;
    },
});
