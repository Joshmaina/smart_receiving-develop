<template>
	<div class="item-grid">
		<div class="search-box">
			<span class="search-icon">&#128269;</span>
			<input
				id="item-search-input"
				name="item_search"
				ref="searchInputRef"
				type="text"
				v-model="searchTerm"
				placeholder="Search item by code, name, or scan barcode..."
				autocomplete="off"
				aria-label="Search item by code, name, or scan barcode"
				@input="onSearchInput"
				@keydown.enter.prevent="onSearchEnter"
			/>
			<ul v-if="searchResults.length" class="search-results">
				<li v-for="r in searchResults" :key="r.item_code" @click="addItem(r.item_code)">
					<strong>{{ r.item_code }}</strong> - {{ r.item_name }}
					<span class="muted">({{ r.current_stock }} {{ r.stock_uom }} in stock)</span>
				</li>
			</ul>
		</div>

		<table v-if="items.length" class="grid-table">
			<thead>
				<tr>
					<th></th>
					<th>Item</th>
					<th>Recv Qty</th>
					<th>Cost (Excl. VAT)</th>
					<th>VAT</th>
					<th>Cost (Incl. VAT)</th>
					<th>Disc %</th>
					<th>Line Total</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				<template v-for="(row, idx) in items" :key="row.item_code">
					<tr class="item-row">
						<td class="expand-cell">
							<button type="button" class="icon-btn" @click="row.expanded = !row.expanded">
								{{ row.expanded ? "▼" : "▶" }}
							</button>
						</td>
						<td>
							<div class="item-name">{{ row.item_code }} - {{ row.item_name }}</div>
							<div class="muted">Stock: {{ row.current_stock }} {{ row.stock_uom }}</div>
						</td>
						<td class="recv-qty-cell">
							<div class="qty-uom-wrap">
								<input
									:id="'qty-input-' + row.item_code"
									:name="'qty_' + row.item_code"
									type="number"
									min="0"
									step="any"
									v-model.number="row.qty"
									class="num"
									placeholder="0.00"
									:aria-label="'Received Quantity for ' + row.item_code"
								/>
								<select
									v-if="row.available_uoms && row.available_uoms.length > 1"
									:id="'uom-select-' + row.item_code"
									:name="'uom_' + row.item_code"
									v-model="row.uom"
									@change="onUomSelectChange(row)"
									class="uom-select"
									:aria-label="'Unit of Measure for ' + row.item_code"
								>
									<option v-for="u in row.available_uoms" :key="u.uom" :value="u.uom">
										{{ u.label }}
									</option>
								</select>
								<span v-else class="uom-label">{{ row.uom || row.stock_uom }}</span>
							</div>
							<div class="qty-steppers">
								<button type="button" class="stepper-btn" @click="adjustQty(row, -1)" title="Decrease Qty">-1</button>
								<button type="button" class="stepper-btn" @click="adjustQty(row, 1)" title="Increase Qty by 1">+1</button>
								<button type="button" class="stepper-btn" @click="adjustQty(row, 5)" title="Increase Qty by 5">+5</button>
								<button type="button" class="stepper-btn" @click="adjustQty(row, 10)" title="Increase Qty by 10">+10</button>
							</div>
							<div v-if="row.conversion_factor > 1 || (row.uom && row.uom !== row.stock_uom)" class="uom-hint muted">
								⚡ Equivalent: <strong>{{ round2(flt(row.qty) * flt(row.conversion_factor)) }} {{ row.stock_uom }}</strong> ({{ row.conversion_factor }} {{ row.stock_uom }}/{{ row.uom }})
							</div>
						</td>
						<td>
							<MoneyInput
								:id="'cost-excl-' + row.item_code"
								:name="'cost_excl_' + row.item_code"
								:aria-label="'Cost Excluding VAT for ' + row.item_code"
								:value="round2(row.rate_excl)"
								@input="onExclInput(row, $event.target.value)"
							/>
						</td>
						<td class="vat-cell">
							<select
								:id="'vat-select-' + row.item_code"
								:name="'vat_' + row.item_code"
								v-model="row.vat_template"
								:aria-label="'VAT Template for ' + row.item_code"
							>
								<option v-for="t in vatTemplates" :key="t.name" :value="t.name">
									{{ t.name }} ({{ t.rate }}%)
								</option>
							</select>
							<span :class="['tax-badge', taxBadgeClass(row.vat_template)]">
								{{ taxBadgeLabel(row.vat_template) }}
							</span>
							<div class="vat-amount muted">{{ money(vatAmount(row)) }}</div>
						</td>
						<td>
							<MoneyInput
								:id="'cost-incl-' + row.item_code"
								:name="'cost_incl_' + row.item_code"
								:aria-label="'Cost Including VAT for ' + row.item_code"
								:value="round2(rateIncl(row))"
								@input="onInclInput(row, $event.target.value)"
							/>
						</td>
						<td>
							<input
								:id="'discount-input-' + row.item_code"
								:name="'discount_' + row.item_code"
								type="number"
								min="0"
								max="100"
								step="any"
								v-model.number="row.discount_percentage"
								class="num"
								:aria-label="'Discount percentage for ' + row.item_code"
							/>
						</td>
						<td class="line-total">{{ money(lineTotal(row)) }}</td>
						<td><button type="button" class="icon-btn danger" @click="$emit('remove', idx)">&times;</button></td>
					</tr>
					<tr v-if="row.expanded" class="price-panel-row">
						<td></td>
						<td colspan="8">
							<div class="price-panel">
								<div class="price-panel-header">
									<div class="price-panel-title">Selling prices &amp; Profit Margins</div>
									<div class="target-margin-tools">
										<label :for="'target-margin-' + row.item_code" class="target-margin-label">
											<span>⚡ Quick Target Margin %:</span>
											<input
												:id="'target-margin-' + row.item_code"
												type="number"
												min="0"
												max="99"
												step="any"
												v-model.number="row.target_margin"
												placeholder="e.g. 35"
												class="num target-margin-input"
												@input="applyTargetMargin(row)"
											/>
										</label>
										<button type="button" class="preset-btn" @click="applyTargetMargin(row, 25)">25%</button>
										<button type="button" class="preset-btn" @click="applyTargetMargin(row, 30)">30%</button>
										<button type="button" class="preset-btn" @click="applyTargetMargin(row, 35)">35%</button>
										<button type="button" class="preset-btn" @click="applyTargetMargin(row, 40)">40%</button>
									</div>
								</div>
								<div class="price-panel-grid">
									<label v-for="(value, priceList) in row.prices" :key="priceList" :for="'price-' + row.item_code + '-' + priceList.replace(/\s+/g, '-').toLowerCase()" class="price-field">
										<span>
											{{ priceList }}
											<em v-if="priceList === row.primary_price_list">(primary)</em>
										</span>
										<MoneyInput
											:id="'price-' + row.item_code + '-' + priceList.replace(/\s+/g, '-').toLowerCase()"
											:name="'price_' + row.item_code + '_' + priceList.replace(/\s+/g, '_').toLowerCase()"
											:aria-label="'Selling price for ' + priceList + ' for ' + row.item_code"
											:value="round2(row.prices[priceList])"
											@input="row.prices[priceList] = flt($event.target.value)"
										/>
										<span :class="['margin-badge', marginBadgeClass(priceMargin(row, value))]">
											Margin: {{ round2(priceMargin(row, value)) }}%
										</span>
									</label>
								</div>
							</div>
						</td>
					</tr>
				</template>
			</tbody>
			<tfoot>
				<tr>
					<td colspan="7" class="totals-label">Totals</td>
					<td class="totals-value">{{ money(grandTotal) }}</td>
					<td></td>
				</tr>
			</tfoot>
		</table>
		<p v-else class="empty">No items added yet. Search or scan barcode above to add one.</p>
	</div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { call } from "../api";
