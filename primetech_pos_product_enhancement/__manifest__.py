{
    "name": "PrimeTech POS Product Enhancement",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Advanced product card UI with stock, pricing, margins and warehouse info in POS",
    "author": "PrimeTech Services",
    "depends": ["point_of_sale", "stock", "product"],
    "assets": {
    "point_of_sale._assets_pos": [

            "primetech_pos_product_enhancement/static/src/js/stock_color_service.js",
            "primetech_pos_product_enhancement/static/src/js/product_card_patch.js",
            "primetech_pos_product_enhancement/static/src/js/product_details_popup.js",

            "primetech_pos_product_enhancement/static/src/xml/product_card_templates.xml",
            "primetech_pos_product_enhancement/static/src/xml/product_details_popup.xml",

            "primetech_pos_product_enhancement/static/src/css/product_card_styles.css",
            "primetech_pos_product_enhancement/static/src/css/product_details_popup.css",
        ]
    },
    "installable": True,
    "application": False,
}

