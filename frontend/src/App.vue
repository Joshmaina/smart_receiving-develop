<template>
	<div class="smart-receiving-app">
		<ReceivingHeader v-model="header" />

		<div v-if="currentDraftName" class="editing-banner">
			Editing draft <strong>{{ currentDraftName }}</strong>
			<button type="button" @click="resetForm">Discard &amp; start new</button>
		</div>

		<ItemGrid
			:items="cartItems"
			:warehouse="header.warehouse"
			:vat-templates="vatTemplates"
			@add="onAddItem"
			@remove="onRemoveItem"
		/>

		<div class="bill-block">
			<div class="bill-block-title">Bill</div>
			<div class="bill-row">
				<div class="field">
					<label>Additional Discount %</label>
					<input type="number" min="0" max="100" step="any" v-model.number="bill.discount_percentage" class="num" />
				</div>
			</div>

			<div class="expenses">
				<div v-for="(exp, idx) in bill.additional_expenses" :key="idx" class="expense-row">
					<select v-model="exp.expense_account">
						<option value="" disabled>Choose expense account</option>
						<option v-for="a in expenseAccounts" :key="a.name" :value="a.name">{{ a.name }}</option>
					</select>
					<MoneyInput :value="exp.amount" @input="exp.amount = flt($event.target.value)" />
					<input type="text" v-model="exp.description" placeholder="Description (optional)" />
					<button type="button" class="icon-btn danger" @click="bill.additional_expenses.splice(idx, 1)">
						&times;
					</button>
				</div>
				<button type="button" class="link-btn" @click="addExpenseRow">+ Add expense (freight, handling, etc.)</button>
			</div>
		</div>

		<div class="grand-total-bar">
			<span>Total Payable (incl. VAT &amp; expenses)</span>
			<strong>{{ money(finalGrandTotal) }}</strong>
		</div>

		<div class="financial-breakdown-panel">
			<div class="breakdown-title">Financial Breakdown Audit</div>
			<div class="breakdown-row">
				<span>Items Net Subtotal:</span>
				<strong>{{ money(calcNetTotal()) }}</strong>
			</div>
			<div v-if="calcDiscountAmount() > 0" class="breakdown-row discount">
				<span>Discount Amount Deducted ({{ bill.discount_percentage }}%):</span>
				<strong>-{{ money(calcDiscountAmount()) }}</strong>
			</div>
			<div class="breakdown-row">
				<span>VAT Total (16% / Exempt / 0%):</span>
				<strong>{{ money(calcVatTotal()) }}</strong>
			</div>
			<div v-for="(exp, idx) in bill.additional_expenses" :key="idx" class="breakdown-row expense">
				<span>Expense: {{ exp.description || exp.expense_account }}</span>
				<strong>+{{ money(flt(exp.amount)) }}</strong>
			</div>
			<div class="breakdown-row grand-total-row">
				<span>Calculated Grand Total:</span>
				<strong>{{ money(finalGrandTotal) }}</strong>
			</div>
			<div v-if="reconciliationWarning" class="reconciliation-warning">
				⚠️ {{ reconciliationWarning }}
			</div>
		</div>

		<div v-if="currentDraftName" class="attach-block">
			<div class="bill-block-title">Supplier Invoice Document</div>
			<ul v-if="attachedFiles.length" class="attached-files">
				<li v-for="f in attachedFiles" :key="f.name">
					<a :href="f.file_url" target="_blank">{{ f.file_name }}</a>
				</li>
			</ul>
			<input type="file" @change="onAttachFile" />
			<span v-if="attaching" class="muted">Uploading...</span>
			<span v-if="attachError" class="error">{{ attachError }}</span>
		</div>
		<p v-else class="muted attach-hint">Save as Draft first to attach the supplier's invoice document.</p>

		<div v-if="currentDraftName" class="kra-block">
			<div class="bill-block-title">KRA Validation</div>
			<div class="bill-row">
				<div class="field kra-cu-field">
					<label>CU Invoice Number</label>
					<input
						type="text"
						v-model="kra.cu_invoice_number"
						placeholder="19-digit TIMS number or KRACU... eTIMS number"
					/>
				</div>
				<button
					type="button"
					class="secondary"
					:disabled="!canValidateKra || validatingKra"
					@click="onValidateKra"
				>
					{{ validatingKra ? "Validating..." : "Validate with KRA" }}
				</button>
			</div>
			<div v-if="isEtimsNumber" class="bill-row">
				<div class="field kra-scan-field">
					<label>Scanned QR text / URL</label>
					<input
						type="text"
						v-model="kra.etims_scanned_data"
						placeholder="Tap 'Scan QR' below, or paste from any QR scanner app"
					/>
				</div>
				<button type="button" class="secondary" @click="showQrScanner = true">Scan QR</button>
			</div>
			<QrScanner v-if="showQrScanner" @scanned="onQrScanned" @close="showQrScanner = false" />
			<div v-if="isEtimsNumber && !kra.etims_scanned_data" class="bill-row">
				<div class="field">
					<label>Supplier PIN (from receipt)</label>
					<input type="text" v-model="kra.etims_supplier_pin" />
				</div>
				<div class="field">
					<label>Branch ID (from receipt)</label>
					<input type="text" v-model="kra.etims_branch_id" />
				</div>
				<div class="field">
					<label>Receipt Signature</label>
					<input type="text" v-model="kra.etims_receipt_signature" placeholder="dashes optional" />
				</div>
			</div>
			<p v-if="isEtimsNumber && kra.etims_scanned_data" class="muted">
				Using the scanned QR text above - manual PIN/Branch/Signature fields are not needed.
			</p>
			<div v-if="kra.status" class="kra-status">
				Status: <strong>{{ kra.status }}</strong>
				<template v-if="kra.status === 'Fetched'"> - {{ kra.claimable ? "Claimable" : "Not claimable" }}</template>
				<span v-if="kra.message" class="muted"> ({{ kra.message }})</span>
			</div>
		</div>
		<p v-else class="muted attach-hint">Save as Draft first to validate the supplier's KRA invoice.</p>

		<div class="payment-block">
			<label class="toggle-row">
				<span class="toggle-switch">
					<input type="checkbox" v-model="payment.enabled" @change="onPaymentToggle" />
					<span class="toggle-slider"></span>
				</span>
				Record payment now
			</label>
			<div v-if="payment.enabled" class="payment-fields">
				<div class="field">
					<label>Mode of Payment *</label>
					<select v-model="payment.mode_of_payment">
						<option value="" disabled>Choose mode</option>
						<option v-for="m in modesOfPayment" :key="m.name" :value="m.name">{{ m.name }}</option>
					</select>
				</div>
				<div class="field">
					<label>Amount *</label>
					<MoneyInput :value="payment.amount" @input="payment.amount = flt($event.target.value)" />
				</div>
				<div class="field">
					<label>Reference No *</label>
					<input type="text" v-model="payment.reference_no" placeholder="Required" />
				</div>
				<div class="field">
					<label>Reference Date</label>
					<input type="date" v-model="payment.reference_date" />
				</div>
			</div>
		</div>

		<div class="actions">
			<button type="button" class="secondary" :disabled="!canSave || saving" @click="saveDraft">
				{{ saving ? "Saving..." : "Save as Draft" }}
			</button>
			<span v-if="savedResult" class="saved-result">
				Saved {{ savedResult.name }} - Grand Total {{ money(savedResult.grand_total) }} ({{ savedResult.status }})
				<template v-if="changedPriceCount(savedResult) > 0">
					- prices updated for {{ changedPriceCount(savedResult) }} item(s)
				</template>
			</span>
			<span v-if="saveError" class="error">{{ saveError }}</span>

			<span class="spacer"></span>

			<span v-if="submittedResult" class="submitted-result">
				Submitted {{ submittedResult.name }} - {{ submittedResult.status }}
				<template v-if="submittedResult.payment_name"> - Payment {{ submittedResult.payment_name }}</template>
				<template v-if="changedPriceCount(submittedResult) > 0">
					- prices updated for {{ changedPriceCount(submittedResult) }} item(s)
				</template>
				<a :href="'/app/purchase-invoice/' + submittedResult.name" target="_blank">Open in ERPNext</a>
			</span>
			<span v-if="submitError" class="error">{{ submitError }}</span>
			<button type="button" class="primary" :disabled="!canSubmit || submitting" @click="confirmAndSubmit">
				{{ submitting ? "Submitting..." : "Save and Submit" }}
			</button>
		</div>

		<h3>Draft Receivings</h3>
		<p v-if="loadingDrafts">Loading...</p>
		<p v-else-if="drafts.length === 0">No draft receivings yet.</p>
		<table v-else class="drafts-table">
			<thead>
				<tr>
					<th>Name</th>
					<th>Supplier</th>
					<th>Bill No</th>
					<th>Grand Total</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="d in drafts" :key="d.name" class="draft-row" @click="loadDraft(d.name)">
					<td>{{ d.name }}</td>
					<td>{{ d.supplier }}</td>
					<td>{{ d.bill_no }}</td>
					<td>{{ money(d.grand_total) }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { call } from "./api";
import { buildCartRow } from "./cartRow";
import { flt, money, generateRequestId } from "./format";
import { grandTotal as computeGrandTotal, billGrandTotal, itemsNetTotal, itemsVatTotal } from "./rowMath";
import ReceivingHeader from "./components/ReceivingHeader.vue";
import ItemGrid from "./components/ItemGrid.vue";
import MoneyInput from "./components/MoneyInput.vue";
import QrScanner from "./components/QrScanner.vue";

function today() {
	return new Date().toISOString().slice(0, 10);
}

function freshHeader() {
	return {
		supplier: "",
		bill_no: "",
		posting_date: today(),
		warehouse: "Rupa - BO",
	};
}

function freshPayment() {
	return {
		enabled: false,
		mode_of_payment: "",
		amount: 0,
		reference_no: "",
		reference_date: today(),
	};
}

function freshBill() {
	return {
		discount_percentage: 0,
		additional_expenses: [],
	};
}

function freshKra() {
	return {
		cu_invoice_number: "",
		status: "",
		claimable: false,
		message: "",
		etims_supplier_pin: "",
		etims_branch_id: "",
		etims_receipt_signature: "",
		etims_scanned_data: "",
	};
}

const header = reactive(freshHeader());
const cartItems = ref([]);
const currentDraftName = ref(null);
const payment = reactive(freshPayment());
const bill = reactive(freshBill());
const kra = reactive(freshKra());
const validatingKra = ref(false);
const showQrScanner = ref(false);

function onQrScanned(text) {
	kra.etims_scanned_data = text;
	showQrScanner.value = false;
}
const clientRequestId = ref(generateRequestId());

const vatTemplates = ref([]);
const modesOfPayment = ref([]);
const expenseAccounts = ref([]);

const attachedFiles = ref([]);
const attaching = ref(false);
const attachError = ref(null);

const saving = ref(false);
const savedResult = ref(null);
const saveError = ref(null);

const submitting = ref(false);
const submittedResult = ref(null);
const submitError = ref(null);

const drafts = ref([]);
const loadingDrafts = ref(true);
const reconciliationWarning = ref(null);

function calcNetTotal() {
	return itemsNetTotal(cartItems.value);
}

function calcDiscountAmount() {
	const factor = flt(bill.discount_percentage) / 100;
	return calcNetTotal() * factor;
}

function calcVatTotal() {
	const discountFactor = 1 - flt(bill.discount_percentage) / 100;
	return itemsVatTotal(vatTemplates.value, cartItems.value) * discountFactor;
}

const finalGrandTotal = computed(() =>
	billGrandTotal(vatTemplates.value, cartItems.value, bill.discount_percentage, bill.additional_expenses),
);

const canSave = computed(() => header.supplier && cartItems.value.length > 0);
const canSubmit = computed(() => {
	if (!canSave.value) return false;
	if (!payment.enabled) return true;
	return payment.mode_of_payment && payment.reference_no && flt(payment.amount) > 0;
});

function onAddItem(row) {
	const existing = cartItems.value.find((i) => i.item_code === row.item_code);
	if (existing) {
		existing.qty = (flt(existing.qty) || 0) + (flt(row.qty) || 1);
	} else {
		cartItems.value.push(row);
	}
}
function onRemoveItem(idx) {
	cartItems.value.splice(idx, 1);
}

function onPaymentToggle() {
	if (payment.enabled && !payment.amount) {
		payment.amount = Math.round(computeGrandTotal(vatTemplates.value, cartItems.value) * 100) / 100;
	}
}

function addExpenseRow() {
	bill.additional_expenses.push({ expense_account: "", amount: 0, description: "" });
}

const isEtimsNumber = computed(() => kra.cu_invoice_number.trim().toUpperCase().startsWith("KRACU"));
const canValidateKra = computed(() => {
	if (!kra.cu_invoice_number) return false;
	if (!isEtimsNumber.value) return true;
	if (kra.etims_scanned_data) return true;
	return kra.etims_supplier_pin && kra.etims_branch_id && kra.etims_receipt_signature;
});

async function onValidateKra() {
	validatingKra.value = true;
	try {
		const result = await call("smart_receiving.smart_receiving.api.receiving.validate_kra_invoice", {
			purchase_invoice: currentDraftName.value,
			cu_invoice_number: kra.cu_invoice_number,
			etims_supplier_pin: isEtimsNumber.value ? kra.etims_supplier_pin : null,
			etims_branch_id: isEtimsNumber.value ? kra.etims_branch_id : null,
			etims_receipt_signature: isEtimsNumber.value ? kra.etims_receipt_signature : null,
			etims_scanned_data: isEtimsNumber.value ? kra.etims_scanned_data : null,
		});
		kra.status = result.status;
		kra.claimable = result.claimable;
		kra.message = result.message || "";
	} catch (e) {
		kra.status = "Failed";
		kra.message = e.message || "KRA validation failed";
	} finally {
		validatingKra.value = false;
	}
}

async function loadAttachedFiles(name) {
	attachedFiles.value = await call("frappe.client.get_list", {
		doctype: "File",
		filters: { attached_to_doctype: "Purchase Invoice", attached_to_name: name },
		fields: ["name", "file_name", "file_url"],
		limit_page_length: 0,
	});
}

async function onAttachFile(event) {
	const file = event.target.files[0];
	event.target.value = "";
	if (!file || !currentDraftName.value) return;

	attaching.value = true;
	attachError.value = null;
	try {
		const formData = new FormData();
		formData.append("file", file);
		formData.append("doctype", "Purchase Invoice");
		formData.append("docname", currentDraftName.value);
		formData.append("is_private", "1");

		const response = await fetch("/api/method/upload_file", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": window.frappe?.csrf_token || "" },
			body: formData,
		});
		const data = await response.json();
		if (!response.ok) {
			throw new Error(data.message || data.exc || "Upload failed");
		}
		await loadAttachedFiles(currentDraftName.value);
	} catch (e) {
		attachError.value = e.message || "Failed to upload file";
	} finally {
		attaching.value = false;
	}
}

