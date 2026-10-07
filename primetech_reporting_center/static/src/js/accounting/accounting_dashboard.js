/** @odoo-module **/
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { dashboardState, getDefaultCustomDateRange, getGlobalDateFilter, globalDateFilterPayload, setGlobalDateFilter, subscribeToGlobalDateFilter } from "../services/dashboard_state_service";

const ACCOUNTING_FILTER_STATE_KEY = "primetech_reporting_center.accounting_filters";

export class AccountingDashboard extends Component {
    static props = { "*": true };
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const dateFilter = getGlobalDateFilter();
        const savedFilters = dashboardState.load(ACCOUNTING_FILTER_STATE_KEY) || {};
        this.state = useState({ loading: true, dateFilter, filters: { company_id: savedFilters.company_id || "", period: dateFilter.period, comparison: "previous_period" }, data: {} });
        onWillStart(() => this.loadData());
        onMounted(() => {
            this._unsubscribeGlobalDateFilter = subscribeToGlobalDateFilter((filter) => {
                if (!this.isCurrentGlobalDateFilter(filter)) this.applyGlobalDateFilter(filter);
            });
            this.scheduleChartRender();
        });
        onWillUnmount(() => {
            this._unsubscribeGlobalDateFilter?.();
            if (this._chartRenderFrame) cancelAnimationFrame(this._chartRenderFrame);
        });
    }

    async loadData() {
        this.state.loading = true;
        const filters = { ...this.state.filters, ...globalDateFilterPayload(this.state.dateFilter) };
        this.state.data = await this.orm.call("primetech.accounting.dashboard", "get_overview_data", [filters]);
        // Le serveur confirme les bornes calculées, sans écraser les choix visibles
        // de l'utilisateur (société et période) après chaque rechargement.
        this.state.filters = {
            ...(this.state.data.filters || {}),
            company_id: this.state.filters.company_id || "",
            period: this.state.dateFilter.period,
        };
        this.state.loading = false;
        this.scheduleChartRender();
    }

    scheduleChartRender() {
        if (this._chartRenderFrame) cancelAnimationFrame(this._chartRenderFrame);
        this._chartRenderFrame = requestAnimationFrame(() => {
            this._chartRenderFrame = null;
            this.renderCharts();
        });
    }

    async onFilterChange(key, ev) {
        this.state.filters[key] = ev.target.value;
        dashboardState.save(ACCOUNTING_FILTER_STATE_KEY, { company_id: this.state.filters.company_id || "" });
        await this.loadData();
    }

    isCurrentGlobalDateFilter(filter) {
        return ["period", "dateFrom", "dateTo"].every((key) => this.state.dateFilter[key] === filter[key]);
    }

    async applyGlobalDateFilter(filter) {
        this.state.dateFilter = { ...filter };
        this.state.filters.period = filter.period;
        await this.loadData();
    }

    async onGlobalPeriodChange(ev) {
        let next = { ...this.state.dateFilter, period: ev.target.value };
        if (next.period === "custom" && (!next.dateFrom || !next.dateTo)) {
            next = { ...next, ...getDefaultCustomDateRange() };
        }
        this.state.dateFilter = next;
        this.state.filters.period = next.period;
        setGlobalDateFilter(next);
        dashboardState.save(ACCOUNTING_FILTER_STATE_KEY, { company_id: this.state.filters.company_id || "" });
        await this.loadData();
    }

    async selectPeriod(period) {
        await this.onGlobalPeriodChange({ target: { value: period } });
    }

    async onGlobalDateChange(field, ev) {
        const next = { ...this.state.dateFilter, [field]: ev.target.value };
        this.state.dateFilter = next;
        if (next.dateFrom && next.dateTo && next.dateFrom <= next.dateTo) {
            setGlobalDateFilter(next);
            dashboardState.save(ACCOUNTING_FILTER_STATE_KEY, { company_id: this.state.filters.company_id || "" });
            await this.loadData();
        }
    }

    async onCompanyChange(ev) {
        await this.onFilterChange("company_id", ev);
    }

    async onComparisonChange(ev) {
        await this.onFilterChange("comparison", ev);
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

    openInvoices(extraDomain = []) {
        this.openView("Factures clients", "account.move", [...(this.domain.customer_invoices || []), ...extraDomain]);
    }

    openBills(extraDomain = []) {
        this.openView("Factures fournisseurs", "account.move", [...(this.domain.vendor_bills || []), ...extraDomain]);
    }

    openCashMovements(direction = false) {
        const directionDomain = direction === "in" ? [["debit", ">", 0]] : direction === "out" ? [["credit", ">", 0]] : [];
        this.openView("Écritures de trésorerie", "account.move.line", [...(this.domain.cash_movement_lines || []), ...directionDomain]);
    }

    openAccounts(extraDomain = []) {
        this.openView("Comptes", "account.account", [...(this.domain.cash_accounts || []), ...extraDomain]);
    }

    openJournalItems(extraDomain = []) {
        this.openView("Écritures comptables", "account.move.line", [...(this.domain.move_lines || []), ...extraDomain]);
    }

    openPartners(ids = []) {
        this.openView("Clients", "res.partner", ids.length ? [["id", "in", ids]] : []);
    }

    openTrialBalance() {
        this.action.doAction("primetech_reporting_center.action_trial_balance_wizard");
    }

    openAccountingReport(actionXmlId) {
        this.action.doAction(`primetech_reporting_center.${actionXmlId}`);
    }

    renderCharts() {
        if (typeof Chart === "undefined") return;
        const rows = this.state.data.activity_evolution || [];
        this.renderChart("accountingRevenueChart", "line", rows, [
            { label: "Facturation clients", data: rows.map((row) => row.customer_invoicing), borderColor: "#2676ed", backgroundColor: "rgba(38,118,237,.12)", fill: true, tension: .35 },
            { label: "Facturation fournisseurs", data: rows.map((row) => row.supplier_invoicing), borderColor: "#fb5268", backgroundColor: "rgba(251,82,104,.08)", fill: true, tension: .35 },
        ]);
        this.renderChart("accountingFlowChart", "bar", rows, [
            { label: "Encaissements", data: rows.map((row) => row.incoming), backgroundColor: "#19b77a", borderRadius: 4 },
            { label: "Décaissements", data: rows.map((row) => row.outgoing), backgroundColor: "#fb6577", borderRadius: 4 },
        ]);
        const categories = this.state.data.expense_categories || [];
        this.renderChart("accountingExpenseChart", "doughnut", categories, [{ data: categories.map((row) => row.amount), backgroundColor: ["#2878ef", "#ff5b6e", "#a077ed", "#f7bd27", "#16aea7", "#718096"], borderWidth: 0 }], categories.map((row) => row.name));
        this.renderChart("accountingTreasuryChart", "line", rows, [{ label: "Solde de trésorerie", data: rows.map((row) => row.cash), borderColor: "#2878ef", backgroundColor: "rgba(40,120,239,.14)", fill: true, tension: .35 }]);
    }

    renderChart(id, type, rows, datasets, labels = null) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const existing = Chart.getChart(canvas);
        if (existing) existing.destroy();
        new Chart(canvas, { type, data: { labels: labels || rows.map((row) => row.label), datasets }, options: { responsive: true, maintainAspectRatio: false, animation: { duration: 450 }, plugins: { legend: { position: "top", labels: { boxWidth: 9, font: { size: 10 } } } }, scales: type === "doughnut" ? {} : { x: { grid: { display: false }, ticks: { font: { size: 9 } } }, y: { grid: { color: "rgba(148,163,184,.15)" }, ticks: { font: { size: 9 }, maxTicksLimit: 4 } } } } });
    }

    renderTreasuryChart() {
        const canvas = document.getElementById("accountingTreasuryChart");
        if (!canvas) return;
        const existing = Chart.getChart(canvas);
        if (existing) existing.destroy();
        const rows = this.state.data.treasury_evolution || [];
        new Chart(canvas, {
            type: "bar",
            data: {
                labels: rows.map((row) => row.label),
                datasets: [
                    { type: "bar", label: "Encaissements", data: rows.map((row) => row.incoming), backgroundColor: "#60a5fa", borderRadius: 3, borderSkipped: false, barPercentage: .72, categoryPercentage: .72 },
                    { type: "bar", label: "Décaissements", data: rows.map((row) => -(row.outgoing || 0)), backgroundColor: "#fda4af", borderRadius: 3, borderSkipped: false, barPercentage: .72, categoryPercentage: .72 },
                    { type: "line", label: "Solde cumulé", data: rows.map((row) => row.balance), borderColor: "#08965a", backgroundColor: "rgba(8, 150, 90, .11)", fill: true, tension: .28, borderWidth: 2, pointRadius: 0, pointHoverRadius: 3 },
                ],
            },
            options: {
                animation: false,
                parsing: false,
                normalized: true,
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: "index" },
                plugins: { legend: { position: "top", align: "start", labels: { boxWidth: 8, boxHeight: 8, padding: 10, font: { size: 10 } } } },
                scales: {
                    x: { grid: { display: false }, ticks: { autoSkip: true, maxTicksLimit: 8, font: { size: 9 } } },
                    y: { grid: { color: "rgba(148, 163, 184, .18)" }, ticks: { maxTicksLimit: 4, font: { size: 9 } } },
                },
            },
        });
    }

    renderCashChart() {
        const canvas = document.getElementById("accountingCashChart");
        if (!canvas) return;
        const existing = Chart.getChart(canvas);
        if (existing) existing.destroy();
        const rows = this.state.data.cash_accounts || [];
        new Chart(canvas, { type: "doughnut", data: { labels: rows.map((row) => row.name), datasets: [{ data: rows.map((row) => row.amount), backgroundColor: ["#2563eb", "#16a34a", "#f97316", "#f59e0b", "#7c3aed", "#0891b2", "#e11d48", "#64748b"], borderWidth: 0 }] }, options: { animation: false, parsing: false, normalized: true, events: [], responsive: true, maintainAspectRatio: false, cutout: "58%", plugins: { legend: { display: false } } } });
    }

    renderAgeChart() {
        const canvas = document.getElementById("accountingAgeChart");
        if (!canvas) return;
        const existing = Chart.getChart(canvas);
        if (existing) existing.destroy();
        const rows = this.state.data.receivable_aging || [];
        new Chart(canvas, { type: "doughnut", data: { labels: rows.map((row) => row.label), datasets: [{ data: rows.map((row) => row.amount), backgroundColor: ["#2563eb", "#f59e0b", "#ef4444", "#7c3aed"], borderWidth: 0 }] }, options: { animation: false, parsing: false, normalized: true, events: [], responsive: true, maintainAspectRatio: false, cutout: "58%", plugins: { legend: { display: false } } } });
    }
}
AccountingDashboard.template = "primetech_reporting_center.AccountingDashboard";
