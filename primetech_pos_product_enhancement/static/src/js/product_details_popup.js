/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * Product Detail Popup (POS)
 * - Affiche un panneau détaillé enrichi sur produit
 * - Utilisable en hover + click
 */

export class ProductDetailsPopup extends Component {
    static template = "primetech_pos_product_enhancement.ProductDetailsPopup";

    setup() {
        this.state = useState({
            visible: false,
            product: null,
            position: { x: 0, y: 0 },
        });

        this.openPopup = this.openPopup.bind(this);
        this.closePopup = this.closePopup.bind(this);

        onMounted(() => {
            document.addEventListener("click", this._onOutsideClick.bind(this));
        });
    }

    get lots() {
    return this.state.product?.pos_lots || [];
    }

    get hasLots() {
        return (this.state.product?.pos_lots || []).length > 0;
    }

    /**
     * Ouvrir popup avec produit sélectionné
     */
    openPopup(product, event) {
        if (!product) return;

        this.state.product = null; // FORCE reset (important POS OWL)

        this.state.product = product;

        this.state.visible = true;

        if (event) {
            this.state.position = {
                x: event.clientX,
                y: event.clientY,
            };
        }
    }

    /**
     * Fermer popup
     */
    closePopup() {
        this.state.visible = false;
        this.state.product = null;
    }

    /**
     * Fermeture si clic hors composant
     */
    _onOutsideClick(ev) {
        const popup = document.querySelector(".pt-product-popup");
        if (popup && !popup.contains(ev.target)) {
            this.closePopup();
        }
    }

    /**
     * Calcul marge
     */
    get margin() {
        const p = this.state.product;
        if (!p) return 0;
        return (p.lst_price || 0) - (p.standard_price || 0);
    }

    /**
     * Stock status color
     */
    get stockColor() {
        const qty = this.state.product?.qty_available || 0;
        if (qty <= 0) return "red";
        if (qty <= 5) return "orange";
        return "green";
    }
        /**
     * Lots sécurisés
     */
    get lots() {
        const p = this.state.product;
        return p?.pos_lots || [];
    }

    /**
     * Vérifie si produit tracké par lot
     */
    get hasLots() {
        return (this.state.product?.pos_lots?.length || 0) > 0;
    }
}

/**
 * Registry (facultatif pour extension future POS actions)
 */
registry.category("pos_screens").add("ProductDetailsPopup", ProductDetailsPopup);