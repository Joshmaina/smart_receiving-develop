<template>
	<div class="receiving-header">
		<label for="company-input" class="field">
			<span class="label-text">Company</span>
			<input id="company-input" name="company" type="text" value="BEVALI ONLINE" disabled autocomplete="off" aria-label="Company Name" />
		</label>
		<label for="supplier-input" class="field">
			<span class="label-text">Supplier *</span>
			<input id="supplier-input" name="supplier" list="supplier-options" v-model="header.supplier" placeholder="Choose supplier" autocomplete="off" aria-label="Supplier Name" />
			<datalist id="supplier-options">
				<option v-for="s in suppliers" :key="s.name" :value="s.name" />
			</datalist>
		</label>
		<label for="reference-no-input" class="field">
			<span class="label-text">Reference No</span>
			<input id="reference-no-input" name="reference_no" type="text" v-model="header.bill_no" placeholder="Supplier's invoice number" autocomplete="off" aria-label="Supplier Invoice Number" />
		</label>
		<label for="posting-date-input" class="field">
			<span class="label-text">Date</span>
			<input id="posting-date-input" name="posting_date" type="date" v-model="header.posting_date" autocomplete="off" aria-label="Invoice Posting Date" />
		</label>
		<label for="warehouse-select" class="field">
			<span class="label-text">Warehouse</span>
			<select id="warehouse-select" name="warehouse" v-model="header.warehouse" autocomplete="off" aria-label="Receiving Warehouse">
				<option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
			</select>
		</label>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { call } from "../api";

const header = defineModel({ required: true });

const suppliers = ref([]);
const warehouses = ref([]);

onMounted(async () => {
	suppliers.value = await call("frappe.client.get_list", {
		doctype: "Supplier",
		filters: { disabled: 0 },
		fields: ["name"],
		limit_page_length: 0,
		order_by: "name asc",
	});
	warehouses.value = await call("frappe.client.get_list", {
		doctype: "Warehouse",
		filters: { disabled: 0, is_group: 0, company: "BEVALI ONLINE" },
		fields: ["name"],
		limit_page_length: 0,
		order_by: "name asc",
	});
});
</script>

<style scoped>
.receiving-header {
	display: flex;
	gap: 16px;
	flex-wrap: wrap;
	padding: 16px 0 20px;
	border-bottom: 1px solid var(--dark-border-color, #e5e7eb);
	margin-bottom: 20px;
}
.field {
	display: flex;
	flex-direction: column;
	gap: 4px;
	min-width: 170px;
}
.field .label-text {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-muted, #6b7280);
	text-transform: uppercase;
	letter-spacing: 0.02em;
}
.field input,
.field select {
	padding: 8px 10px;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 6px;
	font-size: 14px;
}
.field input:disabled {
	background: var(--gray-100, #f4f5f6);
	color: var(--text-muted, #6b7280);
}
.field input:focus,
.field select:focus {
	outline: none;
	border-color: var(--primary, #5e64ff);
	box-shadow: 0 0 0 3px rgba(94, 100, 255, 0.15);
}
</style>
