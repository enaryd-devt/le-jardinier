/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";

patch(Navbar.prototype, {

    triggerRefresh() {
        console.log("🔥 REFRESH CLICKED");

        // ✅ Odoo 18 POS correct way
        const pos = this.env.services.pos;

        // 🔥 reload via reloadOrders / loadFromServer via store
        pos.get_order_list?.()?.length; // safe access (debug)

        // 👉 méthode safe : reload page POS (100% compatible)
        window.location.reload();
    },

});
