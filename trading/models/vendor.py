from odoo import api, fields, models, _

class Vendor(models.Model):
    _name = 'trading.vendor'
    _description = 'Vendor'

    name = fields.Char(string='Name', required=True)
    sl_no = fields.Char(string='Serial Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    address = fields.Text(string='Address')
    is_customer = fields.Boolean(string='Customer')
    is_vendor = fields.Boolean(string='Vendor')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sl_no', _('New')) == _('New'):
                vals['sl_no'] = self.env['ir.sequence'].next_by_code('trading.vendor') or _('New')
        return super().create(vals_list)
