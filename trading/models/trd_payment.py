from odoo import api, fields, models, _

class Payment(models.Model):
    _name = 'trd.payment'
    _description = 'Payment'

    name = fields.Char(string='Name', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    amount = fields.Float(string='Amount')

    