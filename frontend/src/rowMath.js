// Shared cost/VAT/margin math for a single cart row, used by both the item
// grid (per-row display) and the app shell (grand total for the payment
// default). vatTemplates is the [{name, rate}] list from
// list_item_tax_templates.
import { flt } from "./format";

export function vatRate(vatTemplates, row) {
	const t = (vatTemplates || []).find((t) => t.name === row.vat_template);
	return t ? t.rate : 0;
}

export function rateIncl(vatTemplates, row) {
	return flt(row.rate_excl) * (1 + vatRate(vatTemplates, row) / 100);
}

export function costBasis(row) {
	return flt(row.rate_excl) * (1 - flt(row.discount_percentage) / 100);
}

export function vatAmount(vatTemplates, row) {
	return flt(row.qty) * costBasis(row) * (vatRate(vatTemplates, row) / 100);
}

// Margin is deliberately based on the VAT-inclusive landed cost, not the net
// cost - the accounting-correct basis would exclude VAT, but this business
// wants margin measured against what was actually paid out the door.
export function marginCostBasis(vatTemplates, row) {
	return costBasis(row) * (1 + vatRate(vatTemplates, row) / 100);
}

export function priceMargin(vatTemplates, row, price) {
	const sp = flt(price);
	if (!sp) return 0;
	return ((sp - marginCostBasis(vatTemplates, row)) / sp) * 100;
}

export function priceFromMargin(vatTemplates, row, targetMargin) {
	const tm = flt(targetMargin);
	if (tm >= 100) return 0;
	const cb = marginCostBasis(vatTemplates, row);
	if (!cb) return 0;
	return cb / (1 - tm / 100);
}

export function lineTotal(vatTemplates, row) {
	const net = flt(row.qty) * costBasis(row);
	return net * (1 + vatRate(vatTemplates, row) / 100);
}

export function grandTotal(vatTemplates, rows) {
	return (rows || []).reduce((sum, row) => sum + lineTotal(vatTemplates, row), 0);
}

export function itemsNetTotal(rows) {
	return (rows || []).reduce((sum, row) => sum + flt(row.qty) * costBasis(row), 0);
}

export function itemsVatTotal(vatTemplates, rows) {
	return (rows || []).reduce((sum, row) => sum + vatAmount(vatTemplates, row), 0);
}

// Mirrors the backend's "Apply Discount On: Net Total" behaviour (verified
// via bench execute): additional_discount_percentage scales net_total AND
// each item's tax proportionally by the same factor, then flat expenses are
// added on top untouched. This is what actually posts to the Purchase
// Invoice, so this total - not the item grid's own subtotal - is the one to
// show as the final payable amount.
export function billGrandTotal(vatTemplates, rows, discountPercentage, expenses) {
	const discountFactor = 1 - flt(discountPercentage) / 100;
	const netAfter = itemsNetTotal(rows) * discountFactor;
	const vatAfter = itemsVatTotal(vatTemplates, rows) * discountFactor;
	const expensesTotal = (expenses || []).reduce(
		(sum, e) => sum + (e.expense_account && flt(e.amount) > 0 ? flt(e.amount) : 0),
		0,
	);
	return netAfter + vatAfter + expensesTotal;
}
