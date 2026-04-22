from odoo import api, fields, models, _

class Payment(models.Model):
    _name = 'trading.payment'
    _description = 'Payment'

    name = fields.Char(string='Name', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    amount = fields.Float(string='Amount')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('trading.payment') or _('New')
        return super().create(vals_list)