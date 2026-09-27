from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ComplianceLicense(models.Model):
    _name = "compliance.license"
    _description = "Compliance License / Certificate"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "expiry_date, name"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    factory_id = fields.Many2one("compliance.factory", required=True, check_company=True)
    license_type = fields.Selection([
        ("fire", "Fire License"), ("factory", "Factory License"), ("environment", "Environmental Clearance"),
        ("boiler", "Boiler Certificate"), ("electrical", "Electrical Certificate"),
        ("trade", "Trade License"), ("other", "Other")
    ], default="other", required=True)
    license_number = fields.Char(required=True)
    issue_date = fields.Date()
    expiry_date = fields.Date(required=True, tracking=True)
    responsible_id = fields.Many2one("hr.employee", tracking=True)
    status = fields.Selection([
        ("valid", "Valid"), ("expiring", "Expiring Soon"), ("expired", "Expired")
    ], compute="_compute_status", store=False)
    days_to_expiry = fields.Integer(compute="_compute_status")
    attachment = fields.Binary(attachment=True)
    attachment_filename = fields.Char()
    notes = fields.Text()
    active = fields.Boolean(default=True)

    @api.depends("expiry_date")
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.expiry_date:
                rec.status = "valid"
                rec.days_to_expiry = 0
            else:
                rec.days_to_expiry = (rec.expiry_date - today).days
                if rec.expiry_date < today:
                    rec.status = "expired"
                elif rec.expiry_date <= today + timedelta(days=60):
                    rec.status = "expiring"
                else:
                    rec.status = "valid"

    @api.constrains("issue_date", "expiry_date")
    def _check_dates(self):
        for rec in self:
            if rec.issue_date and rec.expiry_date and rec.expiry_date < rec.issue_date:
                raise ValidationError(_("Expiry date cannot be earlier than issue date."))

    @api.model
    def _cron_expiry_activities(self):
        today = fields.Date.context_today(self)
        limit_date = today + timedelta(days=30)
        records = self.search([
            ("active", "=", True), ("expiry_date", ">=", today), ("expiry_date", "<=", limit_date),
            ("responsible_id.user_id", "!=", False)
        ])
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        model_id = self.env["ir.model"]._get_id(self._name)
        for rec in records:
            user = rec.responsible_id.user_id
            summary = "Compliance license expiring soon"
            exists = self.env["mail.activity"].search_count([
                ("res_model_id", "=", model_id), ("res_id", "=", rec.id),
                ("activity_type_id", "=", activity_type.id), ("user_id", "=", user.id), ("summary", "=", summary)
            ])
            if not exists:
                self.env["mail.activity"].create({
                    "activity_type_id": activity_type.id,
                    "res_model_id": model_id,
                    "res_id": rec.id,
                    "user_id": user.id,
                    "date_deadline": rec.expiry_date,
                    "summary": summary,
                    "note": _("%s expires on %s.") % (rec.name, rec.expiry_date),
                })


class ComplianceSafetyInspection(models.Model):
    _name = "compliance.safety.inspection"
    _description = "Safety Inspection"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "inspection_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(default="New", required=True, copy=False, readonly=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    factory_id = fields.Many2one("compliance.factory", required=True, check_company=True, tracking=True)
    inspection_type = fields.Selection([
        ("fire", "Fire Safety"), ("electrical", "Electrical Safety"), ("building", "Building Safety"),
        ("ppe", "PPE / Workplace"), ("chemical", "Chemical Safety"), ("other", "Other")
    ], default="fire", required=True)
    inspection_date = fields.Date(default=fields.Date.context_today, required=True)
    inspector_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    result = fields.Selection([("pass", "Pass"), ("partial", "Partial"), ("fail", "Fail")], default="pass", required=True)
    findings = fields.Text()
    action_owner_id = fields.Many2one("hr.employee")
    due_date = fields.Date()
    evidence = fields.Binary(attachment=True)
    evidence_filename = fields.Char()
    state = fields.Selection([
        ("planned", "Planned"), ("done", "Done"), ("action_required", "Action Required"), ("closed", "Closed")
    ], default="planned", required=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("compliance.safety") or "SAF/0001"
        return super().create(vals_list)

    def action_mark_done(self):
        for rec in self:
            if rec.state != "planned":
                raise UserError(_("Only planned inspections can be completed."))
            if rec.result in ("partial", "fail") and not rec.findings:
                raise UserError(_("Enter findings for Partial or Failed inspections."))
            rec.state = "action_required" if rec.result in ("partial", "fail") else "done"

    def action_close(self):
        for rec in self:
            if rec.state not in ("done", "action_required"):
                raise UserError(_("Inspection must be completed before closing."))
            if rec.state == "action_required" and (not rec.action_owner_id or not rec.due_date):
                raise UserError(_("Assign an action owner and due date before closing an inspection with required action."))
            rec.state = "closed"


class ComplianceTraining(models.Model):
    _name = "compliance.training"
    _description = "Compliance Training"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "training_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    factory_id = fields.Many2one("compliance.factory", required=True, check_company=True)
    training_type = fields.Selection([
        ("safety", "Safety"), ("labor", "Labor Rights"), ("harassment", "Anti-Harassment"),
        ("environment", "Environment"), ("ethics", "Ethics"), ("other", "Other")
    ], default="safety", required=True)
    training_date = fields.Date(default=fields.Date.context_today, required=True)
    trainer = fields.Char()
    employee_ids = fields.Many2many("hr.employee", string="Participants")
    participant_count = fields.Integer(compute="_compute_participant_count", store=True)
    duration_hours = fields.Float(default=1.0)
    notes = fields.Text()
    evidence = fields.Binary(attachment=True)
    evidence_filename = fields.Char()
    state = fields.Selection([("planned", "Planned"), ("done", "Completed"), ("cancelled", "Cancelled")], default="planned", tracking=True)

    @api.depends("employee_ids")
    def _compute_participant_count(self):
        for rec in self:
            rec.participant_count = len(rec.employee_ids)

    def action_done(self):
        for rec in self:
            if rec.state != "planned":
                raise UserError(_("Only planned training can be completed."))
            if not rec.employee_ids:
                raise UserError(_("Add at least one participant before completing training."))
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})


