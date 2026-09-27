/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class ComplianceDashboard extends Component {
    static template = "garments_compliance.ComplianceDashboard";
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({audits:0, openFindings:0, openCapa:0, expiring:0, hrOpen:0, avgScore:0, gradeA:0, gradeB:0, gradeC:0, gradeD:0});
        onWillStart(async () => {
            const limit = new Date();
            limit.setDate(limit.getDate() + 60);
            const limitDate = limit.toISOString().slice(0, 10);
            const [audits, findings, capas, licenses, hr, groups] = await Promise.all([
                this.orm.searchCount("compliance.audit", [["state", "!=", "cancelled"]]),
                this.orm.searchCount("compliance.finding", [["state", "!=", "closed"]]),
                this.orm.searchCount("compliance.capa", [["state", "!=", "done"]]),
                this.orm.searchCount("compliance.license", [["active", "=", true], ["expiry_date", "!=", false], ["expiry_date", "<=", limitDate]]),
                this.orm.searchCount("compliance.hr.compliance", [["state", "not in", ["compliant", "closed"]]]),
                this.orm.readGroup("compliance.audit", [["state", "!=", "cancelled"]], ["compliance_rate:avg", "grade"], ["grade"]),
            ]);
            this.state.audits = audits; this.state.openFindings = findings; this.state.openCapa = capas; this.state.expiring = licenses; this.state.hrOpen = hr;
            let weighted=0, count=0;
            for (const g of groups) { const n=g.__count || 0; weighted += (g.compliance_rate || 0) * n; count += n; const gr=g.grade; if (gr && ["A","B","C","D"].includes(gr)) this.state[`grade${gr}`]=n; }
            this.state.avgScore = count ? (weighted / count).toFixed(2) : "0.00";
        });
    }
    open(model, domain=[]) { this.action.doAction({type:"ir.actions.act_window", name:"Compliance", res_model:model, views:[[false,"list"],[false,"form"]], domain}); }
}
registry.category("actions").add("garments_compliance.dashboard", ComplianceDashboard);
