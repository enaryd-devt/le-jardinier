/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

let activePos;
// Group rapid changes (quantity button presses, barcode scans, etc.) in one
// request while keeping the update perceptibly instantaneous for other POSes.
const SYNC_DELAY = 350;
const RETRY_DELAY = 100;

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        activePos = this;
        this._primetechOrderSyncTimers = new Map();
        this._primetechOrderSyncState = new Map();
        this.data.connectWebSocket(
            "PRIMETECH_ORDER_SYNC",
            this._primetechReceiveLightOrderSync.bind(this)
        );
    },

    _primetechScheduleLightOrderSync(order) {
        if (!order || order.finalized || this.data.network.offline) {
            return;
        }
        const key = order.uuid;
        let state = this._primetechOrderSyncState.get(key);
        if (!state) {
            state = { revision: 0, syncing: false };
            this._primetechOrderSyncState.set(key, state);
        }
        state.revision += 1;
        window.clearTimeout(this._primetechOrderSyncTimers.get(key));
        this._primetechOrderSyncTimers.set(
            key,
            window.setTimeout(async () => {
                this._primetechOrderSyncTimers.delete(key);
                // A change made while its previous request is in flight must
                // be sent afterwards.  Without this guard, syncAllOrders()
                // ignores the second request because the order is already
                // being synchronised and that last change can be lost.
                if (state.syncing) {
                    this._primetechOrderSyncTimers.set(
                        key,
                        window.setTimeout(
                            () => this._primetechScheduleLightOrderSync(order),
                            RETRY_DELAY
                        )
                    );
                    return;
                }

                const revision = state.revision;
                state.syncing = true;
                try {
                    await this.syncAllOrders({
                        orders: [order],
                        context: { primetech_light_order_sync: true },
                    });
                } catch (error) {
                    console.warn("PrimeTech POS lightweight order sync", error);
                } finally {
                    state.syncing = false;
                    if (state.revision !== revision && !order.finalized) {
                        this._primetechScheduleLightOrderSync(order);
                    }
                }
            }, SYNC_DELAY)
        );
    },

    async _primetechReceiveLightOrderSync(data) {
        const isOrigin =
            data.origin_session_id === this.session.id &&
            Number(data.login_number) === Number(odoo.login_number);
        if (isOrigin || !data.records) {
            return;
        }
        const records = await this.data.missingRecursive(data.records);
        this.models.loadData(records, [], false);
    },
});

patch(PosOrderline.prototype, {
    setDirty() {
        const result = super.setDirty(...arguments);
        activePos?._primetechScheduleLightOrderSync(this.order_id);
        return result;
    },
});

patch(PosOrder.prototype, {
    setDirty() {
        const result = super.setDirty(...arguments);
        // Covers order-level edits such as customer, fiscal position, note,
        // pricelist or global discount, which do not always dirty a line.
        activePos?._primetechScheduleLightOrderSync(this);
        return result;
    },

    removeOrderline(line) {
        const result = super.removeOrderline(...arguments);
        activePos?._primetechScheduleLightOrderSync(this);
        return result;
    },
});