function changedPriceCount(result) {
	return Object.keys(result?.changed_prices || {}).filter((code) =>
		Object.values(result.changed_prices[code]).some((v) => v !== "unchanged"),
	).length;
}

function resetForm() {
	Object.assign(header, freshHeader());
	cartItems.value = [];
	currentDraftName.value = null;
	Object.assign(payment, freshPayment());
	Object.assign(bill, freshBill());
	Object.assign(kra, freshKra());
	attachedFiles.value = [];
	attachError.value = null;
	clientRequestId.value = generateRequestId();
	savedResult.value = null;
	saveError.value = null;
	submittedResult.value = null;
	submitError.value = null;
}

async function loadDrafts() {
	loadingDrafts.value = true;
	drafts.value = await call("smart_receiving.smart_receiving.api.receiving.list_draft_receivings");
	loadingDrafts.value = false;
}

async function loadDraft(name) {
	const draft = await call("smart_receiving.smart_receiving.api.receiving.get_receiving_draft", { name });

	header.supplier = draft.supplier;
	header.bill_no = draft.bill_no || "";
	header.posting_date = draft.posting_date || today();
	header.warehouse = draft.warehouse;
	currentDraftName.value = draft.name;
	bill.discount_percentage = draft.additional_discount_percentage || 0;
	bill.additional_expenses = draft.additional_expenses || [];
	Object.assign(payment, draft.planned_payment || freshPayment());
	savedResult.value = null;
	saveError.value = null;
	submittedResult.value = null;
	submitError.value = null;
	attachError.value = null;
	await loadAttachedFiles(draft.name);

	const existingKra = await call("smart_receiving.smart_receiving.api.receiving.get_kra_validation", {
		purchase_invoice: draft.name,
	});
	if (existingKra) {
		kra.cu_invoice_number = existingKra.cu_invoice_number;
		kra.status = existingKra.status;
		kra.claimable = existingKra.claimable;
		kra.message = existingKra.pending_reason || "";
		kra.etims_supplier_pin = existingKra.etims_supplier_pin || "";
		kra.etims_branch_id = existingKra.etims_branch_id || "";
		kra.etims_receipt_signature = existingKra.etims_receipt_signature || "";
		kra.etims_scanned_data = existingKra.etims_scanned_data || "";
	} else {
		Object.assign(kra, freshKra());
	}

	const rows = [];
	for (const item of draft.items) {
		const context = await call("smart_receiving.smart_receiving.api.receiving.get_item_receiving_context", {
			item_code: item.item_code,
			warehouse: draft.warehouse,
		});
		rows.push(
			buildCartRow(context, {
				qty: item.qty,
				rate_excl: item.rate,
				uom: item.uom,
				conversion_factor: item.conversion_factor,
				discount_percentage: item.discount_percentage,
				vat_template: item.item_tax_template,
			}),
		);
	}
	cartItems.value = rows;
}

