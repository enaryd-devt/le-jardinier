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
        if (typeof vals.product_id == "number") {
            vals.product_id = this.data.models["product.product"].get(vals.product_id);
        }
        const product = vals.product_id;

        let availableLots = await this.env.services.orm.call(
            "stock.lot",
            "get_available_lots_for_pos_product",
            [],
            { product_id: product.id }
        );

        let selectedLot = null;
        if (this.config.enable_auto_lot_selection &&product.tracking === "serial") {

            let existingOrderline = null;
            let allUsedSerials = [];
            
            // Get all orderlines for this product and collect all used serials
            order.get_orderlines().forEach(line => {
                if (line.product_id.id === product.id) {
                    existingOrderline = line;
                    if (line.pack_lot_ids && line.pack_lot_ids.length) {
                        line.pack_lot_ids.forEach(pl => {
                            allUsedSerials.push(pl.lot_name);
                        });
                    }
                }
            });

            for (let lot of availableLots) {
                if (!allUsedSerials.includes(lot.name) && lot.available_qty > 0) {
                    selectedLot = lot;
                    break;
                }
            }

            if (selectedLot) {
                if (existingOrderline) {                
                    const allLots = [];
                    
                    if (existingOrderline.pack_lot_ids && existingOrderline.pack_lot_ids.length) {
                        existingOrderline.pack_lot_ids.forEach(pl => {
                            allLots.push({ lot_name: pl.lot_name });
                        });
                    }
                    
                    // Add new serial
                    allLots.push({ lot_name: selectedLot.name });
                    
                    
                    existingOrderline.setPackLotLines({
                        modifiedPackLotLines: [],
                        newPackLotLines: allLots,
                        setQuantity: true,
                    });
                    
                    return existingOrderline;
                } else {
                    // First serial for this product - create new orderline
                    const orderline = await super.addLineToOrder(vals, order, opts, false);
                    
                    orderline.setPackLotLines({
                        modifiedPackLotLines: [],
                        newPackLotLines: [{ lot_name: selectedLot.name }],
                        setQuantity: true,
                    });
                    return orderline;
                }
            }
            else {
                this.dialog.add(AlertDialog, {
                    title: _t("No Serial Available"),
                    body: _t("No unused serial number available for this product."),
                });
                return;
            }

        }
        else if (this.config.enable_auto_lot_selection &&product.tracking === "lot") {
            // LOT TRACKING 
            for (let lot of availableLots) {
                let usedQty = 0;
                order.get_orderlines().forEach(line => {
                    if (line.product_id.id === product.id && line.pack_lot_ids && line.pack_lot_ids.length) {
                        line.pack_lot_ids.forEach(pl => {
                            if (pl.lot_name == lot.name) {
                                usedQty += line.qty;
                            }
                        });
                    }
                });

                if (lot.available_qty > usedQty) {
                    selectedLot = lot;
                    break;
                }
            }

            if (selectedLot) {
                const orderline = await super.addLineToOrder(vals, order, opts, false);
                orderline.setPackLotLines({
                    modifiedPackLotLines: [],
                    newPackLotLines: [{ lot_name: selectedLot.name }],
                    setQuantity: true,
                });
                return orderline;
            } else {
                console.warn("No available lot with remaining quantity");
                this.dialog.add(AlertDialog, {
                    title: _t("Not enough stock in lots"),
                    body: _t("The requested quantity exceeds the total available quantity across lots."),
                });
                return;
            }
        }
        await super.addLineToOrder(vals, order, opts, configure);;
    }
});