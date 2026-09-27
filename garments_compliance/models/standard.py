from odoo import fields, models


SEVERITY_SELECTION = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
    ("critical", "Critical"),
]

AUDIT_PROGRAM_SELECTION = [
    ("general", "General / Internal"),
    ("bsci", "amfori BSCI"),
    ("wrap", "WRAP"),
    ("sedex", "SEDEX / SMETA"),
    ("buyer", "Buyer Specific"),
]

CATEGORY_SELECTION = [
    ("labor", "Labor & Human Rights"),
    ("health", "Health & Safety"),
    ("environment", "Environment"),
    ("ethics", "Ethics"),
    ("documentation", "Documentation"),
    ("buyer", "Buyer Specific"),
    ("other", "Other"),
]


class ComplianceStandard(models.Model):
    _name = "compliance.standard"
    _description = "Compliance Standard"
    _order = "name"
    _check_company_auto = True

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    category = fields.Selection(CATEGORY_SELECTION, default="buyer", required=True)
    program_type = fields.Selection(AUDIT_PROGRAM_SELECTION, string="Audit Program", default="buyer", required=True, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    description = fields.Text()
    active = fields.Boolean(default=True)
    checklist_ids = fields.One2many("compliance.checklist", "standard_id")
    checklist_count = fields.Integer(compute="_compute_checklist_count")

    _sql_constraints = [
        ("standard_code_company_uniq", "unique(code, company_id)", "Standard code must be unique per company."),
    ]

    def _compute_checklist_count(self):
        for rec in self:
            rec.checklist_count = len(rec.checklist_ids.filtered("active"))


class ComplianceChecklist(models.Model):
    _name = "compliance.checklist"
    _description = "Compliance Checklist Item"
    _order = "standard_id, sequence, name"
    _check_company_auto = True

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    standard_id = fields.Many2one(
        "compliance.standard", required=True, ondelete="cascade", check_company=True, index=True
    )
    company_id = fields.Many2one(related="standard_id.company_id", store=True, index=True)
    category = fields.Selection(CATEGORY_SELECTION, default="other", required=True)
    requirement = fields.Text(required=True)
    guidance = fields.Text(string="Audit Guidance / Evidence Expected")
    severity = fields.Selection(SEVERITY_SELECTION, default="medium", required=True)
    weight = fields.Float(default=1.0, required=True, help="Additional scoring weight. Severity weight is applied automatically.")
    mandatory = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
