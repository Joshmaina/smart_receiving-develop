// Builds a receiving cart line from a get_item_receiving_context response,
// optionally overriding qty/rate/discount/tax (used when resuming a draft,
// where those values come from the saved PI rather than fresh defaults).
export function buildCartRow(context, overrides = {}) {
	const prices = {};
	for (const p of context.selling_prices || []) {
		prices[p.price_list] = p.price ?? 0;
	}
	return {
		item_code: context.item_code,
		item_name: context.item_name,
		stock_uom: context.stock_uom,
		current_stock: context.current_stock,
		qty: overrides.qty ?? 1,
		rate_excl: overrides.rate_excl ?? context.last_purchase_rate ?? 0,
		vat_template: overrides.vat_template ?? context.item_tax_template,
		discount_percentage: overrides.discount_percentage ?? 0,
		primary_price_list: context.primary_price_list,
		prices,
		expanded: false,
	};
}
