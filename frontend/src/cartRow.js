// Builds a receiving cart line from a get_item_receiving_context response,
// optionally overriding qty/rate/discount/tax/uom (used when resuming a draft,
// where those values come from the saved PI rather than fresh defaults).
export function buildCartRow(context, overrides = {}) {
	const prices = {};
	for (const p of context.selling_prices || []) {
		prices[p.price_list] = p.price ?? 0;
	}
	const uoms = context.uoms || [{ uom: context.stock_uom, conversion_factor: 1.0 }];
	const defaultUom = overrides.uom || context.default_purchase_uom || context.stock_uom;
	const selectedUomObj = uoms.find((u) => u.uom === defaultUom) || uoms[0] || { uom: context.stock_uom, conversion_factor: 1.0 };

	return {
		item_code: context.item_code,
		item_name: context.item_name,
		stock_uom: context.stock_uom,
		current_stock: context.current_stock,
		uom: selectedUomObj.uom,
		conversion_factor: overrides.conversion_factor ?? selectedUomObj.conversion_factor ?? 1.0,
		available_uoms: uoms,
		is_multi_uom: context.is_multi_uom ?? (uoms.length > 1),
		po_qty: overrides.po_qty ?? context.po_qty ?? 0,
		qty: overrides.qty ?? 1,
		rate_excl: overrides.rate_excl ?? context.last_purchase_rate ?? 0,
		vat_template: overrides.vat_template ?? context.item_tax_template,
		discount_percentage: overrides.discount_percentage ?? 0,
		primary_price_list: context.primary_price_list,
		prices,
		expanded: false,
	};
}
