from odoo import fields, models

class Payment(models.Model):
    _name = 'trading.payment'
    _description = 'Payment'

    name = fields.Char(string='Name')
    amount = fields.Float(string='Amount')
    