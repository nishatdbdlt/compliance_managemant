# -*- coding: utf-8 -*-
{
    "name": "Trading",
    "version": "18.0.1.1.0",
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
- Unified Returns for Sales and Purchase
""",
    "author": "Custom Development",
    "category": "Sales",
    "depends": ["base", "mail",],
    "data": [
         "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/trd_cron_data.xml",
        "views/trd_product_catagory_views.xml",
        "views/trd_sales_views.xml",
        "views/trd_purchase_views.xml",
        "views/trd_stock_views.xml",
        "views/trd_vendor_views.xml",
        "views/trd_expense_views.xml",
        "views/trd_payment_views.xml",
        "views/trd_transaction_views.xml",
        "views/trd_product_views.xml",
        "views/trd_return_views.xml",
        "views/trd_menu_views.xml",
       
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
