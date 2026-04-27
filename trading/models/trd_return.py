from odoo import fields, models, api, _

class TradingReturn(models.Model):
    _name = 'trd.returns'
    _description = 'Trading Return'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    return_type = fields.Selection([
        ('sales', 'Sales Return'),
        ('purchase', 'Purchase Return')
    ], string='Return Type', default='sales', required=True)
    
    date = fields.Date(string='Return Date', default=fields.Date.today(), required=True)
    partner_id = fields.Many2one('trd.contact', string='Contact', required=True)
    
    order_id_sales = fields.Many2one(
        'trd.sales',
        string='Sales Order',
        domain="[('state', '=', 'confirmed')]"
    )
    order_id_purchase = fields.Many2one(
        'trd.purchase',
        string='Purchase Order',
        domain="[('state', '=', 'confirmed')]"
    )
    
    return_line_ids = fields.One2many('trd.returns.line', 'return_id', string='Return Lines')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, copy=False)

    @api.depends('return_line_ids.total')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(line.total for line in rec.return_line_ids)

    @api.onchange('partner_id', 'return_type')
    def _onchange_partner_id(self):
        """Partner বা type change হলে order এবং lines clear করো"""
        self.order_id_sales = False
        self.order_id_purchase = False
        self.return_line_ids = [(5, 0, 0)]

        if self.partner_id and self.return_type == 'sales':
            return {
                'domain': {
                    'order_id_sales': [
                        ('customer_id', '=', self.partner_id.id),
                        ('state', '=', 'confirmed')
                    ]
                }
            }
        elif self.partner_id and self.return_type == 'purchase':
            return {
                'domain': {
                    'order_id_purchase': [
                        ('supplier_id', '=', self.partner_id.id),
                        ('state', '=', 'confirmed')
                    ]
                }
            }

    @api.onchange('order_id_sales')
    def _onchange_order_id_sales(self):
        """Sales order select করলে automatically সেই order এর lines আসবে"""
        self.return_line_ids = [(5, 0, 0)]
        if self.order_id_sales:
            lines = []
            for line in self.order_id_sales.sale_line_ids:
                lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'price': line.price,
                }))
            self.return_line_ids = lines

    @api.onchange('order_id_purchase')
    def _onchange_order_id_purchase(self):
        """Purchase order select করলে automatically সেই order এর lines আসবে"""
        self.return_line_ids = [(5, 0, 0)]
        if self.order_id_purchase:
            lines = []
            for line in self.order_id_purchase.purchase_line_ids:
                lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'price': line.price,
                }))
            self.return_line_ids = lines

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('trd.returns') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'


class TradingReturnLine(models.Model):
    _name = 'trd.returns.line'
    _description = 'Trading Return Line'

    return_id = fields.Many2one('trd.returns', string='Return Reference', required=True, ondelete='cascade')
    product_id = fields.Many2one('trd.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    price = fields.Float(string='Unit Price')
    total = fields.Float(string='Total Price', compute='_compute_total', store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price = self.product_id.price

    @api.depends('quantity', 'price')
    def _compute_total(self):
        for line in self:
            line.total = line.quantity * line.price