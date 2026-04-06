# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
{
    'name': "Customer Credit Limit With Approval",
    'version': '18.0.0.0',
    'summary': """ Configure Credit Limit for Customers and approve from sales and account manager
    
    tus
    techultra
    techultra_private_limited_solution
    sales
    approval
    credit
    accounting 
    finance
    Odoo Customer Credit Limit
    Odoo Credit Limit Approval
    Customer Credit Approval Workflow Odoo
    Odoo Sales Order Approval
    Odoo Credit Limit Management
    Credit Limit with Multi-level Approval in Odoo
    Odoo Sales Credit Control
    Odoo Sales Order Blocking by Credit Limit
    Odoo Customer Outstanding Check
    Odoo Finance Approval Workflow
    Odoo Credit Risk Management
    Odoo ERP Sales Workflow
    Block Sales Order if Credit Exceeded Odoo
    Credit Limit Rules for Customers in Odoo
    Sales Manager Approval Odoo
    Odoo Approval Based on Due Amount
    Multi-step Sales Approval Odoo
    Odoo Email Notification for Credit Limit
    Reject Sales Order Odoo
    Odoo Customer Payment Control
    Odoo Credit Limit Approval Module
    Odoo Customer Credit Limit App
    Credit Limit Enforcement in Odoo
    Odoo Sales Order Credit Check
    Credit Control Workflow for Odoo
    Odoo Sales Credit Limit Management
    Customer-Specific Credit Limit Odoo
    Odoo Credit Limit Workflow with Email
    Multi-Level Sales Approval Odoo
    Odoo App for Sales Order Blocking
    credit limit
    customer credit
    email notification
    sales order
    account manager
    credit control
    erp
    odoo14
    odoo15
    odoo16
    odoo17
    odoo18
    odoo19
    Odoo customer credit limit
    Odoo credit limit approval module
    Odoo sales order credit check
    Odoo block sales order if credit exceeded
    Odoo sales order approval workflow
    Credit limit management for customers in Odoo
    Odoo automatic sales block based on dues
    Odoo financial approval for sales orders
    Credit limit enforcement in Odoo
    Customer credit approval Odoo module
    Odoo customer credit limit
    Odoo credit limit approval module
    Odoo sales order credit check
    Odoo block sales order if credit exceeded
    Odoo sales order approval workflow
    Credit limit management for customers in Odoo
    Odoo automatic sales block based on dues
    Odoo financial approval for sales orders
    Credit limit enforcement in Odoo
    Customer credit approval Odoo module
    
    
    """,
    'description': """ Activate and configure credit limit customer wise. If credit limit configured
    the system will warn or block the confirmation of a sales order if the existing due amount is greater
    than the configured warning or blocking credit limit.
     
    tus
    techultra
    techultra_private_limited_solution
    sales
    approval
    credit
    accounting 
    finance
    Odoo Customer Credit Limit
    Odoo Credit Limit Approval
    Customer Credit Approval Workflow Odoo
    Odoo Sales Order Approval
    Odoo Credit Limit Management
    Credit Limit with Multi-level Approval in Odoo
    Odoo Sales Credit Control
    Odoo Sales Order Blocking by Credit Limit
    Odoo Customer Outstanding Check
    Odoo Finance Approval Workflow
    Odoo Credit Risk Management
    Odoo ERP Sales Workflow
    Block Sales Order if Credit Exceeded Odoo
    Credit Limit Rules for Customers in Odoo
    Sales Manager Approval Odoo
    Odoo Approval Based on Due Amount
    Multi-step Sales Approval Odoo
    Odoo Email Notification for Credit Limit
    Reject Sales Order Odoo
    Odoo Customer Payment Control
    Odoo Credit Limit Approval Module
    Odoo Customer Credit Limit App
    Credit Limit Enforcement in Odoo
    Odoo Sales Order Credit Check
    Credit Control Workflow for Odoo
    Odoo Sales Credit Limit Management
    Customer-Specific Credit Limit Odoo
    Odoo Credit Limit Workflow with Email
    Multi-Level Sales Approval Odoo
    Odoo App for Sales Order Blocking
    credit limit
    customer credit
    email notification
    sales order
    account manager
    credit control
    erp
    odoo14
    odoo15
    odoo16
    odoo17
    odoo18
    odoo19
    Odoo customer credit limit
    Odoo credit limit approval module
    Odoo sales order credit check
    Odoo block sales order if credit exceeded
    Odoo sales order approval workflow
    Credit limit management for customers in Odoo
    Odoo automatic sales block based on dues
    Odoo financial approval for sales orders
    Credit limit enforcement in Odoo
    Customer credit approval Odoo module
    Odoo customer credit limit
    Odoo credit limit approval module
    Odoo sales order credit check
    Odoo block sales order if credit exceeded
    Odoo sales order approval workflow
    Credit limit management for customers in Odoo
    Odoo automatic sales block based on dues
    Odoo financial approval for sales orders
    Credit limit enforcement in Odoo
    Customer credit approval Odoo module
    
     """,
    'author': "TechUltra Solutions Private Limited",
    'company': 'TechUltra Solutions Private Limited',
    'website': "https://www.techultrasolutions.com/",
    'category': 'Sales',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/credit_limit_approval_mail.xml',
        'wizard/warning_wizard.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
    ],
    'images': [
        'static/description/main_screen.gif',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
}
