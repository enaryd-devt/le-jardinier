/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getDefaultCustomDateRange, getGlobalDateFilter, globalDateFilterPayload, setGlobalDateFilter, subscribeToGlobalDateFilter } from "../services/dashboard_state_service";

export class SalesOverviewDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loaded: false, ...getGlobalDateFilter(), data: {} });
        onWillStart(async () => this.refresh());
        onMounted(() => {
            this._unsubscribeGlobalDateFilter = subscribeToGlobalDateFilter((filter) => {
                if (!this.isCurrentGlobalDateFilter(filter)) this.applyGlobalDateFilter(filter);
            });
            setTimeout(() => this.renderChart(), 100);
        });
        onWillUnmount(() => this._unsubscribeGlobalDateFilter?.());
    }

    isCurrentGlobalDateFilter(filter) {
        return ["period", "dateFrom", "dateTo"].every((key) => this.state[key] === filter[key]);
    }

    async applyGlobalDateFilter(filter) {
        Object.assign(this.state, filter);
        await this.refresh();
    }

    async onGlobalPeriodChange(ev) {
        let next = { period: ev.target.value, dateFrom: this.state.dateFrom, dateTo: this.state.dateTo };
        if (next.period === "custom" && (!next.dateFrom || !next.dateTo)) {
            next = { ...next, ...getDefaultCustomDateRange() };
        }
        Object.assign(this.state, next);
        setGlobalDateFilter(next);
        await this.refresh();
    }

    async onGlobalDateChange(field, ev) {
        const next = { period: this.state.period, dateFrom: this.state.dateFrom, dateTo: this.state.dateTo, [field]: ev.target.value };
        Object.assign(this.state, next);
        if (next.dateFrom && next.dateTo && next.dateFrom <= next.dateTo) {
            setGlobalDateFilter(next);
            await this.refresh();
        }
    }

    async refresh() {
        this.state.loaded = false;
        this.state.data = await this.orm.call("primetech.sales.overview", "get_dashboard_data", [globalDateFilterPayload(this.state)]);
        this.state.loaded = true;
        setTimeout(() => this.renderChart(), 0);
    }

    get domain() {
        return this.state.data.domains || {};
    }

    money(value) {
        return `${Math.round(value || 0).toLocaleString()} FCFA`;
    }

    pct(value) {
        return `${Number(value || 0).toFixed(1)}%`;
    }

    openView(name, resModel, domain = [], views = [[false, "list"], [false, "form"]]) {
        this.action.doAction({ type: "ir.actions.act_window", name, res_model: resModel, views, view_mode: views.map((view) => view[1]).join(","), domain });
    }

    openOrders(extraDomain = []) {
        this.openView("Commandes clients", "sale.order", [...(this.domain.orders || []), ...extraDomain]);
    }

    openInvoices(extraDomain = []) {
        this.openView("Factures clients", "account.move", [...(this.domain.invoices || []), ...extraDomain]);
    }

    openPartners(ids = []) {
        this.openView("Clients", "res.partner", ids.length ? [["id", "in", ids]] : (this.domain.customers || []));
    }

    openProducts(ids = []) {
        this.openView("Produits vendus", "product.product", ids.length ? [["id", "in", ids]] : (this.domain.products || []));
    }

    openSalespersons(ids = []) {
        this.openView("Commerciaux", "res.users", ids.length ? [["id", "in", ids]] : (this.domain.salespersons || []));
    }

    openReport(actionXmlId) {
        this.action.doAction(`primetech_reporting_center.${actionXmlId}`);
    }

    renderChart() {
        if (!this.state.data.monthly_sales || typeof Chart === "undefined") return;
        const labels = this.state.data.monthly_sales.map((item) => item.month);
        this.renderCanvasChart("salesEvolutionChart", "line", labels, [
            { label: "Chiffre d'affaires", data: this.state.data.monthly_sales.map((item) => item.amount), borderColor: "#2676ed", backgroundColor: "rgba(38,118,237,.12)", fill: true, tension: .35 },
            { label: "Marge brute", data: this.state.data.monthly_sales.map((item) => item.margin || 0), borderColor: "#18b877", backgroundColor: "rgba(24,184,119,.08)", fill: true, tension: .35 },
        ]);
        this.renderCanvasChart("salesOrderChart", "bar", labels, [{ label: "Commandes confirmées", data: this.state.data.monthly_sales.map((item) => item.orders || 0), backgroundColor: "#8b5cf6", borderRadius: 4 }]);
        const categories = this.state.data.category_sales || [];
        this.renderCanvasChart("salesCategoryChart", "doughnut", categories.map((item) => item.name), [{ data: categories.map((item) => item.amount), backgroundColor: ["#2878ef", "#ff5b6e", "#a077ed", "#f7bd27", "#16aea7", "#718096"], borderWidth: 0 }]);
        const channels = this.state.data.sales_channels || [];
        this.renderCanvasChart("salesChannelChart", "doughnut", channels.map((item) => item.name), [{ data: channels.map((item) => item.amount), backgroundColor: ["#2878ef", "#20b879", "#ff8a27", "#8954e8", "#ef6477", "#12aaa5"], borderWidth: 0 }]);
    }

    renderCanvasChart(id, type, labels, datasets) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const existing = Chart.getChart(canvas);
        if (existing) existing.destroy();
        new Chart(canvas, {
            type,
            data: {
                labels,
                datasets,
            },
            options: { responsive: true, maintainAspectRatio: false, animation: { duration: 450 }, plugins: { legend: { position: "top", labels: { boxWidth: 9, font: { size: 10 } } } }, scales: type === "doughnut" ? {} : { x: { grid: { display: false }, ticks: { font: { size: 9 } } }, y: { beginAtZero: true, grid: { color: "rgba(148,163,184,.15)" }, ticks: { font: { size: 9 }, maxTicksLimit: 4 } } } },
        });
    }
}

SalesOverviewDashboard.template = "primetech_reporting_center.SalesOverviewDashboard";
registry.category("actions").add("primetech_sales_overview_dashboard", SalesOverviewDashboard);
