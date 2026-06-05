export function getStockColor(quantity) {
    if (quantity <= 0) return "red";
    if (quantity <= 5) return "orange";
    return "green";
}