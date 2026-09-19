from odoo import fields, models

class GarmentComplianceBuyer(models.Model):
    _name = 'garment.compliance.buyer'
    _description = 'Buyer Compliance Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact')
    code = fields.Char()
    code_of_conduct = fields.Html()
    audit_frequency_months = fields.Integer(default=12)
    last_audit_date = fields.Date()
    next_audit_date = fields.Date()
    active = fields.Boolean(default=True)
    notes = fields.Html()
    requirement_ids = fields.One2many('garment.compliance.requirement','buyer_id')
