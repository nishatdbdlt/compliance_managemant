from odoo import fields, models, api, _

class Purchase(models.Model):
    _name = 'trd.purchase'
    _description = 'Purchase'

    Sl_no = fields.Char(string='PI', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, copy=False)
    
    supplier_id = fields.Many2one('trd.contact', string='Supplier', domain="[('is_vendor', '=', True)]")
    
    purchase_line_ids = fields.One2many('trd.purchase.line', 'purchase_id', string='Order Lines')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)

    payment_id = fields.Many2one('trd.payment', string='Payment')
    category_id = fields.Many2one('trd.product.category', string='Category')
    stock_id = fields.Many2one('trd.stock.location', string='Stock')
    vendor_id = fields.Many2one('trd.contact', string='Other Vendor')
    expense_id = fields.Many2one('trd.expense', string='Expense')
    date = fields.Date(string='Date', default=fields.Date.today())
    Location = fields.Many2one('trd.stock.location', string='Location')
    

    @api.depends('purchase_line_ids.total')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(line.total for line in rec.purchase_line_ids)

    def action_confirm(self):
        for rec in self:
            if rec.Sl_no == _('New'):
                rec.Sl_no = self.env['ir.sequence'].next_by_code('trd.purchase') or _('New')
            rec.state = 'confirmed'

    def action_print_report(self):
        return self.env.ref('trading.action_report_trd_purchase').report_action(self)

class PurchaseLine(models.Model):
    _name = 'trd.purchase.line'
    _description = 'Purchase Line'

    purchase_id = fields.Many2one('trd.purchase', string='Purchase Reference', required=True, ondelete='cascade')
    sl_no = fields.Char(string='PI')
    product_id = fields.Many2one('trd.product', string='Product Name', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    price = fields.Float(string='Unit Price')
    discount = fields.Char(string='Discount', help="Enter '10%' for percentage or '50' for fixed amount")
    total = fields.Float(string='Total Price', compute='_compute_total', store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price = self.product_id.price

    @api.depends('quantity', 'price', 'discount')
    def _compute_total(self):
        for line in self:
            subtotal = line.quantity * line.price
            if line.discount:
                discount_str = line.discount.strip()
                if discount_str.endswith('%'):
                    try:
                        val = float(discount_str[:-1])
                        line.total = subtotal * (1 - (val / 100.0))
                    except ValueError:
                        line.total = subtotal
                else:
                    try:
                        numeric_str = ''.join(c for c in discount_str if c.isdigit() or c == '.')
                        val = float(numeric_str) if numeric_str else 0.0
                        line.total = subtotal - val
                    except ValueError:
                        line.total = subtotal
            else:
                line.total = subtotal
