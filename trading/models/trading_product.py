from odoo import models, fields, api, _

class TrandingProduct(models.Model):
    _name = 'tranding.product'
    _description = 'tranding product'

    name = fields.Char(string='Name', required=True)
    sl_no = fields.Char(string='Serial Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sl_no', _('New')) == _('New'):
                vals['sl_no'] = self.env['ir.sequence'].next_by_code('tranding.product') or _('New')
        return super().create(vals_list)

    price = fields.Float(string='Actual Price (Cost)')

    # percentage = fields.Float(string='Discount Percentage (%)', default=0.0)

    # sell_price = fields.Float(
    #     string='Sell Price',
    #     compute='_compute_sell_price',
    #     store=True,
    # )

    product_category = fields.Many2one(
        'trading.product.category',
        string='Product Category',
    )

    # @api.depends('price', 'percentage')
    # def _compute_sell_price(self):
    #     for record in self:
    #         record.sell_price = record.price - (record.price * record.percentage / 100)

