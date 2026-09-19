from odoo import api, fields, models

class GarmentComplianceAudit(models.Model):
    _name = 'garment.compliance.audit'
    _description = 'Garments Compliance Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date desc, id desc'

    name = fields.Char(required=True)
    reference = fields.Char(default='New', copy=False, readonly=True)
    audit_type = fields.Selection([('buyer','Buyer Audit'),('internal','Internal Audit'),('social','Social Audit'),('safety','Safety Audit'),('environment','Environmental Audit'),('security','Security Audit'),('quality','Quality Audit')], required=True, default='internal')
    buyer_id = fields.Many2one('garment.compliance.buyer')
    department_id = fields.Many2one('hr.department')
    auditor_id = fields.Many2one('res.users')
    audit_date = fields.Date(required=True, default=fields.Date.context_today)
    next_audit_date = fields.Date()
    state = fields.Selection([('planned','Planned'),('scheduled','Scheduled'),('running','Audit Running'),('reported','Report Received'),('capa','CAPA'),('verified','Verification'),('closed','Closed')], default='planned', tracking=True)
    score = fields.Float()
    line_ids = fields.One2many('garment.compliance.audit.line','audit_id')
    finding_ids = fields.One2many('garment.compliance.finding','audit_id')
    report_attachment_ids = fields.Many2many('ir.attachment', string='Audit Reports')
    notes = fields.Html()

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('reference','New') == 'New': vals['reference'] = seq.next_by_code('garment.compliance.audit') or 'New'
        return super().create(vals_list)

    def action_next(self):
        order=['planned','scheduled','running','reported','capa','verified','closed']
        for rec in self:
            i=order.index(rec.state)
            if i < len(order)-1: rec.state=order[i+1]

class GarmentComplianceAuditLine(models.Model):
    _name = 'garment.compliance.audit.line'
    _description = 'Audit Checklist Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    audit_id = fields.Many2one('garment.compliance.audit', required=True, ondelete='cascade')
    section = fields.Char()
    question = fields.Char(required=True)
    result = fields.Selection([('yes','Yes'),('no','No'),('na','N/A'),('observation','Observation')])
    observation = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment')

class GarmentComplianceFinding(models.Model):
    _name = 'garment.compliance.finding'
    _description = 'Compliance Finding'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, string='Finding')
    audit_id = fields.Many2one('garment.compliance.audit', required=True, ondelete='cascade')
    category = fields.Char()
    severity = fields.Selection([('minor','Minor'),('major','Major'),('critical','Critical')], default='minor', tracking=True)
    observation = fields.Text()
    root_cause = fields.Text()
    responsible_id = fields.Many2one('res.users')
    due_date = fields.Date()
    state = fields.Selection([('open','Open'),('progress','In Progress'),('submitted','Submitted'),('verified','Verified'),('closed','Closed')], default='open', tracking=True)
    capa_ids = fields.One2many('garment.compliance.capa','finding_id')
    attachment_ids = fields.Many2many('ir.attachment', string='Evidence')
