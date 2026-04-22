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
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/tranding_product_catagory.xml",
        'views/tranding_customer.xml',
         "views/tranding_sales.xml",
        'views/tranding_stock.xml',
        'views/tranding_vendor.xml',
        'views/tranding_expense.xml',
        'views/tranding_payment.xml',
        'views/tranding_product.xml',
        "views/tranding_menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
