/** @odoo-module **/
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { getDefaultCustomDateRange, getGlobalDateFilter, globalDateFilterPayload, setGlobalDateFilter, subscribeToGlobalDateFilter } from "../services/dashboard_state_service";

export class StockDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.state = useState({ loading: true, ...getGlobalDateFilter(), data: {} });
        onWillStart(() => this.loadDashboard());
        onMounted(() => { this._unsubscribe = subscribeToGlobalDateFilter((filter) => { if (!this.isCurrent(filter)) this.applyGlobalDateFilter(filter); }); setTimeout(() => this.renderCharts(), 100); });
        onWillUnmount(() => this._unsubscribe?.());
    }
    async loadDashboard() { this.state.loading = true; this.state.data = await rpc("/primetech/stock/dashboard", globalDateFilterPayload(this.state)); this.state.loading = false; setTimeout(() => this.renderCharts(), 0); }
    isCurrent(filter) { return ["period", "dateFrom", "dateTo"].every((key) => this.state[key] === filter[key]); }
    async applyGlobalDateFilter(filter) { Object.assign(this.state, filter); await this.loadDashboard(); }
    async onGlobalPeriodChange(ev) { let next = { period: ev.target.value, dateFrom: this.state.dateFrom, dateTo: this.state.dateTo }; if (next.period === "custom" && (!next.dateFrom || !next.dateTo)) next = { ...next, ...getDefaultCustomDateRange() }; Object.assign(this.state, next); setGlobalDateFilter(next); await this.loadDashboard(); }
    async onGlobalDateChange(field, ev) { const next = { period: this.state.period, dateFrom: this.state.dateFrom, dateTo: this.state.dateTo, [field]: ev.target.value }; Object.assign(this.state, next); if (next.dateFrom && next.dateTo && next.dateFrom <= next.dateTo) { setGlobalDateFilter(next); await this.loadDashboard(); } }
    get domain() { return this.state.data.domains || {}; }
    money(value) { return `${Math.round(value || 0).toLocaleString()} FCFA`; }
    pct(value) { return `${Number(value || 0).toFixed(1)}%`; }
    openView(name, resModel, domain = [], views = [[false, "list"], [false, "form"]]) { this.action.doAction({ type: "ir.actions.act_window", name, res_model: resModel, views, view_mode: views.map((view) => view[1]).join(","), domain }); }
    openProducts(extra = []) { this.openView("Produits", "product.product", [...(this.domain.products || []), ...extra]); }
    openLocations(extra = []) { this.openView("Emplacements", "stock.location", [...(this.domain.locations || []), ...extra]); }
    openMoves(extra = []) { this.openView("Mouvements de stock", "stock.move", [...(this.domain.moves || []), ...extra]); }
    openReport(xmlId) { this.action.doAction(xmlId); }
    renderCharts() {
        if (typeof Chart === "undefined") return;
        const rows = this.state.data.period_moves || [];
        this.renderChart("stockMovementsChart", "bar", rows.map((row) => row.label), [{ label: "Entrées", data: rows.map((row) => row.incoming), backgroundColor: "#19b77a", borderRadius: 4 }, { label: "Sorties", data: rows.map((row) => row.outgoing), backgroundColor: "#fb6577", borderRadius: 4 }]);
        const categories = this.state.data.category_stock || [];
        this.renderChart("stockCategoryChart", "doughnut", categories.map((row) => row.name), [{ data: categories.map((row) => row.value), backgroundColor: ["#2878ef", "#ff5b6e", "#a077ed", "#f7bd27", "#16aea7", "#718096"], borderWidth: 0 }]);
        const warehouses = this.state.data.warehouses || [];
        this.renderChart("stockWarehouseChart", "bar", warehouses.map((row) => row.name), [{ label: "Valeur", data: warehouses.map((row) => row.value), backgroundColor: "#2878ef", borderRadius: 4 }]);
        const delta = (this.state.data.incoming_qty || 0) - (this.state.data.outgoing_qty || 0);
        this.renderChart("stockValueChart", "line", rows.map((row) => row.label), [{ label: "Valeur estimée", data: rows.map((row, index) => (this.state.data.stock_value || 0) - (rows.length - index - 1) * delta), borderColor: "#8954e8", backgroundColor: "rgba(137,84,232,.12)", fill: true, tension: .35 }]);
    }
    renderChart(id, type, labels, datasets) { const canvas = document.getElementById(id); if (!canvas) return; const chart = Chart.getChart(canvas); if (chart) chart.destroy(); new Chart(canvas, { type, data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: false, animation: { duration: 450 }, plugins: { legend: { position: "top", labels: { boxWidth: 9, font: { size: 10 } } } }, scales: type === "doughnut" ? {} : { x: { grid: { display: false }, ticks: { font: { size: 9 } } }, y: { beginAtZero: true, grid: { color: "rgba(148,163,184,.15)" }, ticks: { font: { size: 9 }, maxTicksLimit: 4 } } } } }); }
}
StockDashboard.template = "primetech_reporting_center.StockDashboard";
registry.category("actions").add("primetech_stock_dashboard", StockDashboard);
