from odoo import api, fields, models, _

class Expense(models.Model):
    _name = 'trading.expense'
    _description = 'Expense'

    name = fields.Char(string='Name', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    # amount = fields.Float(string='Amount', required=True)
    # date = fields.Date(string='Date', required=True)
    description = fields.Text(string='Description')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('trading.expense') or _('New')
        return super().create(vals_list)