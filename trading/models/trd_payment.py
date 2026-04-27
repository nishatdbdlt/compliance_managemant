from odoo import api, fields, models, _

class Payment(models.Model):
    _name = 'trd.payment'
    _description = 'Payment'
    _rec_name = 'name'

    amount = fields.Float(string='Amount')
    name = fields.Char(string='Name')

    