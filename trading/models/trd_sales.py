from odoo import fields, models, api, _

class Sales(models.Model):
    _name = 'trd.sales'
    _description = 'Sales'

    Sl_no = fields.Char(string='SL', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    product = fields.Char(string='Product')
    name = fields.Char(string='Name')
    quantity = fields.Float(string='Quantity')
    price = fields.Float(string='Price')
    total = fields.Float(string='Total', compute='_compute_total', store=True)

    payment_id = fields.Many2one('trd.payment', string='Payment')
    category_id = fields.Many2one('trd.product.category', string='Category')
    stock_id = fields.Many2one('trd.stock.location', string='Stock')
    vendor_id = fields.Many2one('trd.contact', string='Vendor')
    expense_id = fields.Many2one('trd.expense', string='Expense')

    @api.depends('quantity', 'price')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.quantity * rec.price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('Sl_no', _('New')) == _('New'):
                vals['Sl_no'] = self.env['ir.sequence'].next_by_code('trd.sales') or _('New')
        return super(Sales, self).create(vals_list)