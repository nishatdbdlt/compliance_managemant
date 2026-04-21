# -*- coding: utf-8 -*-
{
    "name": "Trading",
    "version": "18.0.1.0.0",
    "summary": "Simple trading management app for Odoo 18",
    "description": """
Trading App
===========

This module adds a simple custom trading app for Odoo 18.

Features:
- Trading Orders
- Customer tracking
- Buy and sell type orders
- Quantity and price management
- Draft to confirmed workflow
""",
    "author": "Custom Development",
    "category": "Sales",
    "depends": ["base", "mail",],
    "data": [
        "security/ir.model.access.csv",
        "views/product_catagory.xml",
        "views/sales.xml",
        'views/stock.xml',
        'views/vendor.xml',
        'views/expanse.xml',
        'views/payment.xml',
        'views/tranding_product.xml',
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
