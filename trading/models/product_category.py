# # -*- coding: utf-8 -*-
# from odoo import fields, models

# class ProductCategory(models.Model):
#     _name = 'trading.product.category'     
#     _description = 'Product Category'
#     _parent_name = "parent_id"

#     name = fields.Char(string='Name', required=True)
#     parent_id = fields.Many2one('trading.product.category', string='Parent Category')

# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ProductCategory(models.Model):
    _name = 'trading.product.category'
    _description = 'Product Category'

    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'



    name = fields.Char(required=True)

    parent_id = fields.Many2one(
        'trading.product.category',
        string='Parent Category'
    )

  

    parent_path = fields.Char(index=True)

    complete_name = fields.Char(
        compute="_compute_complete_name",
        store=True
    )


    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
     for rec in self:
        if rec.parent_id and rec.parent_id.complete_name:
            rec.complete_name = (
                rec.parent_id.complete_name
                + ' / ' +
                (rec.name or '')
            )
        else:
            rec.complete_name = rec.name or ''