class ComplianceDocument(models.Model):
    _name = "compliance.document"
    _description = "Compliance Document Register"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "review_date, name"
    _check_company_auto = True

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    factory_id = fields.Many2one("compliance.factory", required=True, check_company=True)
    document_type = fields.Selection([
        ("policy", "Policy"), ("procedure", "Procedure"), ("record", "Record"),
        ("certificate", "Certificate"), ("report", "Report"), ("other", "Other")
    ], default="policy", required=True)
    version = fields.Char(default="1.0")
    owner_id = fields.Many2one("hr.employee")
    issue_date = fields.Date()
    review_date = fields.Date()
    state = fields.Selection([("draft", "Draft"), ("active", "Active"), ("obsolete", "Obsolete")], default="draft", tracking=True)
    attachment = fields.Binary(attachment=True)
    attachment_filename = fields.Char()
    notes = fields.Text()

    @api.constrains("issue_date", "review_date")
    def _check_dates(self):
        for rec in self:
            if rec.issue_date and rec.review_date and rec.review_date < rec.issue_date:
                raise ValidationError(_("Review date cannot be earlier than issue date."))


class ComplianceHrCompliance(models.Model):
    _name = "compliance.hr.compliance"
    _description = "HR Compliance Register"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "due_date, id desc"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    factory_id = fields.Many2one("compliance.factory", required=True, check_company=True, tracking=True)
    employee_id = fields.Many2one("hr.employee", string="Employee / Concerned Person", tracking=True)
    compliance_type = fields.Selection([
        ("age", "Minimum Age / Young Worker"),
        ("contract", "Employment Contract"),
        ("working_hours", "Working Hours / Overtime"),
        ("wages", "Wages & Benefits"),
        ("leave", "Leave & Attendance"),
        ("grievance", "Grievance / Harassment"),
        ("discipline", "Disciplinary Practice"),
        ("freedom", "Freedom of Association"),
        ("other", "Other HR Compliance"),
    ], default="contract", required=True, tracking=True)
    requirement = fields.Text(required=True)
    observation = fields.Text()
    responsible_id = fields.Many2one("hr.employee", string="Responsible", tracking=True)
    due_date = fields.Date(tracking=True)
    evidence = fields.Binary(attachment=True)
    evidence_filename = fields.Char()
    state = fields.Selection([
        ("open", "Open"), ("action", "Action Required"), ("compliant", "Compliant"), ("closed", "Closed")
    ], default="open", required=True, tracking=True, index=True)
    is_overdue = fields.Boolean(compute="_compute_is_overdue")

    @api.depends("due_date", "state")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(rec.due_date and rec.due_date < today and rec.state not in ("compliant", "closed"))

    def action_require_action(self):
        for rec in self:
            if not rec.observation:
                raise UserError(_("Enter an observation before marking an HR compliance item as Action Required."))
            rec.state = "action"

    def action_compliant(self):
        self.write({"state": "compliant"})

    def action_close(self):
        for rec in self:
            if rec.state not in ("compliant", "action"):
                raise UserError(_("The HR compliance item must be compliant or under completed action before closing."))
        self.write({"state": "closed"})
