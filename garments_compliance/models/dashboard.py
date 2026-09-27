from datetime import timedelta

from odoo import api, fields, models


class ComplianceDashboard(models.AbstractModel):
    _name = "compliance.dashboard"
    _description = "Compliance Dashboard Service"

    @api.model
    def get_dashboard_data(self, filters=None):
        filters = filters or {}
        today = fields.Date.context_today(self)
        factory_id = int(filters.get("factory_id") or 0)
        standard_id = int(filters.get("standard_id") or 0)
        period = filters.get("period") or "365"

        audit_domain = [("state", "!=", "cancelled")]
        if factory_id:
            audit_domain.append(("factory_id", "=", factory_id))
        if standard_id:
            audit_domain.append(("standard_id", "=", standard_id))
        if period != "all":
            try:
                days = max(1, int(period))
            except (TypeError, ValueError):
                days = 365
            audit_domain.append(("audit_date", ">=", today - timedelta(days=days)))

        # Related records use audit_id so dashboard filters stay consistent.
        audits = self.env["compliance.audit"].search(audit_domain)
        audit_ids = audits.ids
        finding_domain = [("audit_id", "in", audit_ids)]
        capa_domain = [("finding_id.audit_id", "in", audit_ids)]

        open_findings = self.env["compliance.finding"].search_count(finding_domain + [("state", "!=", "closed")])
        critical_findings = self.env["compliance.finding"].search_count(
            finding_domain + [("state", "!=", "closed"), ("severity", "=", "critical")]
        )
        overdue_findings = self.env["compliance.finding"].search_count(
            finding_domain + [("state", "!=", "closed"), ("deadline", "<", today)]
        )
        open_capa = self.env["compliance.capa"].search_count(capa_domain + [("state", "!=", "done")])
        overdue_capa = self.env["compliance.capa"].search_count(
            capa_domain + [("state", "!=", "done"), ("deadline", "<", today)]
        )

        scores = audits.filtered(lambda a: a.completed_items > 0).mapped("compliance_rate")
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        completed_audits = len(audits.filtered(lambda a: a.state in ("reviewed", "closed")))
        completion_rate = round((completed_audits / len(audits)) * 100, 1) if audits else 0.0

        grade_counts = {grade: 0 for grade in ("A", "B", "C", "D", "Ungraded")}
        for audit in audits:
            grade = audit.grade if audit.grade in ("A", "B", "C", "D") else "Ungraded"
            grade_counts[grade] += 1
        grade_total = sum(grade_counts.values()) or 1
        grades = [
            {"label": key, "value": value, "pct": round((value / grade_total) * 100, 1)}
            for key, value in grade_counts.items()
        ]

        severity_counts = {key: 0 for key in ("critical", "high", "medium", "low")}
        for finding in self.env["compliance.finding"].search(finding_domain + [("state", "!=", "closed")]):
            if finding.severity in severity_counts:
                severity_counts[finding.severity] += 1
        severity_max = max(severity_counts.values()) if severity_counts else 0
        severities = [
            {
                "key": key,
                "label": key.replace("_", " ").title(),
                "value": value,
                "pct": round((value / severity_max) * 100, 1) if severity_max else 0,
            }
            for key, value in severity_counts.items()
        ]

        capa_states = []
        capa_model = self.env["compliance.capa"]
        state_labels = dict(capa_model._fields["state"].selection)
        capa_records = capa_model.search(capa_domain)
        for key in ("draft", "in_progress", "to_verify", "done", "reopened"):
            value = len(capa_records.filtered(lambda c, k=key: c.state == k))
            capa_states.append({"key": key, "label": state_labels.get(key, key), "value": value})


        # Audit state distribution for the dashboard bar chart.
        audit_state_labels = dict(self.env["compliance.audit"]._fields["state"].selection)
        audit_state_order = [key for key, _label in self.env["compliance.audit"]._fields["state"].selection if key != "cancelled"]
        audit_state_counts = {key: 0 for key in audit_state_order}
        for audit in audits:
            if audit.state in audit_state_counts:
                audit_state_counts[audit.state] += 1
        audit_state_max = max(audit_state_counts.values()) if audit_state_counts else 0
        audit_states = [
            {
                "key": key,
                "label": audit_state_labels.get(key, key.replace("_", " ").title()),
                "value": audit_state_counts[key],
                "pct": round((audit_state_counts[key] / audit_state_max) * 100, 1) if audit_state_max else 0,
            }
            for key in audit_state_order
        ]

        # Standard mix for the dynamic donut chart.
        standard_bucket = {}
        for audit in audits:
            name = audit.standard_id.display_name or "Unspecified"
            standard_bucket[name] = standard_bucket.get(name, 0) + 1
        standard_mix = [
            {"label": name, "value": value}
            for name, value in sorted(standard_bucket.items(), key=lambda item: (-item[1], item[0]))[:6]
        ]

        # 6-month audit trend, based on records already filtered by factory/standard.
        trend = []
        cursor = today.replace(day=1)
        months = []
        for offset in range(5, -1, -1):
            year = cursor.year
            month = cursor.month - offset
            while month <= 0:
                month += 12
                year -= 1
            start = cursor.replace(year=year, month=month, day=1)
            if month == 12:
                end = start.replace(year=year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=month + 1, day=1) - timedelta(days=1)
            months.append((start, end))
        for start, end in months:
            month_audits = audits.filtered(lambda a, s=start, e=end: a.audit_date and s <= a.audit_date <= e)
            month_scores = month_audits.filtered(lambda a: a.completed_items > 0).mapped("compliance_rate")
            trend.append({
                "label": start.strftime("%b"),
                "count": len(month_audits),
                "score": round(sum(month_scores) / len(month_scores), 1) if month_scores else 0.0,
            })
        trend_max = max([item["count"] for item in trend] or [0])
        for item in trend:
            item["height"] = round((item["count"] / trend_max) * 100, 1) if trend_max else 0

        recent_audits = []
        for audit in audits.sorted(key=lambda a: (a.audit_date or fields.Date.from_string("1900-01-01"), a.id), reverse=True)[:6]:
            recent_audits.append({
                "id": audit.id,
                "name": audit.name,
                "factory": audit.factory_id.display_name or "—",
                "standard": audit.standard_id.display_name or "—",
                "date": fields.Date.to_string(audit.audit_date) if audit.audit_date else "",
                "score": round(audit.compliance_rate or 0.0, 1),
                "grade": audit.grade or "—",
                "state": dict(audit._fields["state"].selection).get(audit.state, audit.state),
            })

        recent_findings = []
        finding_records = self.env["compliance.finding"].search(
            finding_domain + [("state", "!=", "closed")], order="deadline asc, id desc", limit=6
        )
        for finding in finding_records:
            recent_findings.append({
                "id": finding.id,
                "reference": finding.reference,
                "name": finding.name,
                "severity": finding.severity,
                "deadline": fields.Date.to_string(finding.deadline) if finding.deadline else "",
                "overdue": bool(finding.deadline and finding.deadline < today),
            })

        license_domain = [("active", "=", True)]
        hr_domain = []
        if factory_id:
            license_domain.append(("factory_id", "=", factory_id))
            hr_domain.append(("factory_id", "=", factory_id))
        expiring_date = today + timedelta(days=60)
        license_attention = self.env["compliance.license"].search_count(
            license_domain + [("expiry_date", "!=", False), ("expiry_date", "<=", expiring_date)]
        )
        hr_open = self.env["compliance.hr.compliance"].search_count(
            hr_domain + [("state", "not in", ["compliant", "closed"])]
        )

        factories = self.env["compliance.factory"].search([("active", "=", True)], order="name")
        standards = self.env["compliance.standard"].search([("active", "=", True)], order="name")

        return {
            "kpi": {
                "audits": len(audits),
                "avg_score": avg_score,
                "completion_rate": completion_rate,
                "open_findings": open_findings,
                "critical_findings": critical_findings,
                "overdue_findings": overdue_findings,
                "open_capa": open_capa,
                "overdue_capa": overdue_capa,
                "license_attention": license_attention,
                "hr_open": hr_open,
            },
            "grades": grades,
            "severities": severities,
            "capa_states": capa_states,
            "audit_states": audit_states,
            "standard_mix": standard_mix,
            "trend": trend,
            "recent_audits": recent_audits,
            "recent_findings": recent_findings,
            "filters": {
                "factories": [{"id": rec.id, "name": rec.display_name} for rec in factories],
                "standards": [{"id": rec.id, "name": rec.display_name} for rec in standards],
            },
            "generated_on": fields.Datetime.to_string(fields.Datetime.now()),
        }