function buildCart() {
	return {
		name: currentDraftName.value || undefined,
		supplier: header.supplier,
		bill_no: header.bill_no,
		posting_date: header.posting_date,
		warehouse: header.warehouse,
		items: cartItems.value.map((row) => ({
			item_code: row.item_code,
			qty: row.qty,
			rate: row.rate_excl,
			uom: row.uom,
			conversion_factor: row.conversion_factor,
			discount_percentage: row.discount_percentage,
			item_tax_template: row.vat_template,
			prices_by_list: row.prices,
		})),
		additional_discount_percentage: bill.discount_percentage,
		additional_expenses: bill.additional_expenses.filter((e) => e.expense_account && flt(e.amount) > 0),
		// Not acted upon until Save and Submit - stored as-is so a partial
		// payment entered before a Save as Draft isn't lost on resume.
		planned_payment: payment.enabled ? { ...payment } : null,
	};
}

async function saveDraft() {
	saving.value = true;
	saveError.value = null;
	reconciliationWarning.value = null;
	try {
		const result = await call("smart_receiving.smart_receiving.api.receiving.build_purchase_invoice", {
			cart: buildCart(),
		});
		currentDraftName.value = result.name;
		savedResult.value = result;

		const clientTotal = flt(finalGrandTotal.value);
		const serverTotal = flt(result.grand_total);
		if (Math.abs(clientTotal - serverTotal) > 0.01) {
			reconciliationWarning.value = `Grand Total variance detected: UI calculated ${clientTotal.toFixed(2)} KES, but server returned ${serverTotal.toFixed(2)} KES.`;
		}

		await loadAttachedFiles(result.name);
		await loadDrafts();
	} catch (e) {
		saveError.value = e.message || "Failed to save draft";
	} finally {
		saving.value = false;
	}
}

