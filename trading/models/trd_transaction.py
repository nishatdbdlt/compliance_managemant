from odoo import api, fields, models, _

class Transaction(models.Model):
    _name = 'trd.transaction'
    _description = 'Payment Transaction'
    _order = 'payment_date desc, id desc'

    name = fields.Char(string='Transaction ID', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True)
    partner_id = fields.Many2one('trd.contact', string='Partner', required=True)
    amount = fields.Float(string='Amount', required=True)
    payment_method_id = fields.Many2one('trd.payment', string='Payment Method', required=True)
    
    sale_id = fields.Many2one('trd.sales', string='Sales Reference', readonly=True)
    purchase_id = fields.Many2one('trd.purchase', string='Purchase Reference', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', readonly=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.sale_id = False
        self.purchase_id = False
        if self.partner_id:
            return {'domain': {
                'sale_id': [('customer_id', '=', self.partner_id.id), ('state', '=', 'confirmed')],
                'purchase_id': [('supplier_id', '=', self.partner_id.id), ('state', '=', 'confirmed')]
            }}

    @api.onchange('sale_id')
    def _onchange_sale_id(self):
        if self.sale_id:
            self.amount = self.sale_id.total_amount

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        if self.purchase_id:
            self.amount = self.purchase_id.total_amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('trd.transaction') or _('New')
        return super().create(vals_list)

    def action_paid(self):
        for rec in self:
            rec.state = 'paid'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