import { buildCartRow } from "../cartRow";
import { flt, round2, money } from "../format";
import * as rowMath from "../rowMath";
import MoneyInput from "./MoneyInput.vue";

const props = defineProps({
	items: { type: Array, required: true },
	warehouse: { type: String, required: true },
	vatTemplates: { type: Array, required: true },
});
const emit = defineEmits(["add", "remove"]);

const searchInputRef = ref(null);
const searchTerm = ref("");
const searchResults = ref([]);
let searchDebounce = null;

onMounted(() => {
	searchInputRef.value?.focus();
});

function focusSearch() {
	nextTick(() => {
		searchInputRef.value?.focus();
	});
}

defineExpose({ focusSearch });

function adjustQty(row, delta) {
	const current = flt(row.qty) || 0;
	row.qty = Math.max(1, current + delta);
}

function handleUomChange(row) {
	const selected = (row.available_uoms || []).find((u) => u.uom === row.uom);
	if (selected) {
		row.conversion_factor = flt(selected.conversion_factor || 1.0);
	}
}

function onUomSelectChange(row) {
	handleUomChange(row);
}

function onSearchInput() {
	clearTimeout(searchDebounce);
	const term = searchTerm.value.trim();
	if (!term) {
		searchResults.value = [];
		return;
	}
	searchDebounce = setTimeout(async () => {
		searchResults.value = await call("smart_receiving.smart_receiving.api.receiving.search_items", {
			term,
			warehouse: props.warehouse,
		});
	}, 200);
}

