from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Transaction(models.Model):
    _name = 'trd.transaction'
    _description = 'Payment Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'payment_date desc, id desc'

    name = fields.Char(
        string='Transaction ID', required=True, copy=False,
        readonly=True, default=lambda self: _('New')
    )
    payment_date = fields.Date(
        string='Payment Date',
        default=fields.Date.context_today,
        required=True,
    )
    partner_id = fields.Many2one('trd.contact', string='Partner')

    amount = fields.Float(
        string='Total Amount',
        default=lambda self: self.env.context.get('default_amount', 0.0),
    )

    # ── This is the ONLY field the user enters in Draft ────────────────────────
    # It is the first partial payment. 0 means "pay full amount".
    initial_payment = fields.Float(
        string='Initial Payment',
        default=0.0,
        help='How much are you paying now? Leave 0 to pay the full amount at once.',
    )

    # ── Cumulative paid total — ALWAYS computed/set by actions, never by user ──
    paid_amount = fields.Float(
        string='Total Paid',
        default=0.0,
        readonly=True,
        tracking=True,
        copy=False,
    )

    due_amount = fields.Float(
        string='Due Amount',
        compute='_compute_due_amount',
        store=True,
        tracking=True,
    )

    # ── Additional payment toward due — editable only in 'due' state ───────────
    due_payment_amount = fields.Float(
        string='Paying Now (additional)',
        default=0.0,
        help='Enter how much extra you are paying toward the due balance. '
             'Leave 0 to clear the full remaining due at once.',
    )

    payment_method_id = fields.Many2one('trd.payment', string='Payment Method')

    sale_id     = fields.Many2one('trd.sales',    string='Sales Reference',    readonly=True)
    purchase_id = fields.Many2one('trd.purchase', string='Purchase Reference', readonly=True)

    state = fields.Selection([
        ('draft',  'Draft'),
        ('due',    'Partially Paid (Due)'),
        ('paid',   'Paid'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # ── Computed ───────────────────────────────────────────────────────────────
    @api.depends('amount', 'paid_amount')
    def _compute_due_amount(self):
        for rec in self:
            rec.due_amount = max(rec.amount - rec.paid_amount, 0.0)

    # ── Onchange ──────────────────────────────────────────────────────────────
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.sale_id = False
        self.purchase_id = False
        if self.partner_id:
            return {'domain': {
                'sale_id': [
                    ('customer_id', '=', self.partner_id.id),
                    ('state', '=', 'confirmed'),
                ],
                'purchase_id': [
                    ('supplier_id', '=', self.partner_id.id),
                    ('state', '=', 'confirmed'),
                ],
            }}

    @api.onchange('sale_id')
    def _onchange_sale_id(self):
        if self.sale_id:
            self.amount = self.sale_id.total_amount or 0.0
            if self.sale_id.customer_id:
                self.partner_id = self.sale_id.customer_id

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        if self.purchase_id:
            self.amount = self.purchase_id.total_amount or 0.0

    # ── Create ────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('trd.transaction') or _('New')
                )
            if not vals.get('amount'):
                vals['amount'] = self.env.context.get('default_amount', 0.0)
        return super().create(vals_list)

    # ── Actions ───────────────────────────────────────────────────────────────
    def action_paid(self):
        """Confirm the initial payment.
        - initial_payment == 0        → full payment (paid_amount = amount, state = paid)
        - 0 < initial_payment < amount → partial  (paid_amount = initial_payment, state = due)
        - initial_payment >= amount   → full payment
        """
        for rec in self:
            if not rec.amount or rec.amount <= 0:
                raise UserError(_('Please set a Total Amount greater than 0 before confirming.'))

            first = rec.initial_payment or 0.0

            if first <= 0:
                # No partial entered → pay in full
                rec.write({
                    'paid_amount': rec.amount,
                    'initial_payment': rec.amount,
                    'due_payment_amount': 0.0,
                    'state': 'paid',
                })
            elif first < rec.amount:
                # Partial → due
                rec.write({
                    'paid_amount': first,
                    'due_payment_amount': 0.0,
                    'state': 'due',
                })
            else:
                # Entered >= total → treat as full
                rec.write({
                    'paid_amount': rec.amount,
                    'initial_payment': rec.amount,
                    'due_payment_amount': 0.0,
                    'state': 'paid',
                })

    def action_pay_due(self):
        """Pay additional amount toward the due balance.
        - due_payment_amount > 0 → add it to paid_amount (cumulative)
        - due_payment_amount == 0 → pay the full remaining due
        If new total >= amount → state = 'paid', else stay 'due'.
        """
        for rec in self:
            if rec.state != 'due':
                raise UserError(_('Only transactions with a due balance can use this action.'))
            if rec.due_amount <= 0:
                raise UserError(_('No remaining due balance on this transaction.'))

            adding = rec.due_payment_amount or 0.0

            if adding <= 0:
                # Clear the full remaining due
                rec.write({
                    'paid_amount': rec.amount,
                    'due_payment_amount': 0.0,
                    'state': 'paid',
                })
            elif adding > rec.due_amount:
                raise UserError(_(
                    'Amount to pay (%(pay).2f) exceeds the remaining due (%(due).2f).',
                    pay=adding, due=rec.due_amount,
                ))
            else:
                new_paid = rec.paid_amount + adding
                if new_paid >= rec.amount:
                    rec.write({
                        'paid_amount': rec.amount,
                        'due_payment_amount': 0.0,
                        'state': 'paid',
                    })
                else:
                    rec.write({
                        'paid_amount': new_paid,
                        'due_payment_amount': 0.0,
                        # stays 'due'
                    })

    def action_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft',
                'paid_amount': 0.0,
                'initial_payment': 0.0,
                'due_payment_amount': 0.0,
            })

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
