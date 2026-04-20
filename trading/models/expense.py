from odoo import fields, models

class Expense(models.Model):
    _name = 'trading.expense'
    _description = 'Expense'

    name = fields.Char(string='Name', required=True)
    # amount = fields.Float(string='Amount', required=True)
    # date = fields.Date(string='Date', required=True)
    description = fields.Text(string='Description')