async function onSearchEnter() {
	if (searchResults.value.length > 0) {
		await addItem(searchResults.value[0].item_code);
	} else if (searchTerm.value.trim()) {
		const results = await call("smart_receiving.smart_receiving.api.receiving.search_items", {
			term: searchTerm.value.trim(),
			warehouse: props.warehouse,
		});
		if (results.length > 0) {
			await addItem(results[0].item_code);
		}
	}
}

async function addItem(item_code) {
	const existing = props.items.find((i) => i.item_code === item_code);
	if (existing) {
		existing.qty = (flt(existing.qty) || 0) + 1;
	} else {
		const context = await call("smart_receiving.smart_receiving.api.receiving.get_item_receiving_context", {
			item_code,
			warehouse: props.warehouse,
		});
		emit("add", buildCartRow(context));
	}
	searchTerm.value = "";
	searchResults.value = [];
	focusSearch();
}

function taxBadgeLabel(templateName) {
	if (!templateName) return "V - BO";
	if (templateName.startsWith("V")) return "V - 16%";
	if (templateName.startsWith("E")) return "E - Exempt";
	if (templateName.startsWith("Z")) return "Z - 0%";
	return templateName;
}

function taxBadgeClass(templateName) {
	if (!templateName || templateName.startsWith("V")) return "badge-vat";
	if (templateName.startsWith("E")) return "badge-exempt";
	if (templateName.startsWith("Z")) return "badge-zero";
	return "badge-vat";
}

function rateIncl(row) {
	return rowMath.rateIncl(props.vatTemplates, row);
}
function vatAmount(row) {
	return rowMath.vatAmount(props.vatTemplates, row);
}
function priceMargin(row, price) {
	return rowMath.priceMargin(props.vatTemplates, row, price);
}

function marginBadgeClass(margin) {
	const m = flt(margin);
	if (m >= 30) return "margin-badge-high";
	if (m >= 15) return "margin-badge-mid";
	return "margin-badge-low";
}

function applyTargetMargin(row, presetMargin = null) {
	if (presetMargin !== null && presetMargin !== undefined) {
		row.target_margin = presetMargin;
	}
	const tm = flt(row.target_margin);
	if (tm > 0 && tm < 100) {
		const newPrice = rowMath.priceFromMargin(props.vatTemplates, row, tm);
		if (newPrice > 0) {
			const primaryList = row.primary_price_list;
			if (primaryList && row.prices[primaryList] !== undefined) {
				row.prices[primaryList] = round2(newPrice);
			} else {
				for (const pl of Object.keys(row.prices)) {
					row.prices[pl] = round2(newPrice);
				}
			}
		}
	}
}
function lineTotal(row) {
	return rowMath.lineTotal(props.vatTemplates, row);
}

