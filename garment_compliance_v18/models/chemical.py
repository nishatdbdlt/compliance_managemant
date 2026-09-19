from odoo import fields, models
class GarmentComplianceChemical(models.Model):
    _name='garment.compliance.chemical'; _description='Chemical Register'; _inherit=['mail.thread','mail.activity.mixin']
    name=fields.Char(required=True); supplier_id=fields.Many2one('res.partner'); hazard_class=fields.Char(); storage_location=fields.Char(); approval_status=fields.Selection([('approved','Approved'),('restricted','Restricted'),('banned','Banned'),('pending','Pending')],default='pending',tracking=True); expiry_date=fields.Date(); ppe_requirement=fields.Text(); sds_attachment_ids=fields.Many2many('ir.attachment',string='SDS / MSDS'); notes=fields.Text()
