from odoo import models, fields, api, _

class TrandingProduct(models.Model):
    _name = 'trd.product'
    _description = 'trd product'

    name = fields.Char(string='Name', required=True)
    sl_no = fields.Char(string='Serial Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sl_no', _('New')) == _('New'):
                vals['sl_no'] = self.env['ir.sequence'].next_by_code('trd.product') or _('New')
        return super().create(vals_list)

    price = fields.Float(string='Actual Price (Cost)')

    
    product_category = fields.Many2one(
        'trd.product.category',
        string='Product Category',
    )

    
