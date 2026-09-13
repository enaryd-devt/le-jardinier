# PrimeTech Mass Bank Reconciliation (Odoo 18)

## Purpose

This module lets accounting users select multiple unreconciled bank transactions and
apply the same manual counterpart account to every transaction. Each transaction keeps
its own journal entry and audit trail; selected debits and credits are never reconciled
against one another.

## Installation and permissions

Install the module from **Apps**, then grant **Mass Bank Reconciliation User** to users
who may process transactions. The Manager role additionally exposes the immutable audit
log. Normal Accounting ACLs, journal access, company access, and account record rules
continue to apply.

## Use

1. Open Accounting / Bank transactions and select at least two compatible lines.
2. Choose **Actions / Mass Reconcile**.
3. Review count, debit/credit totals, journal, partner, currency, and line preview.
4. In **Counterpart account**, select an eligible account directly from the chart of
   accounts of the transaction company. Optionally enter a label and analytic distribution,
   then choose **Validate and Reconcile**.

The wizard can also gather unreconciled transactions for a chosen partner. Enable
**Match and apply a partner**: the partner selector then appears. Select the partner and
click **Gather Matching Transactions**. That partner is applied to every processed bank
transaction and counterpart. The search remains restricted to the reference company,
journal, transaction currency, debit/credit direction, posted entries, and unreconciled
transactions.

For example, 100 bank-charge transactions can each be reclassified from the bank
suspense account to account `627000` in one atomic request.

## Architecture and accounting behavior

The wizard uses Odoo 18's `account.bank.statement.line._seek_for_lines()` API to locate
the single suspense line of each already-posted, balanced statement move. It reclassifies
that line without changing debit, credit, `amount_currency`, or the liquidity line. This
is the standard manual-counterpart primitive and consequently delegates currency and
rounding behavior to Odoo. A persistent log records the user, date, lines, totals,
company, journal, and account.

## Safety and limitations

Selections must share company and bank/cash journal and must use compatible transaction
currencies. Every move must be posted, unreconciled, and contain exactly one standard
suspense line. Complex matches to invoices or moves already containing reconciliation
counterparts remain the responsibility of Odoo's interactive reconciliation interface.
The module deliberately offers only individual processing, not a grouped journal entry.
There are no manual commits; an exception rolls the complete RPC transaction back.
