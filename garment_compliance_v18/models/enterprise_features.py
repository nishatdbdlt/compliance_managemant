
from datetime import timedelta
from odoo import api, fields, models, _


class GarmentComplianceVendor(models.Model):
    _name = 'garment.compliance.vendor'
    _description = 'Vendor / Subcontractor Compliance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'risk_level desc, name'

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Related Contact')
    vendor_type = fields.Selection([
        ('supplier', 'Supplier'), ('subcontractor', 'Subcontractor'),
        ('waste', 'Waste Vendor'), ('chemical', 'Chemical Supplier'),
        ('service', 'Service Provider'), ('other', 'Other')
    ], default='supplier', required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    responsible_id = fields.Many2one('res.users', string='Compliance Owner', tracking=True)
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending Review'), ('approved', 'Approved'),
        ('conditional', 'Conditionally Approved'), ('blocked', 'Blocked')
    ], default='draft', tracking=True)
    risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')
    ], default='medium', tracking=True)
    last_audit_date = fields.Date()
    next_audit_date = fields.Date(index=True)
    certificate_expiry = fields.Date(index=True)
    score = fields.Float(digits=(16, 2))
    scope = fields.Text()
    notes = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment', string='Compliance Documents')

    def action_submit(self): self.write({'approval_status': 'pending'})
    def action_approve(self): self.write({'approval_status': 'approved'})
    def action_block(self): self.write({'approval_status': 'blocked'})

    @api.model
    def _cron_vendor_due(self):
        today = fields.Date.context_today(self)
        warning = fields.Date.add(today, days=30)
        for rec in self.search([
            '|', ('next_audit_date', '!=', False), ('certificate_expiry', '!=', False),
            ('responsible_id', '!=', False)
        ]):
            due_dates = [d for d in (rec.next_audit_date, rec.certificate_expiry) if d]
            due = min(due_dates) if due_dates else False
            if due and due <= warning:
                exists = self.env['mail.activity'].search_count([
                    ('res_model', '=', self._name), ('res_id', '=', rec.id),
                    ('user_id', '=', rec.responsible_id.id), ('summary', '=', _('Vendor compliance due'))
                ])
                if not exists:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo', user_id=rec.responsible_id.id,
                        date_deadline=due, summary=_('Vendor compliance due'),
                        note=_('Vendor audit/certificate needs review.')
                    )


class GarmentComplianceDocument(models.Model):
    _name = 'garment.compliance.document'
    _description = 'Controlled Compliance Document / SOP'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code, version desc'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    document_type = fields.Selection([
        ('policy', 'Policy'), ('sop', 'SOP'), ('procedure', 'Procedure'),
        ('form', 'Form'), ('manual', 'Manual'), ('buyer', 'Buyer Code / Requirement'),
        ('legal', 'Legal Document'), ('other', 'Other')
    ], default='sop', required=True)
    version = fields.Char(required=True, default='1.0', tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    owner_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, tracking=True)
    department_id = fields.Many2one('hr.department')
    effective_date = fields.Date()
    review_date = fields.Date(index=True)
    supersedes_id = fields.Many2one('garment.compliance.document', string='Supersedes')
    state = fields.Selection([
        ('draft', 'Draft'), ('review', 'Under Review'), ('approved', 'Approved'),
        ('obsolete', 'Obsolete')
    ], default='draft', tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Files')
    notes = fields.Html()

    def action_review(self): self.write({'state': 'review'})
    def action_approve(self):
        for rec in self:
            if rec.supersedes_id and rec.supersedes_id.state != 'obsolete':
                rec.supersedes_id.state = 'obsolete'
            rec.state = 'approved'
            if not rec.effective_date:
                rec.effective_date = fields.Date.context_today(rec)
    def action_obsolete(self): self.write({'state': 'obsolete'})

    @api.model
    def _cron_document_review(self):
        today = fields.Date.context_today(self)
        warning = fields.Date.add(today, days=30)
        for rec in self.search([
            ('state', '=', 'approved'), ('review_date', '!=', False),
            ('review_date', '<=', warning), ('owner_id', '!=', False)
        ]):
            exists = self.env['mail.activity'].search_count([
                ('res_model', '=', self._name), ('res_id', '=', rec.id),
                ('user_id', '=', rec.owner_id.id), ('summary', '=', _('Document review due'))
            ])
            if not exists:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=rec.owner_id.id,
                    date_deadline=rec.review_date, summary=_('Document review due')
                )


