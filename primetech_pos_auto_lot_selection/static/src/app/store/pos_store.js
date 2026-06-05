/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {

        if (!this.config.enable_auto_lot_selection) {
            return await super.addLineToOrder(vals, order, opts, configure);
        }

        configure = false;

        // ==============================
        // NORMALISATION QUANTITÉ
        // ==============================
        const requestedQty = Number(vals.qty || 1);

        if (requestedQty <= 0) {
            this.dialog.add(AlertDialog, {
                title: _t("Quantité invalide"),
                body: _t("La quantité doit être supérieure à 0."),
            });
            return;
        }

        // ==============================
        // PRODUIT
        // ==============================
        if (typeof vals.product_id === "number") {
            vals.product_id =
                this.data.models["product.product"].get(vals.product_id);
                console.log("PRODUCT", product);
                console.log("ALLOCATIONS", allocations);
                console.log("REQUESTED QTY", requestedQty);
        }

        const product = vals.product_id;
        const usedQty = getUsedQty(order, product.id);

        const [res] = await this.env.services.orm.read(
            "product.product",
            [product.id],
            ["qty_available"]
        );

        const availableQty = res.qty_available;

        // ==============================
        // GLOBAL STOCK CHECK (ANTI NEGATIF)
        // ==============================
        if (availableQty - usedQty < requestedQty) {

            this.dialog.add(AlertDialog, {
                title: _t("Stock insuffisant"),
                body: _t("Quantité insuffisante pour la vente."),
            });

            return;
        }

        function getUsedQty(order, productId) {
            let used = 0;

            order.get_orderlines().forEach((line) => {
                if (line.product_id.id === productId) {
                    used += line.qty;
                }
            });

            return used;
        }

        

        // PRODUITS SANS TRACKING → bypass FEFO
        const hasTracking = product.tracking === "lot" || product.tracking === "serial";
        if (!hasTracking) {
            return await super.addLineToOrder(
                { ...vals, qty: requestedQty },
                order,
                opts,
                configure
            );
        }

        // ==============================
        // FEFO LOTS
        // ==============================
        let allocations = await this.env.services.orm.call(
            "stock.lot",
            "allocate_fefo_lots",
            [],
            {
                product_id: product.id,
                requested_qty: requestedQty,
            }
        ) || [];

        if (product.tracking !== "none") {
            allocations = await this.env.services.orm.call(
                "stock.lot",
                "allocate_fefo_lots",
                [],
                {
                    product_id: product.id,
                    requested_qty: requestedQty,
                }
            );
        }

        // ==============================
        // FALLBACK (SANS LOTS)
        // ==============================
        if (
            product.tracking === "lot" &&
            allocations.length === 0
        ) {
            const [res] = await this.env.services.orm.read(
                "product.product",
                [product.id],
                ["qty_available"]
            );

            const availableQty = res.qty_available;

            if (availableQty < requestedQty) {
                this.dialog.add(AlertDialog, {
                    title: _t("Stock insuffisant"),
                    body: _t("Quantité insuffisante pour la vente."),
                });
                return;
            }

            return await super.addLineToOrder(
                { ...vals, qty: requestedQty },
                order,
                opts,
                false
            );
        }

        // ==============================
        // SERIAL TRACKING
        // ==============================
        if (product.tracking === "serial") {

            let existingOrderline = null;
            let allUsedSerials = [];

            order.get_orderlines().forEach((line) => {
                if (line.product_id.id === product.id) {
                    existingOrderline = line;

                    if (line.pack_lot_ids?.length) {
                        line.pack_lot_ids.forEach((pl) => {
                            allUsedSerials.push(pl.lot_name);
                        });
                    }
                }
            });

            let selectedLot = null;

            for (let lot of allocations) {
                if (
                    !allUsedSerials.includes(lot.name) &&
                    lot.available_qty > 0
                ) {
                    selectedLot = lot;
                    break;
                }
            }

            if (!selectedLot) {
                this.dialog.add(AlertDialog, {
                    title: _t("No Serial Available"),
                    body: _t("No unused serial number available for this product."),
                });
                return;
            }

            if (existingOrderline) {

                const allLots = [];

                if (existingOrderline.pack_lot_ids?.length) {
                    existingOrderline.pack_lot_ids.forEach((pl) => {
                        allLots.push({ lot_name: pl.lot_name });
                    });
                }

                allLots.push({ lot_name: selectedLot.name });

                existingOrderline.setPackLotLines({
                    modifiedPackLotLines: [],
                    newPackLotLines: allLots,
                    setQuantity: true,
                });

                return existingOrderline;
            }

            const orderline = await super.addLineToOrder(
                { ...vals, qty: 1 },
                order,
                opts,
                false
            );

            orderline.setPackLotLines({
                modifiedPackLotLines: [],
                newPackLotLines: [{ lot_name: selectedLot.name }],
                setQuantity: true,
            });

            return orderline;
        }

        // ==============================
        // LOT TRACKING (FEFO)
        // ==============================
        else if (product.tracking === "lot") {

            let remainingQty = requestedQty;
            const allocatedLots = [];

            for (let lot of allocations) {

                if (remainingQty <= 0) break;

                let usedQty = 0;

                order.get_orderlines().forEach((line) => {
                    if (
                        line.product_id.id === product.id &&
                        line.pack_lot_ids?.length
                    ) {
                        line.pack_lot_ids.forEach((pl) => {
                            if (pl.lot_name === lot.name) {
                                usedQty += line.qty;
                            }
                        });
                    }
                });

                const remainingLotQty = lot.available_qty - usedQty;

                if (remainingLotQty <= 0) continue;

                const qtyToTake = Math.min(
                    remainingLotQty,
                    remainingQty
                );

                allocatedLots.push({
                    lot_name: lot.name,
                    qty: qtyToTake,
                });

                remainingQty -= qtyToTake;
            }

            if (remainingQty > 0) {
                this.dialog.add(AlertDialog, {
                    title: _t("Stock insuffisant"),
                    body: _t("Quantité insuffisante pour la vente."),
                });
                return;
            }

            let firstLine = null;

            for (let alloc of allocatedLots) {

                const orderline = await super.addLineToOrder(
                    {
                        ...vals,
                        qty: alloc.qty,
                    },
                    order,
                    opts,
                    false
                );

                orderline.setPackLotLines({
                    modifiedPackLotLines: [],
                    newPackLotLines: [
                        { lot_name: alloc.lot_name },
                    ],
                    setQuantity: true,
                });

                if (!firstLine) {
                    firstLine = orderline;
                }
            }

            return firstLine;
        }

        // ==============================
        // PRODUIT SANS TRACKING
        // ==============================
        return await super.addLineToOrder(
            { ...vals, qty: requestedQty },
            order,
            opts,
            configure
        );
    },
});