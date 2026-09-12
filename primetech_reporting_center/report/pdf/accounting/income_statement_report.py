from odoo import fields, models

class IncomeStatementReport(models.AbstractModel):
    _name = 'report.primetech_reporting_center.income_statement_report'
    _description = 'Compte de Résultat OHADA Report'

    def _get_report_values(self, docids, data=None):
        data = data or {}
        wizard = self.env['primetech.income.statement.wizard'].browse(docids)
        report_data = self.env['primetech.income.statement'].get_income_statement(date_from=data.get('date_from'), date_to=data.get('date_to'), posted_only=data.get('posted_only'))
        return {'docs': wizard, 'data': report_data, 'date_from': data.get('date_from'), 'date_to': data.get('date_to'), 'generated_at': fields.Datetime.now().strftime('%d/%m/%Y %H:%M')}
