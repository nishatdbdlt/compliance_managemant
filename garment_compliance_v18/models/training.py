from odoo import fields, models
class GarmentComplianceTraining(models.Model):
    _name='garment.compliance.training'; _description='Compliance Training'; _inherit=['mail.thread','mail.activity.mixin']; _order='training_date desc'
    name=fields.Char(required=True); training_type=fields.Selection([('fire','Fire Safety'),('firstaid','First Aid'),('hse','Health & Safety'),('chemical','Chemical Handling'),('harassment','Anti-Harassment'),('rights','Worker Rights'),('machine','Machine Safety'),('evacuation','Emergency Evacuation'),('other','Other')],default='hse',required=True)
    training_date=fields.Date(required=True,default=fields.Date.context_today); next_training_date=fields.Date(); trainer=fields.Char(); department_id=fields.Many2one('hr.department'); participant_ids=fields.Many2many('hr.employee'); notes=fields.Text(); attachment_ids=fields.Many2many('ir.attachment')
