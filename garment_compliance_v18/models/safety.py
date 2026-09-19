from odoo import fields, models
class GarmentSafetyInspection(models.Model):
    _name='garment.compliance.safety'; _description='Safety Inspection'; _inherit=['mail.thread','mail.activity.mixin']; _order='inspection_date desc'
    name=fields.Char(required=True); inspection_type=fields.Selection([('fire','Fire Safety'),('electrical','Electrical Safety'),('structural','Structural Safety'),('boiler','Boiler Safety'),('machine','Machine Safety'),('ppe','PPE'),('firstaid','First Aid'),('other','Other')],required=True)
    department_id=fields.Many2one('hr.department'); inspector_id=fields.Many2one('res.users'); inspection_date=fields.Date(default=fields.Date.context_today,required=True); next_inspection_date=fields.Date(); condition=fields.Selection([('good','Good'),('attention','Needs Attention'),('unsafe','Unsafe')],default='good',tracking=True)
    observation=fields.Text(); action_required=fields.Text(); responsible_id=fields.Many2one('res.users'); due_date=fields.Date(); attachment_ids=fields.Many2many('ir.attachment'); state=fields.Selection([('open','Open'),('done','Done')],default='open')
