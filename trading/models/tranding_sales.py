from odoo import fields, models, api, _

class Sales(models.Model):
    _name = 'trading.sales'
    _description = 'Sales'

    name = fields.Char(string='Name', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    product = fields.Char(string='Product')
    quantity = fields.Float(string='Quantity')
    price = fields.Float(string='Price')
    total = fields.Float(string='Total', compute='_compute_total', store=True)

    payment_id = fields.Many2one('trading.payment', string='Payment')
    category_id = fields.Many2one('trading.product.category', string='Category')
    stock_id = fields.Many2one('trading.stock.location', string='Stock')
    vendor_id = fields.Many2one('trading.vendor', string='Vendor')
    expense_id = fields.Many2one('trading.expense', string='Expense')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('trading.sales') or _('New')
        return super().create(vals_list)

    @api.depends('quantity', 'price')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.quantity * rec.price
