{
    'name': 'Product Low Stock Alert',
    'version':  '18.0.1.0.1',
    'category': 'Inventory, Point of Sale, Warehouse, Productivity, Alert, Notification, Extra Tools',
    'summary': 'Avoid stockouts and ensure smooth operations with Product Low Stock Alert Odoo App. Receive timely notifications for low stock levels, configurable globally, per product, or by category. Includes visual indicators and real-time POS warnings. Compatible with Odoo 16, 17, and 18, supporting multi-user alerts. Product, Product Low Stock, Low Stock, Low Stock Alert, Product Low Stock Alert, product low stock email, low stock product alert, product minimum stock alerts, warehouse low stock alerts, display low stock quantity, product stock alert, Minimum Stock Reminder, Print product, Low Stock Report, Product Low Stock Notification, Inventory management, low stock alert, Stock alert system for online stores, Low inventory notification, Product Low Stock Alerts on Products, Minimum Stock Alerts, Minimum product stock alert, Minimum stock notification, low stock reminder, low stock level notifications, minimum stock email notifications apps for product, low stock alert on product, minimum stock alerts on product, low stock notification on product, minimum low stock reminder, minimum stock email alert inventory',
    'description':"""Product Low Stock Alert Odoo module provides a flexible low stock alert system to prevent disruptions and optimize your supply chain. Configure alerts globally, per product, or per category in Odoo Settings. Low stock items are visually highlighted in inventory views (List & Kanban) and the POS. Multi-user notifications ensure timely replenishment. Features a dynamic UI (Odoo 17+), multi-language support (EN, FR, ES, DE, JP), and compatibility with Odoo 16, 17, and 18. Improve efficiency and avoid stockouts with Product Low Stock Alert Odoo App.""",
    'author': 'Zehntech Technologies Inc.',
    'company': 'Zehntech Technologies Inc.',
    'maintainer': 'Zehntech Technologies Inc.',
    'contributor':' Zehntech Technologies Inc.',
    'website': 'https://www.zehntech.com/',
    'support': 'odoo-support@zehntech.com',
    "live_test_url": "https://zehntechodoo.com/app_name=zehntech_product_low_stock_alert/app_version=18.0",
    'depends': ['stock', 'point_of_sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/res_config_settings_views.xml',
        'views/product_product_views.xml',
        'views/product_category_views.xml',
        'views/inventory_low_stock_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zehntech_product_low_stock_alert/static/src/css/low_stock_style.css',   
        ],
        'point_of_sale._assets_pos': [
            'zehntech_product_low_stock_alert/static/src/js/pos_low_stock_alert.js',
        ],
         
    },
     "images": [
        "static/description/banner.png"
    ],
 
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
    'price':0.0,
    'currency': 'USD',
}
