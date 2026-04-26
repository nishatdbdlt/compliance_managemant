from odoo import api, fields, models, _

class Payment(models.Model):
    _name = 'trd.payment'
    _description = 'Payment'

    amount = fields.Float(string='Amount')
    Name = fields.Char(string='Name')

    