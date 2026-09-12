from odoo import models

class IncomeStatementXlsx(models.AbstractModel):
    _name = 'report.primetech_reporting_center.income_statement_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Compte de Résultat OHADA XLSX'

    def generate_xlsx_report(self, workbook, data, wizard):
        report_data = self.env['primetech.income.statement'].get_income_statement(date_from=data.get('date_from'), date_to=data.get('date_to'), posted_only=data.get('posted_only'))
        sheet = workbook.add_worksheet('Compte Resultat')
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'border': 1})
        header = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#D9D9D9'})
        text = workbook.add_format({'border': 1})
        amount = workbook.add_format({'border': 1, 'num_format': '#,##0', 'align': 'right'})
        subtotal_text = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9D9D9'})
        subtotal_amount = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9D9D9', 'num_format': '#,##0', 'align': 'right'})
        sheet.set_column('A:A', 10)
        sheet.set_column('B:B', 60)
        sheet.set_column('C:C', 8)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:F', 20)
        row = 0
        sheet.merge_range(row, 0, row, 5, 'COMPTE DE RESULTAT OHADA', title)
        row += 2
        sheet.write(row, 0, 'REF', header)
        sheet.write(row, 1, 'LIBELLES', header)
        sheet.write(row, 2, '+/-', header)
        sheet.write(row, 3, 'NOTE', header)
        sheet.write(row, 4, 'EXERCICE N', header)
        sheet.write(row, 5, 'EXERCICE N-1', header)
        row += 1
        for line in report_data['lines']:
            if line['line_type'] == 'subtotal':
                txt_fmt = subtotal_text
                amt_fmt = subtotal_amount
            else:
                txt_fmt = text
                amt_fmt = amount
            sheet.write(row, 0, line.get('ref', ''), txt_fmt)
            sheet.write(row, 1, line.get('label', ''), txt_fmt)
            sheet.write(row, 2, line.get('sign', ''), txt_fmt)
            sheet.write(row, 3, line.get('note', ''), txt_fmt)
            sheet.write_number(row, 4, line.get('amount', 0.0), amt_fmt)
            sheet.write_number(row, 5, line.get('amount_n1', 0.0), amt_fmt)
            row += 1
        row += 2
        sheet.merge_range(row, 0, row, 3, 'RESULTAT NET', subtotal_text)
        sheet.write_number(row, 4, report_data['resultat_net'], subtotal_amount)
