from odoo import api, fields, models, _
class GarmentComplianceCertificate(models.Model):
    _name='garment.compliance.certificate'; _description='License and Certificate'; _inherit=['mail.thread','mail.activity.mixin']; _order='expiry_date asc'
    name=fields.Char(required=True,tracking=True); certificate_no=fields.Char(); category=fields.Selection([('trade','Trade License'),('factory','Factory License'),('fire','Fire Safety'),('environment','Environment'),('boiler','Boiler'),('electrical','Electrical'),('buyer','Buyer'),('iso','ISO'),('social','Social Compliance'),('other','Other')],default='other')
    authority=fields.Char(); issue_date=fields.Date(); expiry_date=fields.Date(tracking=True); responsible_id=fields.Many2one('res.users'); company_id=fields.Many2one('res.company',default=lambda self:self.env.company,required=True)
    state=fields.Selection([('valid','Valid'),('expiring','Expiring Soon'),('expired','Expired')],default='valid',tracking=True); attachment_ids=fields.Many2many('ir.attachment')
    @api.model
    def _cron_check_expiry(self):
        today=fields.Date.context_today(self); warning=fields.Date.add(today,days=30)
        for r in self.search([('expiry_date','!=',False)]):
            new='expired' if r.expiry_date<today else ('expiring' if r.expiry_date<=warning else 'valid')
            if r.state!=new: r.state=new
            if new=='expiring' and r.responsible_id:
                if not self.env['mail.activity'].search_count([('res_model','=','garment.compliance.certificate'),('res_id','=',r.id),('summary','=',_('Certificate renewal due'))]):
                    r.activity_schedule('mail.mail_activity_data_todo',user_id=r.responsible_id.id,date_deadline=r.expiry_date,summary=_('Certificate renewal due'))
