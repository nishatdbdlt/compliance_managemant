from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ComplianceFactory(models.Model):
    _name = "compliance.factory"
    _description = "Compliance Factory"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, copy=False, tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    partner_id = fields.Many2one("res.partner", string="Address / Contact", tracking=True)
    responsible_id = fields.Many2one("hr.employee", string="Compliance Responsible")
    active = fields.Boolean(default=True)
    notes = fields.Text()

    _sql_constraints = [
        ("factory_code_company_uniq", "unique(code, company_id)", "Factory code must be unique per company."),
    ]


class ComplianceBuyer(models.Model):
    _name = "compliance.buyer"
    _description = "Compliance Buyer / Audit Organization"
    _order = "name"
    _check_company_auto = True

    name = fields.Char(required=True)
    code = fields.Char()
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    partner_id = fields.Many2one("res.partner", string="Contact")
    active = fields.Boolean(default=True)
    notes = fields.Text()


class ComplianceGradeRule(models.Model):
    _name = "compliance.grade.rule"
    _description = "Compliance Grade Rule"
    _order = "min_score desc, id"
    _check_company_auto = True

    name = fields.Char(string="Grade", required=True)
    min_score = fields.Float(required=True, digits=(5, 2))
    max_score = fields.Float(required=True, digits=(5, 2), default=100.0)
    description = fields.Char()
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    active = fields.Boolean(default=True)

    @api.constrains("min_score", "max_score")
    def _check_score_range(self):
        for rec in self:
            if rec.min_score < 0 or rec.max_score > 100 or rec.min_score > rec.max_score:
                raise ValidationError(_("Grade range must be between 0 and 100 and minimum cannot exceed maximum."))

    def _refresh_company_audits(self, companies):
        if companies and "compliance.audit" in self.env:
            audits = self.env["compliance.audit"].search([("company_id", "in", companies.ids)])
            if audits:
                audits._compute_metrics()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._refresh_company_audits(records.mapped("company_id"))
        return records

    def write(self, vals):
        companies = self.mapped("company_id")
        result = super().write(vals)
        self._refresh_company_audits(companies | self.mapped("company_id"))
        return result

    def unlink(self):
        companies = self.mapped("company_id")
        result = super().unlink()
        self._refresh_company_audits(companies)
        return result

    @api.model
    def get_grade_for_score(self, score, company=None):
        company = company or self.env.company
        rule = self.search([
            ("company_id", "=", company.id),
            ("active", "=", True),
            ("min_score", "<=", score),
            ("max_score", ">=", score),
        ], order="min_score desc", limit=1)
        if rule:
            return rule.name
        # Safe fallback for companies that do not yet have configured grade rules.
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        return "D"
