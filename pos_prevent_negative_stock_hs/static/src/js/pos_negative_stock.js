/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

console.log("✅ Vérification finale du stock POS chargée !");

patch(PaymentScreen.prototype, {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
    },

    async validateOrder(isForceValidate) {

        const order = this.pos.get_order();
        const lines = order.get_orderlines();

        const produitsInsuffisants = [];

        for (const line of lines) {

            const product = line.get_product();
            const qtyPanier = line.get_quantity();

            // Ignorer les services
            if (product.type === "service" || product.detailed_type === "service") {
                continue;
            }

            try {

                const stockData = await this.orm.call(
                    "product.product",
                    "read",
                    [[product.id]],
                    { fields: ["qty_available"] }
                );

                const qtyDisponible = stockData?.[0]?.qty_available || 0;

                if (qtyPanier > qtyDisponible) {

                    produitsInsuffisants.push({
                        nom: product.display_name,
                        panier: qtyPanier,
                        stock: qtyDisponible,
                    });

                }

            } catch (error) {

                console.error("❌ Erreur de vérification du stock :", error);

                this.dialog.add(ConfirmationDialog, {
                    title: _t("Erreur de vérification du stock"),
                    body: _t(
                        "Impossible de vérifier le stock pour '%s'. Vérifiez votre connexion.",
                        product.display_name
                    ),
                });

                return;
            }
        }

        // 🚫 Si au moins un produit dépasse le stock
        if (produitsInsuffisants.length > 0) {

            let message = "🚫 Stock insuffisant pour les produits suivants :\n\n";

            produitsInsuffisants.forEach(p => {
                message += `${p.nom}\n`;
                message += `Dans le panier : ${p.panier} | Stock disponible : ${p.stock}\n\n`;
            });

            this.dialog.add(ConfirmationDialog, {
                title: _t("Erreur de stock"),
                body: message,
            });

            return; // ❌ bloque le paiement
        }

        // ✅ Si tout est correct
        return super.validateOrder(...arguments);
    },

});