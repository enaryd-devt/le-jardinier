/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * On ajoute un bouton "Liste de prix" dans le footer du panier,
 * juste à côté du bouton client.
 */
registry.category("pos.CartFooterButton").add("PriceListButton", {
    Component: {
        template: "pos_show_qty.CartFooter.PriceListButton",
        setup() {
            const rpc = useService("rpc");

            const showPriceList = async () => {
                try {
                    await rpc.do_action({
                        type: "ir.actions.act_window",
                        res_model: "product.pricelist",
                        name: "Liste de prix",
                        view_mode: "tree,form",
                        target: "current",
                    });
                } catch (error) {
                    console.error("Erreur ouverture Liste de prix :", error);
                }
            };

            return { showPriceList };
        },
    },
    // On force l'ordre pour qu'il apparaisse juste après le bouton client
    sequence: 11, // bouton client est 10 par défaut
});