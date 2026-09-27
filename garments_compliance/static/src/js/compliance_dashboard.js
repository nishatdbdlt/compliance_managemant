/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ComplianceDashboard extends Component {
    static template = "garments_compliance.ComplianceDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            factoryId: "",
            standardId: "",
            period: "365",
            kpi: {},
            grades: [],
            severities: [],
            capaStates: [],
            auditStates: [],
            standardMix: [],
            trend: [],
            recentAudits: [],
            recentFindings: [],
            factories: [],
            standards: [],
            generatedOn: "",
        });
        onWillStart(() => this.loadData());
    }

    get auditDomain() {
        const domain = [["state", "!=", "cancelled"]];
        if (this.state.factoryId) domain.push(["factory_id", "=", Number(this.state.factoryId)]);
        if (this.state.standardId) domain.push(["standard_id", "=", Number(this.state.standardId)]);
        return domain;
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("compliance.dashboard", "get_dashboard_data", [{
                factory_id: this.state.factoryId || false,
                standard_id: this.state.standardId || false,
                period: this.state.period,
            }]);
            Object.assign(this.state, {
                kpi: data.kpi || {},
                grades: data.grades || [],
                severities: data.severities || [],
                capaStates: data.capa_states || [],
                auditStates: data.audit_states || [],
                standardMix: data.standard_mix || [],
                trend: data.trend || [],
                recentAudits: data.recent_audits || [],
                recentFindings: data.recent_findings || [],
                factories: (data.filters && data.filters.factories) || [],
                standards: (data.filters && data.filters.standards) || [],
                generatedOn: data.generated_on || "",
            });
        } catch (error) {
            this.notification.add("Could not load compliance dashboard data.", { type: "danger" });
            throw error;
        } finally {
            this.state.loading = false;
        }
    }


    isFactorySelected(id) {
        return String(id) === this.state.factoryId;
    }

    isStandardSelected(id) {
        return String(id) === this.state.standardId;
    }

    async onFactoryChange(ev) {
        this.state.factoryId = ev.target.value;
        await this.loadData();
    }

    async onStandardChange(ev) {
        this.state.standardId = ev.target.value;
        await this.loadData();
    }

    async onPeriodChange(ev) {
        this.state.period = ev.target.value;
        await this.loadData();
    }

    async refresh() {
        await this.loadData();
        this.notification.add("Dashboard refreshed", { type: "success" });
    }

    openList(model, domain = [], name = "Compliance") {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain,
            target: "current",
        });
    }

    openAuditList() {
        this.openList("compliance.audit", this.auditDomain, "Audits");
    }

    openFindings(extra = []) {
        const domain = [["state", "!=", "closed"], ...extra];
        if (this.state.factoryId) domain.push(["audit_id.factory_id", "=", Number(this.state.factoryId)]);
        if (this.state.standardId) domain.push(["audit_id.standard_id", "=", Number(this.state.standardId)]);
        this.openList("compliance.finding", domain, "Findings");
    }

    openCapa(extra = []) {
        const domain = [["state", "!=", "done"], ...extra];
        if (this.state.factoryId) domain.push(["finding_id.audit_id.factory_id", "=", Number(this.state.factoryId)]);
        if (this.state.standardId) domain.push(["finding_id.audit_id.standard_id", "=", Number(this.state.standardId)]);
        this.openList("compliance.capa", domain, "CAPA Actions");
    }


    openCapaState(state) {
        const domain = [["state", "=", state]];
        if (this.state.factoryId) domain.push(["finding_id.audit_id.factory_id", "=", Number(this.state.factoryId)]);
        if (this.state.standardId) domain.push(["finding_id.audit_id.standard_id", "=", Number(this.state.standardId)]);
        this.openList("compliance.capa", domain, "CAPA Actions");
    }

    openLicenses() {
        const domain = [["active", "=", true]];
        if (this.state.factoryId) domain.push(["factory_id", "=", Number(this.state.factoryId)]);
        this.openList("compliance.license", domain, "Licenses & Certificates");
    }

    openHr() {
        const domain = [["state", "not in", ["compliant", "closed"]]];
        if (this.state.factoryId) domain.push(["factory_id", "=", Number(this.state.factoryId)]);
        this.openList("compliance.hr.compliance", domain, "HR Compliance");
    }

    openRecord(model, id) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    gradeStyle(item) {
        return `--gc-pct:${Math.max(0, Math.min(100, item.pct || 0))}%`;
    }

    severityStyle(item) {
        return `width:${Math.max(0, Math.min(100, item.pct || 0))}%`;
    }

    trendStyle(item) {
        const h = item.height ? Math.max(8, item.height) : 4;
        return `height:${Math.min(100, h)}%`;
    }

    auditStateStyle(item) {
        return `width:${Math.max(0, Math.min(100, item.pct || 0))}%`;
    }

    severityPieStyle() {
        const values = this.state.severities.map((item) => Number(item.value || 0));
        const total = values.reduce((sum, value) => sum + value, 0);
        if (!total) {
            return "background:#eef1f5";
        }
        const colors = ["#c84b55", "#e07838", "#d2a02f", "#4f8bb7"];
        let cursor = 0;
        const stops = [];
        values.forEach((value, index) => {
            const start = cursor;
            cursor += (value / total) * 100;
            stops.push(`${colors[index % colors.length]} ${start}% ${cursor}%`);
        });
        return `background:conic-gradient(${stops.join(",")})`;
    }

    standardMixStyle() {
        const values = this.state.standardMix.map((item) => Number(item.value || 0));
        const total = values.reduce((sum, value) => sum + value, 0);
        if (!total) {
            return "background:#eef1f5";
        }
        const colors = ["#6f42c1", "#16856b", "#4f8bb7", "#d2a02f", "#e07838", "#7b8798"];
        let cursor = 0;
        const stops = [];
        values.forEach((value, index) => {
            const start = cursor;
            cursor += (value / total) * 100;
            stops.push(`${colors[index % colors.length]} ${start}% ${cursor}%`);
        });
        return `background:conic-gradient(${stops.join(",")})`;
    }

    mixDotClass(index) {
        return `o_gc_mix_dot o_gc_mix_${index % 6}`;
    }
}

registry.category("actions").add("garments_compliance.dashboard", ComplianceDashboard);
