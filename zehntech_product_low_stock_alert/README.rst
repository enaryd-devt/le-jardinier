================================================================
Product Low Stock Alert
================================================================

The **Product Low Stock Alert** module provides a comprehensive **Low Stock Alert System** in Odoo with flexible alert levels configurable **globally, per-product, or per-category**. Visual alerts are shown in both the **Inventory** and **Point of Sale (POS)** modules.

Table of contents
================================================================

.. contents::
   :local:

Key Features
================================================================

- **Global Configuration**: Define a default low stock threshold across the entire system. If per-product or per-category thresholds are not defined, the global setting will be used.
- **Per-Product Alert Configuration**: Configure individual alert quantities for each product variant. This takes the highest priority in the alert hierarchy.
- **Per-Category Alert Configuration**: Set low stock alert quantities per product category, applying to all products in that category unless overridden.
- **Low Stock Alerts in Inventory**: List and Kanban views of the Inventory show red visual indicators for products below the alert threshold using <decoration> XML and CSS styling.
- **POS Low Stock Alerts**: Products that are below the alert level in the Point of Sale (POS) module show a “Low Stock” badge using OWL and JavaScript logic.
- **Dynamic Settings Interface**: Admins can select the preferred alert method (Global / Per-Product / Per-Category) using radio buttons. Related fields dynamically appear or hide using the new <visibility> tag (Odoo 17+).
- **Multi-language Translation**: All translatable strings are available in English, French, Spanish, Japanese, and German.
- **Version Compatibility**: Developed for Odoo 17 Community Edition. Fully tested with Odoo 18 and includes downgrade scripts for Odoo 16 (on demand).
- **Sphinx Documentation and Kopyst Integration**: Includes usage documentation, index.rst, and internal onboarding content in Kopyst format.

Summary
================================================================

The **Product Low Stock Alert** module improves inventory and sales decision-making by visually highlighting products that fall below specified stock levels. Admins can configure alerts flexibly based on business needs and receive instant visual cues across Inventory and POS modules. The module is lightweight, modular, and easy to extend.

Installation
================================================================

1. Download or clone the repository to your Odoo `addons` directory.
2. Restart your Odoo server and upgrade the app list:
   ./odoo-bin -u product_low_stock_alert
3. Log in to Odoo and install the module via the Apps interface.
4. Ensure you have the proper user access rights enabled via Developer Mode.

How to use this module
================================================================

1. Navigate to **Settings > Low Stock Alert Configuration**.
2. Select an **Alert Method**:
   - **Global**: Use a system-wide low stock threshold.
   - **Per-Product**: Open any product variant and set its alert quantity.
   - **Per-Category**: Go to any product category and define its alert threshold.
3. Check the alert status in:
   - **Inventory > Products**:
     - Red warnings will appear in the List and Kanban views for low stock items.
   - **Point of Sale**:
     - Low stock items display a red “Low Stock” badge on the POS screen.

Alert Priority
================================================================

The alert logic follows this priority:

1. **Per-Product Setting**
2. **Per-Category Setting**
3. **Global Setting**

If a higher-level configuration is present, lower-level settings are ignored.

Technical Details
================================================================

- **Model Enhancements**:
  - `product.product`: Computed field `alert_state`.
  - `product.category`: New field `alert_quantity`.
  - `res.config.settings`: New fields for global alert configuration and method selection.

- **View Modifications**:
  - Product List and Kanban Views
  - Category Form View
  - POS Template using OWL (Odoo Web Library)
  - Settings Page with `<visibility>` tag support

- **JavaScript Integration**:
  - Lightweight JS for POS only
  - Uses OWL components to dynamically inject low stock warnings

Translations
================================================================

All strings are translated and available in the following languages:

- English
- French
- Spanish
- Japanese
- German

Translation files are located in the `i18n/` folder.

Contributors
================================================================

- Zehntech Technologies Inc.

Change logs
================================================================

[1.0.0]

* ``Added`` [21-05-2025] -  Product Low Stock Alert

Support
================================================================

https://www.zehntech.com/erp-crm/odoo-services/
