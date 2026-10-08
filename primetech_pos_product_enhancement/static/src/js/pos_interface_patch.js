/** @odoo-module **/

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.ptClock = useState({ value: "" });
        this.orm = useService("orm");
        this.ptReloading = useState({ value: false });
        const updateClock = () => { this.ptClock.value = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date()); };
        onMounted(() => { updateClock(); this._ptClockTimer = window.setInterval(updateClock, 1000); });
        onWillUnmount(() => window.clearInterval(this._ptClockTimer));
    },
    get ptCashierName() {
        return this.pos.get_cashier?.()?.name || this.pos.user?.name || "Utilisateur POS";
    },
    get ptWarehouseName() {
        return this.pos.config.primetech_stock_location_name || "Entrepôt non défini";
    },
    async reloadCatalogue() {
        if (this.ptReloading.value) return;
        this.ptReloading.value = true;
        try {
            const data = await this.orm.call("pos.session", "primetech_reload_products", [this.pos.session.id]);
            const products = data?.["product.product"]?.data;
            if (!Array.isArray(products)) {
                throw new Error("Invalid POS product reload response");
            }
            this.pos.data.models.loadData({ "product.product": products }, [], false);
            this.notification.add(_t("Catalogue et quantités actualisés."), { type: "success" });
        } catch (error) {
            this.notification.add(_t("Le catalogue n'a pas pu être actualisé."), { type: "danger" });
            console.warn("PrimeTech POS catalogue reload", error);
        } finally {
            this.ptReloading.value = false;
        }
    },
    get ptOperationName() {
        return this.pos.config.primetech_stock_operation_name || "Type d'opération non défini";
    },
});

patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        const order = this.currentOrder;
        const existingLine = order?.lines.find(
            (line) =>
                line.product_id?.id === product.id &&
                line.price_type === "original" &&
                line.get_discount?.() === 0 &&
                !line.getNote?.() &&
                !line.get_customer_note?.() &&
                !line.refunded_orderline_id &&
                !line.isLotTracked?.() &&
                !line.isPartOfCombo?.()
        );

        if (existingLine) {
            existingLine.set_quantity(existingLine.get_quantity() + 1);
            order.select_orderline(existingLine);
            order.recomputeOrderData();
            return existingLine;
        }

        return super.addProductToOrder(...arguments);
    },

    clearCart() {
        const order = this.currentOrder;
        if (!order || order.is_empty()) {
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Vider le panier ?"),
            body: _t("Tous les articles du panier en cours seront supprimés."),
            confirmLabel: _t("Vider"),
            confirm: () => {
                for (const line of [...order.lines]) {
                    order.removeOrderline(line);
                }
                this.notification.add(_t("Panier vidé."), { type: "success" });
            },
        });
    },
    get ptCashierName() {
        return this.pos.get_cashier?.()?.name || this.pos.user?.name || "Utilisateur POS";
    },
    get ptWarehouseName() {
        return this.pos.config.primetech_stock_location_name || "Entrepôt non défini";
    },
});
