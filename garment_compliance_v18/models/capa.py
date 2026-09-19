from odoo import api, fields, models
class GarmentComplianceCapa(models.Model):
    _name='garment.compliance.capa'; _description='Corrective and Preventive Action'; _inherit=['mail.thread','mail.activity.mixin']; _order='due_date asc,id desc'
    name=fields.Char(required=True); reference=fields.Char(default='New',copy=False,readonly=True)
    finding_id=fields.Many2one('garment.compliance.finding',ondelete='cascade'); root_cause=fields.Text(); corrective_action=fields.Text(required=True); preventive_action=fields.Text()
    responsible_id=fields.Many2one('res.users',tracking=True); due_date=fields.Date(tracking=True); verification_date=fields.Date(); verified_by=fields.Many2one('res.users')
    severity=fields.Selection(related='finding_id.severity',store=True); state=fields.Selection([('open','Open'),('progress','In Progress'),('submitted','Submitted'),('verified','Verified'),('closed','Closed')],default='open',tracking=True)
    evidence_ids=fields.Many2many('ir.attachment',string='Closure Evidence')
    @api.model_create_multi
    def create(self,vals_list):
        seq=self.env['ir.sequence']
        for v in vals_list:
            if v.get('reference','New')=='New': v['reference']=seq.next_by_code('garment.compliance.capa') or 'New'
        return super().create(vals_list)
    def action_progress(self): self.write({'state':'progress'})
    def action_submit(self): self.write({'state':'submitted'})
    def action_verify(self): self.write({'state':'verified','verified_by':self.env.user.id,'verification_date':fields.Date.context_today(self)})
    def action_close(self): self.write({'state':'closed'})
