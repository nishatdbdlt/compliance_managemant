from odoo import api, fields, models, _

class Expense(models.Model):
    _name = 'trd.expense'
    _description = 'Expense'

    name = fields.Char(string='Name')
    sl_no = fields.Char(string='Serial Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    description = fields.Text(string='Description')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sl_no', _('New')) == _('New'):
                vals['sl_no'] = self.env['ir.sequence'].next_by_code('trd.expense') or _('New')
        return super().create(vals_list)