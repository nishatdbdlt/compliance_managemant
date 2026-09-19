from odoo import api, fields, models, _
from odoo.exceptions import UserError

class GarmentComplianceRequirement(models.Model):
    _name = 'garment.compliance.requirement'
    _description = 'Garments Compliance Requirement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date asc, id desc'

    name = fields.Char(required=True, tracking=True)
    reference = fields.Char(default='New', copy=False, readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    department_id = fields.Many2one('hr.department', tracking=True)
    responsible_id = fields.Many2one('res.users', tracking=True)
    buyer_id = fields.Many2one('garment.compliance.buyer', tracking=True)
    category = fields.Selection([
        ('legal','Legal'),('social','Social'),('safety','Health & Safety'),('environment','Environment'),
        ('chemical','Chemical'),('buyer','Buyer'),('hr','HR'),('security','Security'),('quality','Quality'),('other','Other')
    ], required=True, default='legal', tracking=True)
    authority = fields.Char()
    description = fields.Html()
    issue_date = fields.Date()
    effective_date = fields.Date()
    expiry_date = fields.Date(tracking=True)
    review_date = fields.Date()
    risk_level = fields.Selection([('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')], default='medium', tracking=True)
    priority = fields.Selection([('0','Normal'),('1','Low'),('2','High'),('3','Very High')], default='0')
    state = fields.Selection([
        ('draft','Draft'),('pending','Pending'),('review','Under Review'),('compliant','Compliant'),
        ('non_compliant','Non-Compliant'),('corrective','Corrective Action'),('expiring','Expiring Soon'),('expired','Expired')
    ], default='draft', tracking=True)
    compliance_score = fields.Float(default=100.0)
    notes = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment', string='Evidence / Documents')

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = seq.next_by_code('garment.compliance.requirement') or 'New'
        return super().create(vals_list)

    def action_submit(self): self.write({'state':'pending'})
    def action_review(self): self.write({'state':'review'})
    def action_compliant(self): self.write({'state':'compliant'})
    def action_non_compliant(self): self.write({'state':'non_compliant'})
    def action_corrective(self): self.write({'state':'corrective'})
    def action_reset_draft(self): self.write({'state':'draft'})

    @api.model
    def _cron_update_expiry_states(self):
        today = fields.Date.context_today(self)
        warning = fields.Date.add(today, days=30)
        records = self.search([('expiry_date','!=',False)])
        for rec in records:
            if rec.expiry_date < today:
                rec.state = 'expired'
            elif today <= rec.expiry_date <= warning and rec.state not in ('expired','non_compliant','corrective'):
                rec.state = 'expiring'
                if rec.responsible_id:
                    existing = self.env['mail.activity'].search_count([
                        ('res_model','=','garment.compliance.requirement'),('res_id','=',rec.id),('user_id','=',rec.responsible_id.id),
                        ('summary','=',_('Compliance renewal due'))
                    ])
                    if not existing:
                        rec.activity_schedule('mail.mail_activity_data_todo', user_id=rec.responsible_id.id,
                                              date_deadline=rec.expiry_date,
                                              summary=_('Compliance renewal due'),
                                              note=_('This compliance item is expiring soon.'))
