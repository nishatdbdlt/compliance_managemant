from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .standard import SEVERITY_SELECTION


class ComplianceFinding(models.Model):
    _name = "compliance.finding"
    _description = "Compliance Finding / Non-Compliance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "deadline, id"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    reference = fields.Char(default="New", readonly=True, copy=False, index=True)
    audit_id = fields.Many2one("compliance.audit", required=True, ondelete="cascade", tracking=True, check_company=True)
    company_id = fields.Many2one(related="audit_id.company_id", store=True, index=True)
    audit_line_id = fields.Many2one("compliance.audit.line", ondelete="set null", check_company=True)
    severity = fields.Selection(SEVERITY_SELECTION, default="medium", required=True, tracking=True)
    description = fields.Text(required=True)
    root_cause = fields.Text()
    corrective_action = fields.Text()
    preventive_action = fields.Text()
    responsible_id = fields.Many2one("hr.employee", tracking=True)
    deadline = fields.Date(tracking=True)
    days_overdue = fields.Integer(compute="_compute_overdue")
    is_overdue = fields.Boolean(compute="_compute_overdue", search="_search_is_overdue")
    evidence = fields.Binary(attachment=True)
    evidence_filename = fields.Char()
    capa_ids = fields.One2many("compliance.capa", "finding_id")
    state = fields.Selection([
        ("open", "Open"), ("analysis", "Root Cause Analysis"),
        ("action", "Action In Progress"), ("verification", "Verification"),
        ("closed", "Closed"), ("reopened", "Reopened")
    ], default="open", required=True, tracking=True, index=True)

    @api.depends("deadline", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.deadline and rec.state != "closed" and rec.deadline < today:
                rec.is_overdue = True
                rec.days_overdue = (today - rec.deadline).days
            else:
                rec.is_overdue = False
                rec.days_overdue = 0

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        domain = [("deadline", "<", today), ("state", "!=", "closed")]
        if (operator in ("=", "==") and value) or (operator == "!=" and not value):
            return domain
        return ["|", "|", ("deadline", ">=", today), ("deadline", "=", False), ("state", "=", "closed")]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", "New") == "New":
                vals["reference"] = self.env["ir.sequence"].next_by_code("compliance.finding") or "FND/0001"
            if not vals.get("deadline"):
                severity = vals.get("severity", "medium")
                days = {"critical": 3, "high": 7, "medium": 14, "low": 30}.get(severity, 14)
                vals["deadline"] = fields.Date.context_today(self) + timedelta(days=days)
        return super().create(vals_list)

    def _require_state(self, allowed, label):
        for rec in self:
            if rec.state not in allowed:
                raise UserError(_("%s is not allowed from the current finding state.") % label)

    def action_analyze(self):
        self._require_state(("open", "reopened"), _("Root Cause Analysis"))
        self.write({"state": "analysis"})

    def action_start_action(self):
        self._require_state(("analysis",), _("Start Action"))
        for rec in self:
            if not rec.root_cause:
                raise UserError(_("Enter the root cause before starting corrective action."))
            if not rec.responsible_id:
                raise UserError(_("Assign a responsible employee before starting corrective action."))
        self.write({"state": "action"})

    def action_verify(self):
        self._require_state(("action",), _("Submit for Verification"))
        for rec in self:
            if not rec.corrective_action:
                raise UserError(_("Enter the corrective action before verification."))
            unfinished = rec.capa_ids.filtered(lambda c: c.state != "done")
            if rec.capa_ids and unfinished:
                raise UserError(_("Complete all CAPA actions before submitting the finding for verification."))
        self.write({"state": "verification"})

    def action_close(self):
        self._require_state(("verification",), _("Close"))
        self.write({"state": "closed"})

    def action_reopen(self):
        self._require_state(("closed", "verification"), _("Reopen"))
        self.write({"state": "reopened"})

    @api.model
    def _cron_overdue_activities(self):
        today = fields.Date.context_today(self)
        records = self.search([("deadline", "<", today), ("state", "!=", "closed"), ("responsible_id.user_id", "!=", False)])
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        model_id = self.env["ir.model"]._get_id(self._name)
        for rec in records:
            user = rec.responsible_id.user_id
            exists = self.env["mail.activity"].search_count([
                ("res_model_id", "=", model_id), ("res_id", "=", rec.id),
                ("activity_type_id", "=", activity_type.id), ("user_id", "=", user.id),
                ("summary", "=", "Overdue compliance finding"),
            ])
            if not exists:
                self.env["mail.activity"].create({
                    "activity_type_id": activity_type.id,
                    "res_model_id": model_id,
                    "res_id": rec.id,
                    "user_id": user.id,
                    "date_deadline": today,
                    "summary": "Overdue compliance finding",
                    "note": _("Finding %s is overdue and requires action.") % rec.reference,
                })


class ComplianceCapa(models.Model):
    _name = "compliance.capa"
    _description = "Corrective / Preventive Action"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "deadline, id"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    reference = fields.Char(default="New", readonly=True, copy=False, index=True)
    finding_id = fields.Many2one("compliance.finding", required=True, ondelete="cascade", tracking=True, check_company=True)
    company_id = fields.Many2one(related="finding_id.company_id", store=True, index=True)
    action_type = fields.Selection([("corrective", "Corrective"), ("preventive", "Preventive")], default="corrective", required=True)
    description = fields.Text(required=True, default="Action details to be completed")
    responsible_id = fields.Many2one("hr.employee", required=True, tracking=True)
    deadline = fields.Date(required=True, tracking=True)
    completion_date = fields.Date(readonly=True)
    evidence = fields.Binary(attachment=True)
    evidence_filename = fields.Char()
    verification_notes = fields.Text()
    state = fields.Selection([
        ("draft", "Draft"), ("in_progress", "In Progress"),
        ("to_verify", "To Verify"), ("done", "Done"), ("reopened", "Reopened")
    ], default="draft", required=True, tracking=True, index=True)
    is_overdue = fields.Boolean(compute="_compute_overdue")

    @api.depends("deadline", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(rec.deadline and rec.deadline < today and rec.state != "done")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", "New") == "New":
                vals["reference"] = self.env["ir.sequence"].next_by_code("compliance.capa") or "CAPA/0001"
            # Inline/import/API creation can omit or explicitly clear Description.
            # Keep it mandatory while always supplying a useful server-side value.
            if not vals.get("description"):
                vals["description"] = vals.get("name") or _("Action details to be completed")
        return super().create(vals_list)

    def write(self, vals):
        if "description" in vals and not vals.get("description"):
            vals = dict(vals)
            vals["description"] = self[:1].name or _("Action details to be completed")
        return super().write(vals)

    def action_start(self):
        for rec in self:
            if rec.state not in ("draft", "reopened"):
                raise UserError(_("Only Draft or Reopened CAPA can be started."))
        self.write({"state": "in_progress"})

    def action_submit(self):
        for rec in self:
            if rec.state != "in_progress":
                raise UserError(_("Only In Progress CAPA can be submitted."))
            if not rec.evidence:
                raise UserError(_("Attach evidence before submitting CAPA for verification."))
        self.write({"state": "to_verify"})

    def action_verify(self):
        for rec in self:
            if rec.state != "to_verify":
                raise UserError(_("Only CAPA waiting for verification can be closed."))
            if not rec.verification_notes:
                raise UserError(_("Enter verification notes before closing CAPA."))
        self.write({"state": "done", "completion_date": fields.Date.context_today(self)})

    def action_reopen(self):
        for rec in self:
            if rec.state != "done":
                raise UserError(_("Only completed CAPA can be reopened."))
        self.write({"state": "reopened", "completion_date": False})
