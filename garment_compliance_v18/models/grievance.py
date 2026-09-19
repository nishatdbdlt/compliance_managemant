from odoo import api, fields, models
class GarmentComplianceGrievance(models.Model):
    _name='garment.compliance.grievance'; _description='Worker Grievance'; _inherit=['mail.thread','mail.activity.mixin']; _order='create_date desc'
    reference=fields.Char(default='New',copy=False,readonly=True); employee_id=fields.Many2one('hr.employee'); anonymous=fields.Boolean(); category=fields.Selection([('salary','Salary'),('behavior','Supervisor Behavior'),('harassment','Harassment'),('leave','Leave'),('overtime','Overtime'),('safety','Safety'),('facility','Facility'),('other','Other')],required=True)
    description=fields.Text(required=True); assigned_id=fields.Many2one('res.users'); resolution=fields.Text(); state=fields.Selection([('submitted','Submitted'),('investigation','Under Investigation'),('action','Action Taken'),('resolved','Resolved')],default='submitted',tracking=True)
    @api.model_create_multi
    def create(self,vals_list):
        seq=self.env['ir.sequence']
        for v in vals_list:
            if v.get('reference','New')=='New': v['reference']=seq.next_by_code('garment.compliance.grievance') or 'New'
        return super().create(vals_list)
