/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class PrimetechTaxDashboard extends Component {
    static template = "primetech_tax_automation.TaxDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dashboardRef = useRef("dashboardRoot");
        this.salesChartRef = useRef("salesChart");
        this.storageKey = "primetech_tax_dashboard_state_v1";
        const restoredState = this.readStoredState();
        const allowedPeriods = ["month", "quarter", "semester", "year", "custom"];
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        this.state = useState({
            loading: true,
            data: false,
            period: allowedPeriods.includes(restoredState.period) ? restoredState.period : "month",
            dateFrom: restoredState.dateFrom || this.toISO(firstDay),
            dateTo: restoredState.dateTo || this.toISO(lastDay),
            salesDetail: {
                open: false,
                loading: false,
                label: "",
                rows: [],
                total: 0,
            },
        });
        this.refreshTimer = false;
        this.refreshInterval = 0;
        this.dateRefreshTimer = false;
        this.loadSequence = 0;
        this.scrollContainer = false;
        this.scrollEventTarget = false;
        this.scrollSaveFrame = false;
        this.initialScrollTop = Math.max(Number(restoredState.scrollTop || 0), 0);
        this.initialChartScrollLeft = Math.max(Number(restoredState.chartScrollLeft || 0), 0);
        this.isNavigating = false;
        this.onDashboardScroll = () => {
            if (this.isNavigating || this.scrollSaveFrame) {
                return;
            }
            this.scrollSaveFrame = window.requestAnimationFrame(() => {
                this.scrollSaveFrame = false;
                if (!this.isNavigating) {
                    this.persistDashboardState();
                }
            });
        };
        onWillStart(() => this.loadDashboard());
        onMounted(() => {
            this.scrollContainer = this.findScrollContainer();
            this.scrollEventTarget = this.scrollContainer === document.scrollingElement
                ? window
                : this.scrollContainer;
            this.scrollEventTarget?.addEventListener("scroll", this.onDashboardScroll, { passive: true });
            this.salesChartRef.el?.addEventListener("scroll", this.onDashboardScroll, { passive: true });
            window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
                this.setScrollTop(this.initialScrollTop);
                if (this.salesChartRef.el) {
                    this.salesChartRef.el.scrollLeft = this.initialChartScrollLeft;
                }
            }));
        });
        onWillUnmount(() => {
            window.clearInterval(this.refreshTimer);
            window.clearTimeout(this.dateRefreshTimer);
            window.cancelAnimationFrame(this.scrollSaveFrame);
            this.scrollEventTarget?.removeEventListener("scroll", this.onDashboardScroll);
            this.salesChartRef.el?.removeEventListener("scroll", this.onDashboardScroll);
            if (!this.isNavigating) {
                this.persistDashboardState();
            }
        });
    }

    readStoredState() {
        try {
            return JSON.parse(window.sessionStorage.getItem(this.storageKey) || "{}") || {};
        } catch {
            return {};
        }
    }

    findScrollContainer() {
        let element = this.dashboardRef.el?.parentElement;
        let contentOverflow = false;
        while (element && element !== document.body) {
            const overflowY = window.getComputedStyle(element).overflowY;
            if (overflowY === "auto" || overflowY === "scroll") {
                return element;
            }
            if (!contentOverflow && element.scrollHeight > element.clientHeight) {
                contentOverflow = element;
            }
            element = element.parentElement;
        }
        return contentOverflow || document.scrollingElement;
    }

    getScrollTop() {
        if (!this.scrollContainer || this.scrollContainer === document.scrollingElement) {
            return window.scrollY || document.documentElement.scrollTop || 0;
        }
        return this.scrollContainer.scrollTop || 0;
    }

    setScrollTop(value) {
        if (!this.scrollContainer || this.scrollContainer === document.scrollingElement) {
            window.scrollTo({ top: value, left: 0, behavior: "auto" });
        } else {
            this.scrollContainer.scrollTop = value;
        }
    }

    persistDashboardState() {
        try {
            window.sessionStorage.setItem(this.storageKey, JSON.stringify({
                period: this.state.period,
                dateFrom: this.state.dateFrom,
                dateTo: this.state.dateTo,
                scrollTop: Math.round(this.getScrollTop()),
                chartScrollLeft: Math.round(this.salesChartRef.el?.scrollLeft || 0),
            }));
        } catch {
            // Le tableau reste fonctionnel si le stockage du navigateur est désactivé.
        }
    }

    toISO(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    setPresetRange(period) {
        const today = new Date();
        let firstDay;
        let lastDay;
        if (period === "month") {
            firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        } else if (period === "quarter") {
            const firstMonth = Math.floor(today.getMonth() / 3) * 3;
            firstDay = new Date(today.getFullYear(), firstMonth, 1);
            lastDay = new Date(today.getFullYear(), firstMonth + 3, 0);
        } else if (period === "semester") {
            const firstMonth = today.getMonth() < 6 ? 0 : 6;
            firstDay = new Date(today.getFullYear(), firstMonth, 1);
            lastDay = new Date(today.getFullYear(), firstMonth + 6, 0);
        } else {
            firstDay = new Date(today.getFullYear(), 0, 1);
            lastDay = new Date(today.getFullYear(), 12, 0);
        }
        this.state.dateFrom = this.toISO(firstDay);
        this.state.dateTo = this.toISO(lastDay);
    }

    async loadDashboard(silent = false) {
        const sequence = ++this.loadSequence;
        if (!silent) {
            this.state.loading = true;
        }
        try {
            const data = await this.orm.call(
                "primetech.tax.dashboard",
                "get_dashboard_data",
                [this.state.dateFrom, this.state.dateTo, this.state.period]
            );
            if (sequence !== this.loadSequence) {
                return;
            }
            this.state.data = data;
            this.scheduleRefresh();
        } catch (error) {
            if (sequence === this.loadSequence) {
                this.notification.add(error.message || "Impossible de charger le tableau de bord fiscal.", {
                    type: "danger",
                });
            }
        } finally {
            if (sequence === this.loadSequence) {
                this.state.loading = false;
            }
        }
    }

    scheduleRefresh() {
        if (!this.state.data) {
            return;
        }
        const interval = Math.max(Number(this.state.data.refresh_interval || 60) * 1000, 30000);
        if (interval === this.refreshInterval && this.refreshTimer) {
            return;
        }
        window.clearInterval(this.refreshTimer);
        this.refreshInterval = interval;
        this.refreshTimer = window.setInterval(() => this.loadDashboard(true), interval);
    }

    onPeriodChange(event) {
        this.state.period = event.target.value;
        this.resetChartScroll();
        if (this.state.period !== "custom") {
            this.setPresetRange(this.state.period);
            this.loadDashboard();
        }
        this.persistDashboardState();
    }

    onDateFromChange(event) {
        this.state.dateFrom = event.target.value;
        this.resetChartScroll();
        this.persistDashboardState();
        this.scheduleDateRefresh();
    }

    onDateToChange(event) {
        this.state.dateTo = event.target.value;
        this.resetChartScroll();
        this.persistDashboardState();
        this.scheduleDateRefresh();
    }

    scheduleDateRefresh() {
        window.clearTimeout(this.dateRefreshTimer);
        this.dateRefreshTimer = window.setTimeout(() => {
            if (this.state.dateFrom && this.state.dateTo && this.state.dateFrom <= this.state.dateTo) {
                this.loadDashboard();
            }
        }, 200);
    }

    resetChartScroll() {
        this.initialChartScrollLeft = 0;
        if (this.salesChartRef.el) {
            this.salesChartRef.el.scrollLeft = 0;
        }
    }

    formatDate(value) {
        if (!value) {
            return "";
        }
        const [year, month, day] = value.split("-");
        return `${day}/${month}/${year}`;
    }

    format(value) {
        const currency = this.state.data && this.state.data.currency ? this.state.data.currency : "XAF";
        return new Intl.NumberFormat(undefined, {
            style: "currency",
            currency,
            maximumFractionDigits: 0,
        }).format(value || 0);
    }

    barHeight(value) {
        const timeline = (this.state.data && this.state.data.timeline) || [];
        const maximum = Math.max(...timeline.map((point) => Math.abs(point.value)), 1);
        return Math.max(5, Math.round((Math.abs(value) / maximum) * 100));
    }

    percentage(value) {
        return `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} %`;
    }

    scoreAngle(value) {
        return `${Math.min(100, Math.max(0, Number(value || 0)))}%`;
    }

    sectionWidth(section) {
        const maximum = this.state.data?.analysis?.section_maximum || 1;
        return Math.max(4, Math.round((Number(section.amount || 0) / maximum) * 100));
    }

    openAction(model, domain, name, resId = false) {
        this.persistDashboardState();
        this.isNavigating = true;
        const action = {
            type: "ir.actions.act_window",
            name,
            res_model: model,
            // Actions produced by the server contain `views`.  Provide the
            // same normalized form here because the web client preprocesses
            // this attribute before opening a client-side action.
            views: resId ? [[false, "form"]] : [[false, "list"], [false, "form"]],
            domain,
            target: "current",
        };
        if (resId) {
            action.res_id = resId;
        }
        this.action.doAction(action);
    }

    openDeclarations(resId = false) {
        // A direct Owl click passes the browser event as the first argument;
        // only an explicit numeric identifier must open a form record.
        if (!Number.isInteger(resId)) {
            resId = false;
        }
        this.openAction("primetech.dgi.tva.ir.declaration", [], "Déclarations DGI TVA/IR", resId);
    }

    openDeclarationsByState(state) {
        const domain = this.declarationDomain();
        domain.push(["state", "=", state]);
        this.openAction("primetech.dgi.tva.ir.declaration", domain, "Déclarations DGI TVA/IR");
    }

    declarationDomain() {
        return [
            ["date_from", "<=", this.state.dateTo],
            ["date_to", ">=", this.state.dateFrom],
            ["state", "!=", "cancelled"],
        ];
    }

    openTaxBase() {
        this.openAction("primetech.dgi.tva.ir.declaration", this.declarationDomain(), "Bases fiscales");
    }

    openDueDeclarations() {
        const domain = this.declarationDomain();
        domain.push(["state", "!=", "filed"]);
        this.openAction("primetech.dgi.tva.ir.declaration", domain, "Déclarations à payer");
    }

    openPayments(paymentType = false) {
        const domain = [
            ["state", "=", "paid"],
            ["journal_id.type", "in", ["cash", "bank"]],
            ["date", ">=", this.state.dateFrom],
            ["date", "<=", this.state.dateTo],
        ];
        if (paymentType) {
            domain.push(["payment_type", "=", paymentType]);
        }
        this.openAction("account.payment", domain, paymentType === "outbound" ? "Décaissements" : paymentType === "inbound" ? "Encaissements" : "Règlements");
    }

    openPayroll() {
        if (this.state.data.payroll_status !== "available") {
            const message = this.state.data.payroll_status === "restricted"
                ? "Votre profil ne dispose pas de l’accès aux bulletins de paie."
                : "Le module Payroll n’est pas installé.";
            this.notification.add(message, { type: "warning" });
            return;
        }
        this.openAction("hr.payslip", [
            ["state", "=", "done"],
            ["date_from", "<=", this.state.dateTo],
            ["date_to", ">=", this.state.dateFrom],
        ], "Bulletins de paie validés");
    }

    async openSalesBand(point) {
        this.state.salesDetail.open = true;
        this.state.salesDetail.loading = true;
        this.state.salesDetail.label = point.label || `${this.formatDate(point.date_from)} – ${this.formatDate(point.date_to)}`;
        this.state.salesDetail.rows = [];
        try {
            const detail = await this.orm.call(
                "primetech.tax.dashboard",
                "get_sales_detail",
                [point.date_from, point.date_to]
            );
            this.state.salesDetail.rows = detail.rows;
            this.state.salesDetail.total = detail.total;
        } catch (error) {
            this.state.salesDetail.open = false;
            this.notification.add(error.message || "Impossible de charger le détail des ventes.", { type: "danger" });
        } finally {
            this.state.salesDetail.loading = false;
        }
    }

    openAllSales() {
        return this.openSalesBand({
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            label: `${this.formatDate(this.state.dateFrom)} – ${this.formatDate(this.state.dateTo)}`,
        });
    }

    closeSalesDetail() {
        this.state.salesDetail.open = false;
    }

    openSaleRecord(row) {
        this.openAction(row.model, [], row.reference || "Vente", row.res_id);
    }
}

registry.category("actions").add("primetech_tax_dashboard", PrimetechTaxDashboard);