class GarmentComplianceLegal(models.Model):
    _name = 'garment.compliance.legal'
    _description = 'Legal / Regulatory Requirement Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_review_date, name'

    name = fields.Char(required=True, tracking=True)
    authority = fields.Char()
    reference = fields.Char(string='Law / Rule / Clause Reference')
    category = fields.Selection([
        ('labor', 'Labor / Employment'), ('fire', 'Fire Safety'),
        ('factory', 'Factory / Industrial'), ('environment', 'Environment'),
        ('tax', 'Tax / Finance'), ('building', 'Building / Structural'),
        ('boiler', 'Boiler / Pressure'), ('electrical', 'Electrical'),
        ('chemical', 'Chemical'), ('other', 'Other')
    ], default='labor', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    department_id = fields.Many2one('hr.department')
    responsible_id = fields.Many2one('res.users', tracking=True)
    applicable = fields.Boolean(default=True)
    requirement = fields.Html(required=True)
    evidence = fields.Html()
    last_review_date = fields.Date()
    next_review_date = fields.Date(index=True)
    state = fields.Selection([
        ('compliant', 'Compliant'), ('partial', 'Partially Compliant'),
        ('non_compliant', 'Non-Compliant'), ('na', 'Not Applicable')
    ], default='partial', tracking=True)
    attachment_ids = fields.Many2many('ir.attachment')


class GarmentComplianceWorkerDocument(models.Model):
    _name = 'garment.compliance.worker.document'
    _description = 'Worker Document Compliance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'employee_id, document_type'

    employee_id = fields.Many2one('hr.employee', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True, index=True)
    document_type = fields.Selection([
        ('nid', 'NID / Identity'), ('birth', 'Birth / Age Proof'),
        ('appointment', 'Appointment Letter'), ('contract', 'Employment Contract'),
        ('id_card', 'Employee ID Card'), ('nominee', 'Nominee Form'),
        ('medical', 'Medical / Fitness'), ('training', 'Training Certificate'),
        ('other', 'Other')
    ], required=True)
    document_no = fields.Char()
    issue_date = fields.Date()
    expiry_date = fields.Date(index=True)
    verified = fields.Boolean(tracking=True)
    verified_by = fields.Many2one('res.users', readonly=True)
    verified_date = fields.Date(readonly=True)
    attachment_ids = fields.Many2many('ir.attachment')
    notes = fields.Text()

    def action_verify(self):
        self.write({
            'verified': True,
            'verified_by': self.env.user.id,
            'verified_date': fields.Date.context_today(self),
        })


class GarmentCompliancePPE(models.Model):
    _name = 'garment.compliance.ppe.issue'
    _description = 'PPE Issue and Replacement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'replacement_date, issue_date desc'

    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True, index=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    ppe_type = fields.Selection([
        ('helmet', 'Helmet'), ('gloves', 'Gloves'), ('mask', 'Mask / Respirator'),
        ('goggles', 'Safety Goggles'), ('ear', 'Hearing Protection'),
        ('shoe', 'Safety Shoes'), ('apron', 'Apron / Protective Clothing'),
        ('harness', 'Safety Harness'), ('other', 'Other')
    ], required=True)
    quantity = fields.Integer(default=1)
    issue_date = fields.Date(required=True, default=fields.Date.context_today)
    replacement_date = fields.Date(index=True)
    issued_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    condition = fields.Selection([
        ('good', 'Good'), ('replace', 'Replacement Due'), ('damaged', 'Damaged'), ('lost', 'Lost')
    ], default='good', tracking=True)
    notes = fields.Text()

    @api.model
    def _cron_ppe_due(self):
        today = fields.Date.context_today(self)
        for rec in self.search([('replacement_date', '!=', False), ('replacement_date', '<=', today), ('condition', '=', 'good')]):
            rec.condition = 'replace'


class GarmentComplianceCommittee(models.Model):
    _name = 'garment.compliance.committee'
    _description = 'Compliance / Safety Committee'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    committee_type = fields.Selection([
        ('safety', 'Safety Committee'), ('participation', 'Participation Committee'),
        ('anti_harassment', 'Anti-Harassment Committee'), ('environment', 'Environment Committee'),
        ('other', 'Other')
    ], required=True, default='safety')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    chairperson_id = fields.Many2one('hr.employee')
    member_ids = fields.Many2many('hr.employee')
    frequency = fields.Selection([
        ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('half_yearly', 'Half-Yearly'), ('yearly', 'Yearly')
    ], default='monthly')
    next_meeting_date = fields.Date(index=True)
    active = fields.Boolean(default=True)
    notes = fields.Html()


class GarmentComplianceMeeting(models.Model):
    _name = 'garment.compliance.meeting'
    _description = 'Compliance Committee Meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'meeting_date desc'

    name = fields.Char(required=True)
    committee_id = fields.Many2one('garment.compliance.committee', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='committee_id.company_id', store=True, index=True)
    meeting_date = fields.Datetime(required=True, default=fields.Datetime.now)
    attendee_ids = fields.Many2many('hr.employee')
    minutes = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment')
    action_ids = fields.One2many('garment.compliance.meeting.action', 'meeting_id')


class GarmentComplianceMeetingAction(models.Model):
    _name = 'garment.compliance.meeting.action'
    _description = 'Committee Meeting Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, id'

    name = fields.Char(required=True)
    meeting_id = fields.Many2one('garment.compliance.meeting', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='meeting_id.company_id', store=True, index=True)
    responsible_id = fields.Many2one('res.users', required=True)
    due_date = fields.Date(index=True)
    state = fields.Selection([
        ('open', 'Open'), ('progress', 'In Progress'), ('done', 'Done'), ('cancelled', 'Cancelled')
    ], default='open', tracking=True)
    evidence_ids = fields.Many2many('ir.attachment')
    notes = fields.Text()


class GarmentComplianceTrainingMatrix(models.Model):
    _name = 'garment.compliance.training.matrix'
    _description = 'Required Training Matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'department_id, name'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    department_id = fields.Many2one('hr.department', required=True)
    job_title = fields.Char(help='Optional designation/job title scope')
    training_type = fields.Selection([
        ('fire', 'Fire Safety'), ('firstaid', 'First Aid'), ('hse', 'Health & Safety'),
        ('chemical', 'Chemical Handling'), ('harassment', 'Anti-Harassment'),
        ('rights', 'Worker Rights'), ('machine', 'Machine Safety'),
        ('evacuation', 'Emergency Evacuation'), ('other', 'Other')
    ], required=True)
    validity_months = fields.Integer(default=12)
    mandatory = fields.Boolean(default=True)
    notes = fields.Text()


class GarmentComplianceRisk(models.Model):
    _name = 'garment.compliance.risk'
    _description = 'Compliance Risk Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'risk_score desc, id desc'

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    category = fields.Selection([
        ('social', 'Social'), ('safety', 'Safety'), ('legal', 'Legal'),
        ('environment', 'Environment'), ('buyer', 'Buyer'), ('security', 'Security'),
        ('quality', 'Quality'), ('other', 'Other')
    ], default='social', required=True)
    department_id = fields.Many2one('hr.department')
    owner_id = fields.Many2one('res.users', tracking=True)
    probability = fields.Integer(default=1)
    impact = fields.Integer(default=1)
    risk_score = fields.Integer(compute='_compute_risk', store=True)
    risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')
    ], compute='_compute_risk', store=True)
    mitigation = fields.Text()
    target_date = fields.Date(index=True)
    state = fields.Selection([
        ('open', 'Open'), ('mitigating', 'Mitigating'), ('accepted', 'Accepted'), ('closed', 'Closed')
    ], default='open', tracking=True)
    attachment_ids = fields.Many2many('ir.attachment')

    @api.depends('probability', 'impact')
    def _compute_risk(self):
        for rec in self:
            score = max(rec.probability or 0, 0) * max(rec.impact or 0, 0)
            rec.risk_score = score
            if score >= 20:
                rec.risk_level = 'critical'
            elif score >= 12:
                rec.risk_level = 'high'
            elif score >= 6:
                rec.risk_level = 'medium'
            else:
                rec.risk_level = 'low'


class GarmentComplianceCapaEscalation(models.Model):
    _inherit = 'garment.compliance.capa'

    overdue = fields.Boolean(compute='_compute_overdue', store=True)
    escalation_count = fields.Integer(readonly=True)

    @api.depends('due_date', 'state')
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.overdue = bool(rec.due_date and rec.due_date < today and rec.state not in ('verified', 'closed'))

    @api.model
    def _cron_escalate_overdue(self):
        today = fields.Date.context_today(self)
        records = self.search([
            ('due_date', '<', today), ('state', 'not in', ['verified', 'closed']),
            ('responsible_id', '!=', False)
        ])
        for rec in records:
            exists = self.env['mail.activity'].search_count([
                ('res_model', '=', self._name), ('res_id', '=', rec.id),
                ('user_id', '=', rec.responsible_id.id), ('summary', '=', _('Overdue CAPA'))
            ])
            if not exists:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=rec.responsible_id.id,
                    date_deadline=today, summary=_('Overdue CAPA'),
                    note=_('This CAPA is overdue and requires immediate follow-up.')
                )
                rec.escalation_count += 1
