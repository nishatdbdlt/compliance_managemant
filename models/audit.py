from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .standard import SEVERITY_SELECTION, AUDIT_PROGRAM_SELECTION

SEVERITY_WEIGHTS = {"low": 1.0, "medium": 2.0, "high": 3.0, "critical": 4.0}
RESULT_SCORES = {"compliant": 1.0, "partial": 0.5, "non_compliant": 0.0}


class ComplianceAudit(models.Model):
    _name = "compliance.audit"
    _description = "Compliance Audit"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "audit_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(default="New", required=True, copy=False, readonly=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True, tracking=True
    )
    audit_type = fields.Selection([
        ("buyer", "Buyer Audit"), ("internal", "Internal Audit"),
        ("external", "External Audit"), ("certification", "Certification Audit")
    ], default="buyer", required=True, tracking=True)
    standard_id = fields.Many2one("compliance.standard", required=True, tracking=True, check_company=True)
    program_type = fields.Selection(AUDIT_PROGRAM_SELECTION, related="standard_id.program_type", string="Audit Program", store=True, index=True)
    buyer_id = fields.Many2one("compliance.buyer", string="Buyer / Audit Organization", check_company=True)
    factory_id = fields.Many2one("compliance.factory", string="Factory", required=True, tracking=True, check_company=True)
    audit_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    auditor_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True, tracking=True)
    reviewer_id = fields.Many2one("res.users", tracking=True)
    checklist_line_ids = fields.One2many("compliance.audit.line", "audit_id", copy=True)
    finding_ids = fields.One2many("compliance.finding", "audit_id")
    state = fields.Selection([
        ("draft", "Draft"), ("scheduled", "Scheduled"), ("in_progress", "In Progress"),
        ("submitted", "Submitted"), ("reviewed", "Reviewed"), ("closed", "Closed"),
        ("cancelled", "Cancelled")
    ], default="draft", tracking=True, required=True, index=True)
    notes = fields.Html()

    total_items = fields.Integer(compute="_compute_metrics", store=True)
    completed_items = fields.Integer(compute="_compute_metrics", store=True)
    compliant_items = fields.Integer(compute="_compute_metrics", store=True)
    partial_items = fields.Integer(compute="_compute_metrics", store=True)
    noncompliant_items = fields.Integer(compute="_compute_metrics", store=True)
    na_items = fields.Integer(compute="_compute_metrics", store=True)
    open_finding_count = fields.Integer(compute="_compute_metrics", store=True)
    critical_finding_count = fields.Integer(compute="_compute_metrics", store=True)
    compliance_rate = fields.Float(string="Weighted Score %", compute="_compute_metrics", store=True, digits=(5, 2))
    grade = fields.Char(compute="_compute_metrics", store=True)
    result = fields.Selection([
        ("pending", "Pending"), ("pass", "Pass"), ("conditional", "Conditional"), ("fail", "Fail")
    ], compute="_compute_metrics", store=True)

    @api.depends(
        "checklist_line_ids.result", "checklist_line_ids.severity", "checklist_line_ids.weight",
        "finding_ids.state", "finding_ids.severity", "company_id"
    )
    def _compute_metrics(self):
        grade_model = self.env["compliance.grade.rule"]
        for rec in self:
            lines = rec.checklist_line_ids
            applicable = lines.filtered(lambda line: line.result != "na")
            completed = applicable.filtered(lambda line: line.result != "pending")
            rec.total_items = len(applicable)
            rec.completed_items = len(completed)
            rec.compliant_items = len(lines.filtered(lambda line: line.result == "compliant"))
            rec.partial_items = len(lines.filtered(lambda line: line.result == "partial"))
            rec.noncompliant_items = len(lines.filtered(lambda line: line.result == "non_compliant"))
            rec.na_items = len(lines.filtered(lambda line: line.result == "na"))
            rec.open_finding_count = len(rec.finding_ids.filtered(lambda f: f.state != "closed"))
            rec.critical_finding_count = len(rec.finding_ids.filtered(lambda f: f.severity == "critical" and f.state != "closed"))

            earned = 0.0
            possible = 0.0
            for line in completed:
                severity_weight = SEVERITY_WEIGHTS.get(line.severity, 1.0)
                line_weight = max(line.weight or 1.0, 0.0) * severity_weight
                possible += line_weight
                earned += line_weight * RESULT_SCORES.get(line.result, 0.0)
            score = (earned / possible * 100.0) if possible else 0.0
            rec.compliance_rate = score
            rec.grade = grade_model.get_grade_for_score(score, rec.company_id) if completed else False
            if not completed or len(completed) < len(applicable):
                rec.result = "pending"
            elif score >= 90:
                rec.result = "pass"
            elif score >= 70:
                rec.result = "conditional"
            else:
                rec.result = "fail"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("compliance.audit") or "AUD/0001"
        return super().create(vals_list)

    @api.onchange("standard_id")
    def _onchange_standard_id(self):
        if self.standard_id and not self.company_id:
            self.company_id = self.standard_id.company_id

    def action_load_checklist(self):
        self.ensure_one()
        if self.state not in ("draft", "scheduled"):
            raise UserError(_("Checklist can only be loaded before the audit starts."))
        if not self.standard_id:
            raise UserError(_("Select a compliance standard first."))
        existing = self.checklist_line_ids.mapped("checklist_id").ids
        items = self.env["compliance.checklist"].search([
            ("standard_id", "=", self.standard_id.id), ("active", "=", True), ("id", "not in", existing)
        ], order="sequence, id")
        commands = []
        for item in items:
            commands.append((0, 0, {
                "checklist_id": item.id,
                "sequence": item.sequence,
                "name": item.name,
                "requirement": item.requirement,
                "severity": item.severity,
                "weight": item.weight,
                "mandatory": item.mandatory,
            }))
        if commands:
            self.write({"checklist_line_ids": commands})
        return True

    def _require_state(self, allowed, action_label):
        for rec in self:
            if rec.state not in allowed:
                raise UserError(_("%s is not allowed from the current audit state.") % action_label)

    def action_schedule(self):
        self._require_state(("draft",), _("Schedule"))
        for rec in self:
            if not rec.checklist_line_ids:
                raise UserError(_("Load the checklist before scheduling the audit."))
        self.write({"state": "scheduled"})

    def action_start(self):
        self._require_state(("scheduled",), _("Start"))
        self.write({"state": "in_progress"})

    def action_submit(self):
        self._require_state(("in_progress",), _("Submit"))
        for rec in self:
            if not rec.checklist_line_ids:
                raise UserError(_("Load or add checklist items before submitting."))
            pending = rec.checklist_line_ids.filtered(lambda l: l.result == "pending")
            if pending:
                raise UserError(_("Complete every checklist result before submitting."))
            missing_findings = rec.checklist_line_ids.filtered(
                lambda l: l.mandatory and l.result in ("non_compliant", "partial") and not l.finding_id
            )
            if missing_findings:
                raise UserError(_("Create findings for every mandatory Partial or Non-Compliant checklist item."))
        self.write({"state": "submitted"})

    def action_review(self):
        self._require_state(("submitted",), _("Review"))
        self.write({"state": "reviewed", "reviewer_id": self.env.user.id})

    def action_close(self):
        self._require_state(("reviewed",), _("Close"))
        for rec in self:
            if rec.finding_ids.filtered(lambda f: f.state != "closed"):
                raise UserError(_("Close all findings before closing the audit."))
        self.write({"state": "closed"})

    def action_cancel(self):
        self._require_state(("draft", "scheduled", "in_progress"), _("Cancel"))
        self.write({"state": "cancelled"})

    def action_reset_draft(self):
        self._require_state(("cancelled",), _("Reset to Draft"))
        self.write({"state": "draft"})


