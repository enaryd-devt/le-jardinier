{
    "name": "POS qty Display",
    "version": "1.0",
    "category": "Point of Sale",
    "summary": "Affiche la quantité disponible sur les cartes d'article du PDV",
    "author": "ChatGPT",
    "depends": ["point_of_sale", "stock"],
    'assets': {
        'point_of_sale._assets_pos': [
            "pos_show_qty/static/src/xml/pos_show_qty.xml",
            "pos_show_qty/static/src/xml/pos_bouton_item.xml",
            "pos_show_qty/static/src/xml/pos_show_price.xml",
            "pos_show_qty/static/src/js/pos_show_qty.js",            
            "pos_show_qty/static/src/js/pos_show_price.js",
            "pos_show_qty/static/src/css/pos_item.css",
            "pos_show_qty/static/src/js/price_list_button.js",
            "pos_show_qty/static/src/xml/price_list_button.xml",
            "pos_show_qty/static/src/css/price_list_button.css",
           


        ]
    },
    "installable": True,
    "auto_install": False,
}