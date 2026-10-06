/** @odoo-module **/

import { DateTimeField, dateField } from "@web/views/fields/datetime/datetime_field";
import { registry } from "@web/core/registry";

/**
 * Date field dedicated to fiscal years.
 *
 * The value remains a real Odoo date (31 December of the selected year), but
 * only the year is shown to the user.  The XML field options limit the picker
 * itself to years, so no day or month has to be chosen.
 */
class PrimetechFiscalYearField extends DateTimeField {
    getFormattedValue(valueIndex) {
        const value = this.values[valueIndex];
        return value ? value.toFormat("yyyy") : "";
    }
}

registry.category("fields").add("primetech_fiscal_year", {
    ...dateField,
    component: PrimetechFiscalYearField,
});