function confirmAndSubmit() {
	if (window.confirm("Save and submit this receiving, and update the selling prices you changed?")) {
		submitReceiving();
	}
}

async function submitReceiving() {
	submitting.value = true;
	submitError.value = null;
	reconciliationWarning.value = null;
	try {
		const result = await call("smart_receiving.smart_receiving.api.receiving.submit_receiving", {
			cart: buildCart(),
			payment: payment.enabled ? payment : null,
			client_request_id: clientRequestId.value,
		});

		const clientTotal = flt(finalGrandTotal.value);
		const serverTotal = flt(result.grand_total);
		if (Math.abs(clientTotal - serverTotal) > 0.01) {
			reconciliationWarning.value = `Grand Total variance detected: UI calculated ${clientTotal.toFixed(2)} KES, but server returned ${serverTotal.toFixed(2)} KES.`;
		}

		submittedResult.value = result;
		resetForm();
		await loadDrafts();
	} catch (e) {
		submitError.value = e.message || "Failed to submit receiving";
	} finally {
		submitting.value = false;
	}
}

onMounted(async () => {
	await loadDrafts();
	vatTemplates.value = await call("smart_receiving.smart_receiving.api.receiving.list_item_tax_templates");
	modesOfPayment.value = await call("frappe.client.get_list", {
		doctype: "Mode of Payment",
		filters: { enabled: 1 },
		fields: ["name"],
		limit_page_length: 0,
		order_by: "name asc",
	});
	expenseAccounts.value = await call("frappe.client.get_list", {
		doctype: "Account",
		filters: { company: "BEVALI ONLINE", root_type: "Expense", is_group: 0 },
		fields: ["name"],
		limit_page_length: 0,
		order_by: "name asc",
	});
});
</script>

