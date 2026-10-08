{
    "name": "PrimeTech POS Product Enhancement",
    "version": "18.0.1.0.1",
    "category": "Point of Sale",
    "summary": "Advanced product card UI with stock, pricing, margins and warehouse info in POS",
    "author": "PrimeTech Services",
    "depends": ["point_of_sale", "stock", "product"],
    "data": [
        "views/pos_config_views.xml",
    ],
    "assets": {
    "point_of_sale._assets_pos": [

            "primetech_pos_product_enhancement/static/src/js/stock_color_service.js",
            "primetech_pos_product_enhancement/static/src/js/product_card_patch.js",
            "primetech_pos_product_enhancement/static/src/js/pos_order_line_stock_patch.js",
            "primetech_pos_product_enhancement/static/src/js/pos_interface_patch.js",
            "primetech_pos_product_enhancement/static/src/js/pos_payment_stock_reload.js",
            "primetech_pos_product_enhancement/static/src/js/pos_light_order_sync.js",

            "primetech_pos_product_enhancement/static/src/xml/product_card_templates.xml",
            "primetech_pos_product_enhancement/static/src/xml/pos_interface_templates.xml",
            "primetech_pos_product_enhancement/static/src/xml/product_info_popup_templates.xml",

            "primetech_pos_product_enhancement/static/src/css/product_card_styles.css",
            "primetech_pos_product_enhancement/static/src/css/pos_interface.css",
        ]
    },
    "installable": True,
    "application": False,
}

