from odoo import api, fields, models, _

class Vendor(models.Model):
    _name = 'trd.contact'
    _description = 'Vendor'

    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    address = fields.Text(string='Address')
    is_customer = fields.Boolean(string='Customer')
    is_vendor = fields.Boolean(string='Vendor')

    
