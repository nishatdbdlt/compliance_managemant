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
        "views/trd_product_catagory.xml",
        "views/trd_sales.xml",
        "views/trd_purchase.xml",
        'views/trd_stock.xml',
        'views/trd_vendor.xml',
        'views/trd_expense.xml',
        'views/trd_payment.xml',
        'views/trd_product.xml',
        "views/trd_menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
