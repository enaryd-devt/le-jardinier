from odoo import models
from .income_statement_mapping import INCOME_STATEMENT_STRUCTURE

class IncomeStatement(models.AbstractModel):
    _name = 'primetech.income.statement'
    _description = 'Compte de Résultat OHADA'

    def _compute_amount(self, accounts, date_from, date_to, posted_only=True):
        domain = [('date', '>=', date_from), ('date', '<=', date_to)]
        if posted_only:
            domain.append(('move_id.state', '=', 'posted'))
        move_lines = self.env['account.move.line'].search(domain)
        amount = 0.0
        for line in move_lines:
            account_code = line.account_id.code or ''
            if any((account_code.startswith(prefix) for prefix in accounts)):
                amount += line.credit - line.debit
        return amount

    def get_income_statement(self, date_from, date_to, posted_only=True):
        date_from_n1 = date_from.replace(year=date_from.year - 1)
        date_to_n1 = date_to.replace(year=date_to.year - 1)
        values_n = {}
        values_n1 = {}
        for item in INCOME_STATEMENT_STRUCTURE:
            if item['type'] != 'line':
                continue
            amount_n = self._compute_amount(item['accounts'], date_from, date_to, posted_only)
            amount_n1 = self._compute_amount(item['accounts'], date_from_n1, date_to_n1, posted_only)
            if item['sign'] == '-':
                amount_n *= -1
                amount_n1 *= -1
            values_n[item['ref']] = amount_n
            values_n1[item['ref']] = amount_n1
        values_n['XA'] = values_n.get('TA', 0.0) - values_n.get('RA', 0.0) - values_n.get('RB', 0.0)
        values_n1['XA'] = values_n1.get('TA', 0.0) - values_n1.get('RA', 0.0) - values_n1.get('RB', 0.0)
        values_n['XB'] = values_n.get('TB', 0.0) + values_n.get('TC', 0.0) + values_n.get('TD', 0.0)
        values_n1['XB'] = values_n1.get('TB', 0.0) + values_n1.get('TC', 0.0) + values_n1.get('TD', 0.0)
        values_n['XC'] = values_n['XA'] + values_n['XB'] + values_n.get('TE', 0.0) + values_n.get('TF', 0.0) + values_n.get('TG', 0.0) + values_n.get('TH', 0.0) + values_n.get('TI', 0.0) - values_n.get('RC', 0.0) - values_n.get('RD', 0.0) - values_n.get('RE', 0.0) - values_n.get('RF', 0.0) - values_n.get('RG', 0.0) - values_n.get('RH', 0.0) - values_n.get('RI', 0.0) - values_n.get('RJ', 0.0)
        values_n1['XC'] = values_n1['XA'] + values_n1['XB'] + values_n1.get('TE', 0.0) + values_n1.get('TF', 0.0) + values_n1.get('TG', 0.0) + values_n1.get('TH', 0.0) + values_n1.get('TI', 0.0) - values_n1.get('RC', 0.0) - values_n1.get('RD', 0.0) - values_n1.get('RE', 0.0) - values_n1.get('RF', 0.0) - values_n1.get('RG', 0.0) - values_n1.get('RH', 0.0) - values_n1.get('RI', 0.0) - values_n1.get('RJ', 0.0)
        values_n['XD'] = values_n['XC'] - values_n.get('RK', 0.0)
        values_n1['XD'] = values_n1['XC'] - values_n1.get('RK', 0.0)
        values_n['XE'] = values_n['XD'] - values_n.get('RL', 0.0)
        values_n1['XE'] = values_n1['XD'] - values_n1.get('RL', 0.0)
        values_n['XF'] = values_n.get('TK', 0.0) - values_n.get('RN', 0.0)
        values_n1['XF'] = values_n1.get('TK', 0.0) - values_n1.get('RN', 0.0)
        values_n['XH'] = values_n.get('TN', 0.0) - values_n.get('RP', 0.0)
        values_n1['XH'] = values_n1.get('TN', 0.0) - values_n1.get('RP', 0.0)
        values_n['XI'] = values_n['XE'] + values_n['XF'] + values_n['XH'] - values_n.get('RQ', 0.0) - values_n.get('RS', 0.0)
        values_n1['XI'] = values_n1['XE'] + values_n1['XF'] + values_n1['XH'] - values_n1.get('RQ', 0.0) - values_n1.get('RS', 0.0)
        lines = []
        for item in INCOME_STATEMENT_STRUCTURE:
            ref = item['ref']
            if item['type'] == 'line':
                lines.append({'ref': ref, 'label': item['label'], 'sign': item.get('sign', ''), 'note': item.get('note', ''), 'amount': values_n.get(ref, 0.0), 'amount_n1': values_n1.get(ref, 0.0), 'line_type': 'subtotal'})
            else:
                lines.append({'ref': ref, 'label': item['label'], 'sign': '', 'note': '', 'amount': values_n.get(ref, 0.0), 'amount_n1': values_n1.get(ref, 0.0), 'line_type': 'subtotal'})
        return {'lines': lines, 'year_n': date_to.year, 'year_n1': date_to.year - 1, 'resultat_net': values_n.get('XI', 0.0)}