class ComplianceAuditLine(models.Model):
    _name = "compliance.audit.line"
    _description = "Audit Checklist Line"
    _order = "sequence, id"
    _check_company_auto = True

    sequence = fields.Integer(default=10)
    audit_id = fields.Many2one("compliance.audit", required=True, ondelete="cascade", index=True, check_company=True)
    company_id = fields.Many2one(related="audit_id.company_id", store=True, index=True)
    checklist_id = fields.Many2one("compliance.checklist", ondelete="set null", check_company=True)
    name = fields.Char(required=True)
    requirement = fields.Text()
    severity = fields.Selection(SEVERITY_SELECTION, default="medium", required=True)
    weight = fields.Float(default=1.0, required=True)
    mandatory = fields.Boolean(default=True)
    result = fields.Selection([
        ("pending", "Pending"), ("compliant", "Compliant"),
        ("non_compliant", "Non-Compliant"), ("partial", "Partially Compliant"),
        ("na", "Not Applicable")
    ], default="pending", required=True)
    remarks = fields.Text()
    evidence = fields.Binary(attachment=True)
    evidence_filename = fields.Char()
    finding_id = fields.Many2one("compliance.finding", string="Finding", readonly=True, copy=False)

    @api.constrains("weight")
    def _check_weight(self):
        for rec in self:
            if rec.weight < 0:
                raise ValidationError(_("Checklist weight cannot be negative."))

    def action_create_finding(self):
        for line in self:
            if line.result not in ("non_compliant", "partial"):
                raise UserError(_("Finding can only be created for Non-Compliant or Partial items."))
            if not line.finding_id:
                finding = self.env["compliance.finding"].create({
                    "name": line.name,
                    "audit_id": line.audit_id.id,
                    "audit_line_id": line.id,
                    "severity": line.severity,
                    "description": line.remarks or line.requirement or line.name,
                })
                line.finding_id = finding.id
        return True
