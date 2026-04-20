from odoo import fields, models

class Stocklocation(models.Model):
    _name = 'trading.stock.location'
    _description = 'stock location'

    name = fields.Char(string='Name', required=True)
    location_type = fields.Selection([('internal', 'Internal'), ('external', 'External')], string='Location Type', required=True)
    parent_id = fields.Many2one('trading.stock.location', string='Parent Location')
    



