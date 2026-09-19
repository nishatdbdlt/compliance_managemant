from odoo import fields, models
class GarmentComplianceEnvironment(models.Model):
    _name='garment.compliance.environment'; _description='Environmental Monitoring'; _inherit=['mail.thread','mail.activity.mixin']; _order='date desc'
    name=fields.Char(required=True); date=fields.Date(required=True,default=fields.Date.context_today); monitoring_type=fields.Selection([('water','Water Usage'),('wastewater','Wastewater'),('etp','ETP'),('waste','Waste Disposal'),('hazardous','Hazardous Waste'),('air','Air Emission'),('energy','Energy Usage'),('chemical_waste','Chemical Waste')],required=True)
    value=fields.Float(); unit=fields.Char(); limit_value=fields.Float(); result=fields.Selection([('pass','Pass'),('fail','Fail'),('na','N/A')]); observation=fields.Text(); responsible_id=fields.Many2one('res.users'); attachment_ids=fields.Many2many('ir.attachment')
