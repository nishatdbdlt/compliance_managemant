from odoo import models, fields, api


class TrandingProduct(models.Model):
    _name = 'tranding.product'
    _description = 'tranding product'

    name = fields.Char(string='Name')

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