function onExclInput(row, value) {
	row.rate_excl = flt(value);
}
function onInclInput(row, value) {
	const rate = 1 + rowMath.vatRate(props.vatTemplates, row) / 100;
	row.rate_excl = rate ? flt(value) / rate : 0;
}
const grandTotal = computed(() => rowMath.grandTotal(props.vatTemplates, props.items));
</script>

<style scoped>
.item-grid {
	position: relative;
}
.search-box {
	position: relative;
	margin-bottom: 20px;
}
.search-icon {
	position: absolute;
	left: 14px;
	top: 50%;
	transform: translateY(-50%);
	opacity: 0.5;
	pointer-events: none;
}
.search-box input {
	width: 100%;
	max-width: 520px;
	padding: 12px 14px 12px 40px;
	font-size: 15px;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 8px;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
	background: var(--card-bg, #ffffff);
	color: var(--text-color, #1f2937);
}
.search-box input:focus {
	outline: none;
	border-color: var(--primary, #5e64ff);
	box-shadow: 0 0 0 3px rgba(94, 100, 255, 0.15);
}
.search-results {
	position: absolute;
	z-index: 10;
	background: var(--card-bg, #ffffff);
	color: var(--text-color, #1f2937);
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 8px;
	list-style: none;
	margin: 4px 0 0;
	padding: 4px 0;
	max-width: 520px;
	max-height: 260px;
	overflow-y: auto;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.search-results li {
	padding: 8px 14px;
	cursor: pointer;
}
.search-results li:hover {
	background: var(--gray-100, #f4f5f6);
}
.search-results .muted {
	font-size: 12px;
}

.grid-table {
	border-collapse: collapse;
	width: 100%;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 8px;
	overflow: hidden;
	background: var(--card-bg, #ffffff);
	color: var(--text-color, #1f2937);
}
.grid-table th {
	background: var(--gray-100, #f4f5f6);
	font-size: 12px;
	text-transform: uppercase;
	letter-spacing: 0.02em;
	color: var(--text-muted, #6b7280);
}
.grid-table th,
.grid-table td {
	border: 1px solid var(--dark-border-color, #e5e7eb);
	padding: 8px 10px;
	text-align: left;
	vertical-align: middle;
}
.item-row:hover {
	background: var(--gray-50, #fafbfc);
}
.row-over-po {
	background: #fef2f2 !important;
	border-left: 4px solid #ef4444 !important;
}
.po-qty-cell {
	text-align: center;
	font-weight: 500;
}
.item-name {
	font-weight: 500;
}
.muted {
	color: var(--text-muted, #888);
	font-size: 12px;
}
input.num {
	width: 90px;
	padding: 5px 6px;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 4px;
	text-align: right;
	background: var(--card-bg, #ffffff);
	color: var(--text-color, #1f2937);
}
.vat-cell select {
	width: 100%;
	min-width: 120px;
	padding: 5px 6px;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 4px;
	background: var(--card-bg, #ffffff);
	color: var(--text-color, #1f2937);
}
.vat-amount {
	margin-top: 4px;
	text-align: right;
}
.tax-badge {
	display: inline-block;
	font-size: 10px;
	font-weight: 700;
	padding: 2px 6px;
	border-radius: 4px;
	margin-top: 4px;
	text-transform: uppercase;
}
.badge-vat {
	background: #e0e7ff;
	color: #3730a3;
}
.badge-exempt {
	background: #fef3c7;
	color: #92400e;
}
.badge-zero {
	background: #d1fae5;
	color: #065f46;
}
.line-total {
	font-weight: 600;
	text-align: right;
}
.icon-btn {
	border: none;
	background: transparent;
	cursor: pointer;
	font-size: 14px;
	padding: 4px 8px;
	border-radius: 4px;
	color: var(--text-color, #1f2937);
}
.icon-btn:hover {
	background: var(--gray-100, #f4f5f6);
}
.icon-btn.danger {
	color: var(--red-500, #c0392b);
}
.expand-cell {
	text-align: center;
}
.price-panel-row td {
	background: var(--gray-50, #fafbfc);
}
.price-panel {
	padding: 10px 4px;
}
.price-panel-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	flex-wrap: wrap;
	gap: 12px;
	margin-bottom: 12px;
}
.target-margin-tools {
	display: flex;
	align-items: center;
	gap: 6px;
}
.target-margin-label {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 12px;
	font-weight: 500;
	color: var(--text-color, #1f2937);
}
.target-margin-input {
	width: 70px !important;
	padding: 3px 6px !important;
	text-align: right;
}
.preset-btn {
	background: var(--gray-100, #f4f5f6);
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 4px;
	padding: 2px 8px;
	font-size: 11px;
	font-weight: 600;
	cursor: pointer;
	color: var(--text-color, #1f2937);
	transition: background 0.15s ease, border-color 0.15s ease;
}
.preset-btn:hover {
	background: var(--primary, #5e64ff);
	color: #ffffff;
	border-color: var(--primary, #5e64ff);
}
.price-panel-title {
	font-weight: 600;
	font-size: 12px;
	text-transform: uppercase;
	color: var(--text-muted, #6b7280);
	margin-bottom: 0;
}
.price-panel-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 16px;
}
.price-field {
	display: flex;
	flex-direction: column;
	gap: 4px;
	font-size: 13px;
}
.price-field em {
	color: var(--primary, #5e64ff);
	font-style: normal;
	font-weight: 600;
}
.margin-hint {
	font-size: 11px;
}
.margin-badge {
	display: inline-block;
	font-size: 11px;
	font-weight: 700;
	padding: 2px 8px;
	border-radius: 4px;
	margin-top: 4px;
	letter-spacing: 0.02em;
}
.totals-label {
	text-align: right;
	font-weight: 700;
}
.totals-value {
	font-weight: 700;
	text-align: right;
}
.empty {
	color: var(--text-muted, #777);
}
</style>

<style>
.item-row {
	transition: background-color 0.15s ease, border-color 0.15s ease;
}
.item-row:focus-within {
	background-color: #f0fdf4 !important;
	border-left: 4px solid var(--primary, #5e64ff) !important;
}
.row-over-po {
	background-color: #fef2f2 !important;
	border-left: 4px solid #ef4444 !important;
}
.tax-badge {
	display: inline-block;
	font-size: 11px;
	font-weight: 700;
	padding: 3px 8px;
	border-radius: 4px;
	margin-top: 4px;
	text-transform: uppercase;
	letter-spacing: 0.03em;
}
.badge-vat {
	background-color: #e0e7ff !important;
	color: #3730a3 !important;
	border: 1px solid #c7d2fe !important;
}
.badge-exempt {
	background-color: #fef3c7 !important;
	color: #92400e !important;
	border: 1px solid #fde68a !important;
}
.badge-zero {
	background-color: #d1fae5 !important;
	color: #065f46 !important;
	border: 1px solid #a7f3d0 !important;
}
.margin-badge-high {
	background-color: #d1fae5 !important;
	color: #065f46 !important;
	border: 1px solid #a7f3d0 !important;
}
.margin-badge-mid {
	background-color: #fef3c7 !important;
	color: #92400e !important;
	border: 1px solid #fde68a !important;
}
.margin-badge-low {
	background-color: #fee2e2 !important;
	color: #991b1b !important;
	border: 1px solid #fca5a5 !important;
}
.qty-steppers {
	display: flex;
	gap: 3px;
	margin-top: 4px;
}
.stepper-btn {
	background: var(--gray-100, #f4f5f6);
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 3px;
	padding: 1px 5px;
	font-size: 10px;
	font-weight: 700;
	cursor: pointer;
	color: var(--text-color, #1f2937);
	transition: background 0.15s ease, border-color 0.15s ease;
}
.stepper-btn:hover {
	background: var(--primary, #5e64ff);
	color: #ffffff;
	border-color: var(--primary, #5e64ff);
}
</style>