<style>
.smart-receiving-app {
	padding: 24px;
	font-family: var(--font-stack, sans-serif);
	max-width: 1200px;
}
.smart-receiving-app h3 {
	margin-top: 32px;
}
.smart-receiving-app .error {
	color: var(--red-500, #c0392b);
	margin-left: 12px;
}
.smart-receiving-app .actions {
	margin: 20px 0;
	display: flex;
	align-items: center;
	gap: 12px;
	flex-wrap: wrap;
}
.smart-receiving-app .actions .spacer {
	flex: 1;
}
.smart-receiving-app button.primary {
	background: var(--primary, #5e64ff);
	color: #fff;
	border: none;
	padding: 10px 20px;
	border-radius: 6px;
	font-weight: 600;
	cursor: pointer;
}
.smart-receiving-app button.secondary {
	background: var(--gray-100, #f4f5f6);
	color: var(--text-color, #333);
	border: 1px solid var(--dark-border-color, #d1d8dd);
	padding: 10px 20px;
	border-radius: 6px;
	font-weight: 600;
	cursor: pointer;
}
.smart-receiving-app button.primary:disabled,
.smart-receiving-app button.secondary:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}
.smart-receiving-app .saved-result {
	color: var(--text-muted, #666);
	font-weight: 500;
}
.smart-receiving-app .submitted-result {
	color: var(--green-600, #1e8449);
	font-weight: 500;
}
.smart-receiving-app .submitted-result a {
	margin-left: 8px;
}
.smart-receiving-app .editing-banner {
	background: var(--yellow-100, #fff8e1);
	border: 1px solid var(--yellow-300, #ffe08a);
	border-radius: 6px;
	padding: 8px 14px;
	margin-bottom: 16px;
	display: flex;
	align-items: center;
	gap: 12px;
	font-size: 13px;
}
.smart-receiving-app .editing-banner button {
	border: none;
	background: transparent;
	text-decoration: underline;
	cursor: pointer;
	font-size: 13px;
}
.smart-receiving-app .payment-block {
	margin: 20px 0;
	padding: 14px 16px;
	border: 1px solid var(--dark-border-color, #e5e7eb);
	border-radius: 8px;
	background: var(--gray-50, #fafbfc);
}
.smart-receiving-app .toggle-row {
	display: flex;
	align-items: center;
	gap: 10px;
	font-weight: 600;
	cursor: pointer;
}
.smart-receiving-app .toggle-switch {
	position: relative;
	display: inline-block;
	width: 38px;
	height: 22px;
	flex-shrink: 0;
}
.smart-receiving-app .toggle-switch input {
	opacity: 0;
	width: 0;
	height: 0;
}
.smart-receiving-app .toggle-slider {
	position: absolute;
	inset: 0;
	background: var(--dark-border-color, #d1d8dd);
	border-radius: 999px;
	transition: background 0.15s ease;
}
.smart-receiving-app .toggle-slider::before {
	content: "";
	position: absolute;
	height: 16px;
	width: 16px;
	left: 3px;
	top: 3px;
	background: #fff;
	border-radius: 50%;
	transition: transform 0.15s ease;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}
.smart-receiving-app .toggle-switch input:checked + .toggle-slider {
	background: var(--primary, #5e64ff);
}
.smart-receiving-app .toggle-switch input:checked + .toggle-slider::before {
	transform: translateX(16px);
}
.smart-receiving-app .toggle-switch input:focus-visible + .toggle-slider {
	outline: 2px solid var(--primary, #5e64ff);
	outline-offset: 2px;
}
.smart-receiving-app .payment-fields {
	display: flex;
	gap: 16px;
	flex-wrap: wrap;
	margin-top: 12px;
}
.smart-receiving-app .payment-fields .field {
	display: flex;
	flex-direction: column;
	gap: 4px;
	min-width: 160px;
}
.smart-receiving-app .payment-fields label {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-muted, #6b7280);
	text-transform: uppercase;
}
.smart-receiving-app .payment-fields input,
.smart-receiving-app .payment-fields select {
	padding: 8px 10px;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 6px;
	font-size: 14px;
}
.smart-receiving-app .muted {
	color: var(--text-muted, #888);
	font-size: 12px;
}
.smart-receiving-app .icon-btn {
	border: none;
	background: transparent;
	cursor: pointer;
	font-size: 14px;
	padding: 4px 8px;
	border-radius: 4px;
}
.smart-receiving-app .icon-btn:hover {
	background: var(--gray-100, #f4f5f6);
}
.smart-receiving-app .icon-btn.danger {
	color: var(--red-500, #c0392b);
}
.smart-receiving-app .grand-total-bar {
	margin: 20px 0;
	padding: 16px 20px;
	border: 2px solid var(--primary, #5e64ff);
	border-radius: 8px;
	background: var(--gray-50, #fafbfc);
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 16px;
}
.smart-receiving-app .grand-total-bar span {
	font-size: 14px;
	font-weight: 600;
	text-transform: uppercase;
	color: var(--text-muted, #6b7280);
}
.smart-receiving-app .grand-total-bar strong {
	font-size: 28px;
	font-weight: 700;
	color: var(--primary, #5e64ff);
}
.smart-receiving-app .kra-cu-field input {
	min-width: 320px;
}
.smart-receiving-app .kra-scan-field {
	flex: 1;
	min-width: 320px;
}
.smart-receiving-app .kra-scan-field input {
	width: 100%;
}
.smart-receiving-app .kra-status {
	margin-top: 10px;
	font-size: 13px;
}
.smart-receiving-app .bill-block,
.smart-receiving-app .attach-block,
.smart-receiving-app .kra-block {
	margin: 20px 0;
	padding: 14px 16px;
	border: 1px solid var(--dark-border-color, #e5e7eb);
	border-radius: 8px;
}
.smart-receiving-app .attach-hint {
	margin: 8px 0 0;
}
.smart-receiving-app .bill-block-title {
	font-weight: 700;
	font-size: 12px;
	text-transform: uppercase;
	color: var(--text-muted, #6b7280);
	margin-bottom: 10px;
}
.smart-receiving-app .bill-row {
	display: flex;
	gap: 16px;
	flex-wrap: wrap;
	align-items: flex-end;
}
.smart-receiving-app .bill-row .field {
	display: flex;
	flex-direction: column;
	gap: 4px;
	min-width: 160px;
}
.smart-receiving-app .bill-row label {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-muted, #6b7280);
	text-transform: uppercase;
}
.smart-receiving-app .bill-row input {
	padding: 8px 10px;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 6px;
	font-size: 14px;
}
.smart-receiving-app .expenses {
	margin-top: 14px;
}
.smart-receiving-app .expense-row {
	display: flex;
	gap: 10px;
	align-items: center;
	margin-bottom: 8px;
}
.smart-receiving-app .expense-row select {
	min-width: 220px;
	padding: 8px 10px;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 6px;
}
.smart-receiving-app .expense-row input[type="text"] {
	flex: 1;
	padding: 8px 10px;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 6px;
}
.smart-receiving-app .link-btn {
	border: none;
	background: transparent;
	color: var(--primary, #5e64ff);
	cursor: pointer;
	font-weight: 600;
	font-size: 13px;
	padding: 4px 0;
}
.smart-receiving-app .attached-files {
	list-style: none;
	margin: 0 0 10px;
	padding: 0;
}
.smart-receiving-app .attached-files li {
	padding: 4px 0;
}
.smart-receiving-app .drafts-table {
	border-collapse: collapse;
	margin-top: 12px;
	width: 100%;
	border: 1px solid var(--dark-border-color, #d1d8dd);
	border-radius: 8px;
	overflow: hidden;
}
.smart-receiving-app .drafts-table th,
.smart-receiving-app .drafts-table td {
	border: 1px solid var(--dark-border-color, #e5e7eb);
	padding: 8px 12px;
	text-align: left;
}
.smart-receiving-app .drafts-table th {
	background: var(--gray-100, #f4f5f6);
	font-size: 12px;
	text-transform: uppercase;
	color: var(--text-muted, #6b7280);
}
.smart-receiving-app .draft-row {
	cursor: pointer;
}

.smart-receiving-app .row-over-po {
	background-color: #fef2f2 !important;
	border-left: 4px solid #ef4444 !important;
}
.smart-receiving-app .tax-badge {
	display: inline-block;
	font-size: 11px;
	font-weight: 700;
	padding: 3px 8px;
	border-radius: 4px;
	margin-top: 4px;
	text-transform: uppercase;
	letter-spacing: 0.03em;
}
.smart-receiving-app .badge-vat {
	background-color: #e0e7ff !important;
	color: #3730a3 !important;
	border: 1px solid #c7d2fe !important;
}
.smart-receiving-app .badge-exempt {
	background-color: #fef3c7 !important;
	color: #92400e !important;
	border: 1px solid #fde68a !important;
}
.smart-receiving-app .badge-zero {
	background-color: #d1fae5 !important;
	color: #065f46 !important;
	border: 1px solid #a7f3d0 !important;
}
.smart-receiving-app .draft-row:hover {
	background: var(--gray-50, #fafbfc);
}
</style>
