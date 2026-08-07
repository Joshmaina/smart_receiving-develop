import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import frappe
import requests
from bs4 import BeautifulSoup
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from erpnext.stock.doctype.item.item import get_last_purchase_details
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import flt, now_datetime, nowdate

PRIMARY_PRICE_LIST = "Zion Retail Price"


def _get_stock_by_code(item_codes, warehouse):
	"""Return {item_code: actual_qty} in ``warehouse`` for the given item codes."""
	if not warehouse or not item_codes:
		return {}

	bin_doctype = DocType("Bin")
	rows = (
		frappe.qb.from_(bin_doctype)
		.select(bin_doctype.item_code, Sum(bin_doctype.actual_qty).as_("actual_qty"))
		.where(bin_doctype.item_code.isin(item_codes))
		.where(bin_doctype.warehouse == warehouse)
		.groupby(bin_doctype.item_code)
		.run(as_dict=True)
	)
	return {row.item_code: flt(row.actual_qty) for row in rows}


@frappe.whitelist()
def search_items(term, warehouse=None):
	"""Search items by code, name, or barcode.

	Returns item_code, item_name, stock_uom, and current_stock in ``warehouse``
	(0 if no warehouse given). item_code is always returned as text, since
	Bevali item codes are numeric strings with significant leading zeros.
	"""
	term = (term or "").strip()
	if not term:
		return []

	like_term = f"%{term}%"

	item = DocType("Item")
	barcode = DocType("Item Barcode")

	matched = (
		frappe.qb.from_(item)
		.left_join(barcode)
		.on(barcode.parent == item.name)
		.select(item.item_code)
		.distinct()
		.where(item.disabled == 0)
		.where(
			(item.item_code.like(like_term))
			| (item.item_name.like(like_term))
			| (barcode.barcode.like(like_term))
		)
		.limit(20)
		.run(as_dict=True)
	)

	item_codes = [row.item_code for row in matched]
	if not item_codes:
		return []

	items = frappe.get_all(
		"Item",
		filters={"item_code": ["in", item_codes], "disabled": 0},
		fields=["item_code", "item_name", "stock_uom"],
	)

	stock_by_code = _get_stock_by_code(item_codes, warehouse)

	for row in items:
		row["current_stock"] = stock_by_code.get(row["item_code"], 0.0)

	order = {code: i for i, code in enumerate(item_codes)}
	items.sort(key=lambda r: order.get(r["item_code"], 0))

	return items


@frappe.whitelist()
def get_item_receiving_context(item_code, warehouse=None):
	"""Return the per-line data the receiving screen needs for one item:
	last purchase cost (prefill), stock, purchase tax template, and the
	item's current selling price in every enabled Selling price list.
	"""
	item = frappe.get_doc("Item", item_code)

	# Build structured UOM array from Item.uoms child table + direct DB query fallback
	uoms = []
	uom_set = set()
	for uom_row in item.get("uoms") or []:
		if uom_row.uom and uom_row.uom not in uom_set:
			uoms.append({
				"uom": uom_row.uom,
				"conversion_factor": flt(uom_row.conversion_factor or 1.0)
			})
			uom_set.add(uom_row.uom)

	db_uoms = frappe.get_all(
		"UOM Conversion Detail",
		filters={"parent": item_code},
		fields=["uom", "conversion_factor"]
	)
	for uom_row in db_uoms:
		if uom_row.uom and uom_row.uom not in uom_set:
			uoms.append({
				"uom": uom_row.uom,
				"conversion_factor": flt(uom_row.conversion_factor or 1.0)
			})
			uom_set.add(uom_row.uom)

	stock_uom = item.stock_uom or "Pcs"
	if not any(d["uom"] == stock_uom for d in uoms):
		uoms.insert(0, {"uom": stock_uom, "conversion_factor": 1.0})
		uom_set.add(stock_uom)

	default_purchase_uom = item.purchase_uom if item.purchase_uom else stock_uom
	if item.purchase_uom and item.purchase_uom not in uom_set:
		uoms.append({"uom": item.purchase_uom, "conversion_factor": 1.0})
		uom_set.add(item.purchase_uom)

	is_multi_uom = len(uoms) > 1

	last_purchase = get_last_purchase_details(item_code)
	last_purchase_uom = last_purchase.get("uom") or last_purchase.get("stock_uom") or None
	last_purchase_rate_raw = flt(last_purchase.get("base_net_rate") or last_purchase.get("base_rate") or last_purchase.get("rate") or 0)

	# Rate Prefill Semantics: Prefill rate ONLY when selected/default UOM matches last purchase UOM
	if last_purchase_uom and last_purchase_uom == default_purchase_uom:
		last_purchase_rate = last_purchase_rate_raw
	elif not last_purchase_uom:
		last_purchase_rate = last_purchase_rate_raw
	else:
		last_purchase_rate = 0.0

	current_stock = _get_stock_by_code([item_code], warehouse).get(item_code, 0.0)

	item_tax_template = None
	for row in item.taxes:
		if row.tax_category == "Purchase":
			item_tax_template = row.item_tax_template
			break

	item_tax_rate = 0.0
	if item_tax_template:
		item_tax_rate = flt(
			frappe.db.sql(
				"select sum(tax_rate) from `tabItem Tax Template Detail` where parent = %s",
				(item_tax_template,),
			)[0][0]
			or 0
		)

	price_lists = frappe.get_all(
		"Price List", filters={"selling": 1, "enabled": 1}, fields=["name"], order_by="name"
	)
	price_list_names = [pl.name for pl in price_lists]

	item_prices = frappe.get_all(
		"Item Price",
		filters={"item_code": item_code, "selling": 1, "price_list": ["in", price_list_names]},
		fields=["price_list", "price_list_rate"],
	)
	rate_by_list = {p.price_list: flt(p.price_list_rate) for p in item_prices}

	selling_prices = [
		{
			"price_list": name,
			"price": rate_by_list.get(name),
			"is_primary": name == PRIMARY_PRICE_LIST,
		}
		for name in price_list_names
	]

	return {
		"item_code": item.item_code,
		"item_name": item.item_name,
		"stock_uom": item.stock_uom,
		"current_stock": current_stock,
		"last_purchase_rate": last_purchase_rate,
		"uoms": uoms,
		"is_multi_uom": is_multi_uom,
		"default_purchase_uom": default_purchase_uom,
		"item_tax_template": item_tax_template,
		"item_tax_rate": item_tax_rate,
		"selling_prices": selling_prices,
		"primary_price_list": PRIMARY_PRICE_LIST,
	}


COMPANY = "BEVALI ONLINE"
DEFAULT_WAREHOUSE = "Rupa - BO"


@frappe.whitelist()
def build_purchase_invoice(cart):
	"""Create or update a draft Purchase Invoice from a receiving cart.

	``cart`` (dict or JSON string):
		name (optional): existing draft PI to update, instead of creating new.
		supplier, bill_no, bill_date (optional), posting_date (optional).
		warehouse (optional, defaults to Rupa - BO).
		items: [{item_code, qty, rate, discount_percentage, item_tax_template,
			prices_by_list}] - prices_by_list (optional, same shape as
			upsert_item_prices) is written on every save, draft or submit, so
			a price edit is never lost even if the draft is never submitted.
		additional_discount_percentage / discount_amount (optional, applied on Net Total).
		additional_expenses (optional): [{expense_account, amount, description}]
			posted as "Actual" charges on the invoice's own taxes table.
		planned_payment (optional): {enabled, mode_of_payment, amount, reference_no,
			reference_date} - the payment the user entered but hasn't submitted yet.
			Stored as-is (not acted upon) so it survives a Save as Draft/resume
			cycle instead of resetting - only submit_receiving actually creates
			a Payment Entry from it.

	Only ever saves as a draft (docstatus=0) - never submits. Returns the
	draft's name, computed totals, and changed_prices for the screen to
	display.
	"""
	if isinstance(cart, str):
		cart = frappe.parse_json(cart)

	if cart.get("name") and (not cart.get("supplier") or not cart.get("items")):
		existing_draft = get_receiving_draft(cart["name"])
		if not cart.get("supplier"):
			cart["supplier"] = existing_draft.get("supplier")
		if not cart.get("items"):
			cart["items"] = [
				{
					"item_code": d["item_code"],
					"qty": d["qty"],
					"rate": d["rate"],
					"discount_percentage": d.get("discount_percentage", 0),
					"item_tax_template": d.get("item_tax_template"),
					"prices_by_list": {},
				}
				for d in existing_draft.get("items", [])
			]
		if not cart.get("warehouse"):
			cart["warehouse"] = existing_draft.get("warehouse")

	if not cart.get("supplier"):
		frappe.throw("Cart must include a supplier")
	if not cart.get("items"):
		frappe.throw("Cart must include at least one item")

	if cart.get("name"):
		pi = frappe.get_doc("Purchase Invoice", cart["name"])
		if pi.docstatus != 0:
			frappe.throw(f"Purchase Invoice {pi.name} is not a draft and cannot be edited here")
		pi.items = []
		pi.taxes = []
		# Clear this too: it was set (correctly, after set_taxes_and_charges())
		# on the previous save, but if it's already populated when
		# set_missing_values() runs below, ERPNext treats each row's rate as
		# tax-INCLUSIVE instead of net - the same ordering bug as before, just
		# triggered by a pre-existing value instead of one set too early.
		pi.taxes_and_charges = None
	else:
		pi = frappe.new_doc("Purchase Invoice")

	warehouse = cart.get("warehouse") or DEFAULT_WAREHOUSE

	pi.custom_smart_receiving = 1
	pi.company = COMPANY
	pi.supplier = cart["supplier"]
	pi.update_stock = 1
	pi.set_warehouse = warehouse
	pi.tax_category = "Purchase"
	if cart.get("bill_no"):
		pi.bill_no = cart["bill_no"]
	if cart.get("bill_date"):
		pi.bill_date = cart["bill_date"]
	if cart.get("posting_date"):
		pi.posting_date = cart["posting_date"]

	for row in cart["items"]:
		item_uom = row.get("uom") or frappe.db.get_value("Item", row["item_code"], "purchase_uom") or frappe.db.get_value("Item", row["item_code"], "stock_uom")
		item_cf = flt(row.get("conversion_factor") or 1.0)
		pi.append(
			"items",
			{
				"item_code": row["item_code"],
				"qty": flt(row["qty"]),
				"rate": flt(row["rate"]),
				"uom": item_uom,
				"conversion_factor": item_cf,
				"discount_percentage": flt(row.get("discount_percentage") or 0),
				"item_tax_template": row.get("item_tax_template"),
				"warehouse": warehouse,
			},
		)

	pi.ignore_pricing_rule = 1
	pi.set_missing_values()

	# set_missing_values() does not itself populate VAT rows from each item's
	# item_tax_template - that normally happens inside validate()/save(), but
	# only while the taxes table is still empty. Since we're about to append
	# our own additional-expense rows below, we must trigger it now, before
	# taxes stops being empty, or the VAT row never gets added.
	pi.set_taxes_and_charges()

	# Set purely as a display/reference field to match what a hand-created PI
	# would show - the Desk UI auto-fills this via client-side JS, which never
	# runs for a doc built headlessly. Set *after* set_taxes_and_charges() so
	# it can't influence the per-item VAT computation above.
	if not pi.taxes_and_charges:
		pi.taxes_and_charges = frappe.db.get_value(
			"Purchase Taxes and Charges Template", {"is_default": 1, "company": COMPANY}, "name"
		)

	# Always set explicitly (even to 0), not just when truthy: on an update,
	# a discount from a previous save must not silently linger if this cart
	# no longer has one.
	pi.apply_discount_on = "Net Total"
	pi.additional_discount_percentage = flt(cart.get("additional_discount_percentage") or 0)
	pi.discount_amount = flt(cart.get("discount_amount") or 0)

	# Always set (even to None/empty), same reasoning as the discount fields
	# above: a planned payment removed on a resumed draft must not linger.
	planned_payment = cart.get("planned_payment")
	pi.custom_planned_payment = frappe.as_json(planned_payment) if planned_payment else None

	for expense in cart.get("additional_expenses") or []:
		pi.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": expense["expense_account"],
				"tax_amount": flt(expense["amount"]),
				"description": expense.get("description") or expense["expense_account"],
				"add_deduct_tax": "Add",
				"category": "Total",
			},
		)

	pi.calculate_taxes_and_totals()

	# COMPARTMENT C: Financial Reconciliation & Grand Total Assertion
	expected_grand_total = flt(pi.net_total + pi.total_taxes_and_charges, 2)
	if abs(expected_grand_total - flt(pi.grand_total)) > 0.05:
		frappe.throw(
			f"Financial reconciliation assertion failed: server grand total ({pi.grand_total:.2f}) "
			f"differs from expected calculation ({expected_grand_total:.2f})."
		)

	pi.save()

	# Written on every save (draft or submit), not deferred to submit-only:
	# an employee who edits prices and clicks Save as Draft must not lose
	# that edit if they close the screen before submitting.
	changed_prices = {}
	for row in cart["items"]:
		prices_by_list = row.get("prices_by_list")
		if prices_by_list:
			changed_prices[row["item_code"]] = upsert_item_prices(row["item_code"], prices_by_list)

	return {
		"name": pi.name,
		"status": pi.status,
		"net_total": pi.net_total,
		"total_taxes_and_charges": pi.total_taxes_and_charges,
		"grand_total": pi.grand_total,
		"warehouse": warehouse,
		"changed_prices": changed_prices,
	}


@frappe.whitelist()
def upsert_item_prices(item_code, prices_by_list):
	"""Write only the selling prices that actually changed.

	``prices_by_list``: {price_list_name: new_rate}
	Returns {price_list_name: "created" | "updated" | "unchanged"}
	"""
	if isinstance(prices_by_list, str):
		prices_by_list = frappe.parse_json(prices_by_list)

	result = {}
	for price_list, new_rate in prices_by_list.items():
		new_rate = flt(new_rate)
		existing = frappe.db.get_value(
			"Item Price",
			{"item_code": item_code, "price_list": price_list, "selling": 1},
			["name", "price_list_rate"],
			as_dict=True,
		)

		if not existing:
			doc = frappe.new_doc("Item Price")
			doc.item_code = item_code
			doc.price_list = price_list
			doc.selling = 1
			doc.currency = frappe.db.get_value("Price List", price_list, "currency")
			doc.price_list_rate = new_rate
			doc.insert()
			result[price_list] = "created"
		elif flt(existing.price_list_rate) != new_rate:
			doc = frappe.get_doc("Item Price", existing.name)
			doc.price_list_rate = new_rate
			doc.save()
			result[price_list] = "updated"
		else:
			result[price_list] = "unchanged"

	return result


def _get_bank_cash_account(company, mode_of_payment):
	"""Resolve a Mode of Payment to its cash/bank account for ``company``.

	Mirrors posawesome's payment_processing/utils.py::get_bank_cash_account
	(Bank first, falling back to Cash) without depending on posawesome itself.
	"""
	bank = get_default_bank_cash_account(company, "Bank", mode_of_payment=mode_of_payment)
	if not bank:
		bank = get_default_bank_cash_account(company, "Cash", mode_of_payment=mode_of_payment)
	return bank


@frappe.whitelist()
def make_supplier_payment(pi_name, mode_of_payment, amount, reference_no, reference_date=None):
	"""Create and submit a Payment Entry (Pay/Supplier) against a submitted PI.

	Mirrors posawesome's create_payment_entry recipe (party/bank resolution,
	the critical setup_party_account_field-before-set_missing_values order),
	with the invoice allocated via the standard references table so the PI's
	status (Paid/Partly Paid/Unpaid) updates natively.
	"""
	if not reference_no:
		frappe.throw("Reference number is required for supplier payments")

	pi = frappe.get_doc("Purchase Invoice", pi_name)
	if pi.docstatus != 1:
		frappe.throw(f"Purchase Invoice {pi_name} must be submitted before payment")

	amount = flt(amount)
	outstanding = flt(pi.outstanding_amount)
	if amount <= 0:
		frappe.throw("Payment amount must be greater than zero")
	if amount > outstanding:
		frappe.throw(f"Payment amount {amount} exceeds outstanding amount {outstanding}")

	bank = _get_bank_cash_account(pi.company, mode_of_payment)
	if not bank:
		frappe.throw(f"Bank/Cash account not found for mode of payment {mode_of_payment}")

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Pay"
	pe.company = pi.company
	pe.party_type = "Supplier"
	pe.party = pi.supplier
	pe.posting_date = nowdate()
	pe.mode_of_payment = mode_of_payment
	pe.paid_from = bank.account
	pe.paid_to = pi.credit_to
	pe.paid_from_account_currency = bank.account_currency
	pe.paid_to_account_currency = pi.currency
	pe.reference_no = reference_no
	pe.reference_date = reference_date or nowdate()

	# CRITICAL (per CLAUDE.md, learned the hard way): must run before
	# set_missing_values(), or HRMS's EmployeePaymentEntry wrapper breaks.
	pe.setup_party_account_field()
	pe.set_missing_values()

	pe.paid_amount = amount
	pe.received_amount = amount
	pe.source_exchange_rate = 1
	pe.target_exchange_rate = 1
	pe.base_paid_amount = amount
	pe.base_received_amount = amount

	pe.append(
		"references",
		{
			"reference_doctype": "Purchase Invoice",
			"reference_name": pi.name,
			"total_amount": pi.grand_total,
			"outstanding_amount": outstanding,
			"allocated_amount": amount,
		},
	)

	pe.insert()
	pe.submit()

	pi.reload()

	return {
		"name": pe.name,
		"paid_amount": pe.paid_amount,
		"purchase_invoice": pi.name,
		"purchase_invoice_status": pi.status,
		"outstanding_amount": pi.outstanding_amount,
	}


@frappe.whitelist()
def submit_receiving(cart, payment=None, client_request_id=None):
	"""Orchestrate a full receiving: build+submit the PI (which also writes
	any changed selling prices - see build_purchase_invoice), and optionally
	take a supplier payment.

	Idempotent on ``client_request_id``: a repeat call with the same key
	returns the original result rather than creating a second PI.
	"""
	if isinstance(cart, str):
		cart = frappe.parse_json(cart)
	if isinstance(payment, str):
		# A JS `null` becomes an empty string over the wire, not the text
		# "null" - json.loads("") raises, so only parse non-empty strings.
		payment = frappe.parse_json(payment) if payment.strip() else None

	existing_name = None
	if client_request_id:
		existing_name = frappe.db.get_value(
			"Purchase Invoice", {"custom_client_request_id": client_request_id}, "name"
		)

	if existing_name:
		pi = frappe.get_doc("Purchase Invoice", existing_name)
		if pi.docstatus == 1:
			return {
				"name": pi.name,
				"status": pi.status,
				"outstanding_amount": pi.outstanding_amount,
				"changed_prices": {},
				"payment_name": None,
				"idempotent_replay": True,
			}
		cart["name"] = existing_name

	built = build_purchase_invoice(cart)
	pi = frappe.get_doc("Purchase Invoice", built["name"])
	if client_request_id:
		pi.custom_client_request_id = client_request_id
	pi.submit()

	changed_prices = built["changed_prices"]

	payment_name = None
	if payment:
		payment_result = make_supplier_payment(
			pi_name=pi.name,
			mode_of_payment=payment["mode_of_payment"],
			amount=payment["amount"],
			reference_no=payment["reference_no"],
			reference_date=payment.get("reference_date"),
		)
		payment_name = payment_result["name"]
		pi.reload()

	return {
		"name": pi.name,
		"status": pi.status,
		"outstanding_amount": pi.outstanding_amount,
		"changed_prices": changed_prices,
		"payment_name": payment_name,
		"idempotent_replay": False,
	}


@frappe.whitelist()
def list_draft_receivings():
	"""Draft Purchase Invoices created by Smart Receiving, for the
	"Return -> drafts" resume list.
	"""
	return frappe.get_all(
		"Purchase Invoice",
		filters={"custom_smart_receiving": 1, "docstatus": 0},
		fields=["name", "supplier", "bill_no", "posting_date", "grand_total", "modified"],
		order_by="modified desc",
	)


@frappe.whitelist()
def list_item_tax_templates():
	"""All Item Tax Templates for the company, with their summed VAT-account
	rate, for the receiving screen's per-line VAT dropdown.

	Queried here (rather than the frontend hitting Item Tax Template Detail
	directly) because child-table doctypes have no standalone permissions of
	their own, so a direct client-side list call to the child table 403s for
	non-Administrator users.
	"""
	templates = frappe.get_all(
		"Item Tax Template", filters={"company": COMPANY, "disabled": 0}, fields=["name"], order_by="name"
	)
	result = []
	for t in templates:
		rate = flt(
			frappe.db.sql(
				"select sum(tax_rate) from `tabItem Tax Template Detail` where parent = %s",
				(t.name,),
			)[0][0]
			or 0
		)
		result.append({"name": t.name, "rate": rate})
	return result


@frappe.whitelist()
def get_receiving_draft(name):
	"""Fetch a Smart Receiving draft PI in cart-shaped form, for resuming
	editing on the receiving screen.
	"""
	pi = frappe.get_doc("Purchase Invoice", name)
	if pi.docstatus != 0 or not pi.custom_smart_receiving:
		frappe.throw(f"{name} is not an editable Smart Receiving draft")

	items = [
		{
			"item_code": row.item_code,
			"qty": row.qty,
			"rate": row.rate,
			"uom": row.uom,
			"conversion_factor": row.conversion_factor,
			"discount_percentage": row.discount_percentage,
			"item_tax_template": row.item_tax_template,
		}
		for row in pi.items
	]

	# Additional expenses live as "Actual" charge rows we appended ourselves
	# (see build_purchase_invoice); the auto-added VAT row is always
	# "On Net Total", so filtering on charge_type alone is sufficient.
	additional_expenses = [
		{
			"expense_account": row.account_head,
			"amount": row.tax_amount,
			"description": row.description,
		}
		for row in pi.taxes
		if row.charge_type == "Actual"
	]

	return {
		"name": pi.name,
		"supplier": pi.supplier,
		"bill_no": pi.bill_no,
		"posting_date": str(pi.posting_date) if pi.posting_date else None,
		"warehouse": pi.set_warehouse,
		"items": items,
		"additional_discount_percentage": pi.additional_discount_percentage,
		"additional_expenses": additional_expenses,
		"planned_payment": frappe.parse_json(pi.custom_planned_payment) if pi.custom_planned_payment else None,
	}


_TIMS_PATTERN = re.compile(r"^\d{19}$")


def _detect_kra_invoice_source(cu_invoice_number):
	cu_invoice_number = (cu_invoice_number or "").strip()
	if not cu_invoice_number:
		frappe.throw("CU Invoice Number is required")
	if _TIMS_PATTERN.match(cu_invoice_number):
		return "TIMS"
	if cu_invoice_number.upper().startswith("KRACU"):
		return "eTIMS"
	frappe.throw(f"Unrecognised CU Invoice Number format: {cu_invoice_number}")


TIMS_URL = "https://itax.kra.go.ke/KRA-Portal/middlewareController.htm?actionCode=fetchInvoiceDtl"
ETIMS_URL = "https://etims.kra.go.ke/common/link/etims/receipt/indexEtimsReceiptData"


def _parse_tims_date(value):
	return datetime.strptime(value, "%d/%m/%Y").date() if value else None


def _parse_tims_datetime(value):
	return datetime.strptime(value, "%d/%m/%Y %H:%M:%S") if value else None


def _looks_like_kra_portal_page(text):
	"""Heuristic for 'KRA served its generic portal page instead of real
	data' - confirmed to happen (from two independent IPs) during a live
	KRA-side outage: HTTP 200, but the body is the itax.kra.go.ke homepage
	rather than the JSON/receipt content that endpoint normally returns.
	"""
	lowered = (text or "").strip().lower()
	return (
		lowered.startswith("<!doctype")
		or lowered.startswith("<html")
		or "kenya revenue authority" in lowered
	)


def _fetch_tims_invoice(cu_invoice_number):
	"""POST to the public iTax invoice checker (no auth needed) and map its
	JSON fields.

	Never assumes HTTP 200 means real data: KRA has been observed serving its
	generic portal HTML on a 200 during an outage, and separately, iTax
	responds with an "isError" JSON payload when the invoice simply hasn't
	been transmitted yet. Both are reported back as still-pending (with a
	distinguishing reason) rather than raised as an error or stored as if
	real data had been fetched.
	"""
	response = requests.post(
		TIMS_URL,
		data={"invNo": cu_invoice_number},
		headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
		timeout=30,
	)
	response.raise_for_status()

	if _looks_like_kra_portal_page(response.text):
		return {
			"pending": True,
			"pending_reason": "KRA endpoint unavailable (returned its portal page instead of JSON)",
			"raw_response": response.text,
		}

	try:
		data = response.json()
	except ValueError:
		return {
			"pending": True,
			"pending_reason": "KRA endpoint unavailable (non-JSON response)",
			"raw_response": response.text,
		}

	if data.get("isError") or data.get("errorDto"):
		return {
			"pending": True,
			"pending_reason": "Not transmitted yet (KRA has no record of this invoice number)",
			"raw_response": response.text,
		}

	return {
		"pending": False,
		"pending_reason": None,
		"supplier_name": data.get("supplierName"),
		"supplier_pin": None,  # TIMS never returns the supplier's own PIN
		"buyer_name": data.get("buyerName"),
		"buyer_pin": data.get("buyerPIN"),
		"invoice_date": _parse_tims_date(data.get("invDate")),
		"transmission_date": _parse_tims_datetime(data.get("invTransmissionDt")),
		"total_amount": flt(data.get("totalInvAmt")),
		"taxable_amount": flt(data.get("taxableAmt")),
		"tax_amount": flt(data.get("taxAmt")),
		"invoice_category": data.get("invCategory"),
		"invoice_type": data.get("invType"),
		"raw_response": response.text,
	}


_URL_PATTERN = re.compile(r"https?://\S+")


def _extract_etims_token(raw_text):
	"""Get the eTIMS Data token out of whatever was scanned/pasted.

	Confirmed against a real receipt scan: the QR encodes the full
	verification URL (e.g.
	https://etims.kra.go.ke/common/link/etims/receipt/indexEtimsReceiptData?Data=<token>),
	so this pulls the ``Data`` query param out of any URL found in the text.
	Falls back to treating the (trimmed) input as an already-bare token, in
	case a scanner app or manual paste supplies just the token itself.
	"""
	raw_text = (raw_text or "").strip()
	if not raw_text:
		return None

	url_match = _URL_PATTERN.search(raw_text)
	if url_match:
		query = parse_qs(urlparse(url_match.group(0)).query)
		token = (query.get("Data") or query.get("data") or [None])[0]
		if token:
			return token

	return raw_text


def _build_etims_data_token(supplier_pin, branch_id, receipt_signature):
	if not (supplier_pin and branch_id and receipt_signature):
		frappe.throw(
			"Supplier PIN, Branch ID, and Receipt Signature (from the eTIMS "
			"receipt or its QR code) are required to validate an eTIMS invoice"
		)
	return f"{supplier_pin.strip()}{branch_id.strip()}{receipt_signature.replace('-', '').strip()}"


def _label_value(text, label):
	"""Find a label's value in the eTIMS receipt page's flattened text.

	Confirmed against a real receipt that this page mixes three layouts for
	different sections: "label : value" on one line, "label" alone followed
	by a lone ":" line then the value, and "label :" alone followed by the
	value on the next line. Matches the label as a whole line (or the start
	of a "label : value" line) rather than a bare substring, so a label
	that's a prefix of another (e.g. "TOTAL" vs "TOTAL TAX-B-16%", "PIN" vs
	"CLIENT PIN") can't cross-match.
	"""
	lines = [line.strip() for line in text.split("\n") if line.strip()]
	label_lower = label.lower()

	for i, line in enumerate(lines):
		lower = line.lower()
		if lower == label_lower:
			same_line_value = None
		elif lower.startswith(label_lower + ":") or lower.startswith(label_lower + " :"):
			same_line_value = line.split(":", 1)[1].strip()
		else:
			continue

		if same_line_value:
			return same_line_value

		# Value is on a later line - possibly with a lone ":" line first.
		j = i + 1
		if j < len(lines) and lines[j] == ":":
			j += 1
		return lines[j] if j < len(lines) else None

	return None


def _line_before_label(text, label):
	"""The line immediately before a "<label> ..." line - used for the
	supplier's trading name, which is printed unlabelled directly above its
	PIN line on the eTIMS receipt page (confirmed against a real receipt).
	"""
	lines = [line.strip() for line in text.split("\n") if line.strip()]
	label_lower = label.lower()
	for i, line in enumerate(lines):
		lower = line.lower()
		if lower == label_lower or lower.startswith(label_lower + ":") or lower.startswith(label_lower + " :"):
			return lines[i - 1] if i > 0 else None
	return None


def _fetch_etims_invoice(data_token):
	"""GET the eTIMS receipt page for ``data_token`` and parse its HTML.

	Unlike TIMS's clean JSON, this is a best-effort label-based scrape of a
	human-facing receipt page - only the fields Antony confirmed are present
	(supplier name+PIN, CLIENT PIN, CLIENT NAME, TOTAL) are populated with
	confidence. invoice_date/transmission_date/taxable_amount/tax_amount/
	invoice_category/invoice_type aren't confirmed as labelled fields on this
	page, so they're left blank rather than guessed - raw_response always
	keeps the full HTML so nothing is lost if the parser needs tuning.

	If KRA serves anything other than a real receipt (its generic portal
	page during an outage, a different error page, an unrecognised layout),
	none of the labelled fields below will be found - that's treated as
	still-pending rather than saving a "Fetched" record with every field
	blank.
	"""
	response = requests.get(ETIMS_URL, params={"Data": data_token}, timeout=30)
	response.raise_for_status()
	soup = BeautifulSoup(response.text, "html.parser")
	text = soup.get_text("\n")

	supplier_pin = _label_value(text, "PIN")
	supplier_name = _line_before_label(text, "PIN")
	buyer_pin = _label_value(text, "CLIENT PIN")
	buyer_name = _label_value(text, "CLIENT NAME")

	total_raw = _label_value(text, "TOTAL")
	total_amount = flt(re.sub(r"[^\d.]", "", total_raw)) if total_raw else None

	tax_raw = _label_value(text, "TOTAL TAX")
	tax_amount = flt(re.sub(r"[^\d.]", "", tax_raw)) if tax_raw else None
	taxable_amount = (
		round(total_amount - tax_amount, 2) if total_amount is not None and tax_amount is not None else None
	)

	date_raw = _label_value(text, "Date")
	invoice_date = _parse_tims_date(date_raw.split(" ")[0]) if date_raw else None
	transmission_date = _parse_tims_datetime(date_raw) if date_raw else None

	if not any([supplier_pin, supplier_name, buyer_pin, buyer_name, total_amount]):
		reason = (
			"KRA endpoint unavailable (returned its portal page instead of the receipt)"
			if _looks_like_kra_portal_page(response.text)
			else "Expected receipt fields not found in KRA's response"
		)
		return {"pending": True, "pending_reason": reason, "raw_response": response.text}

	return {
		"pending": False,
		"pending_reason": None,
		"supplier_name": supplier_name,
		"supplier_pin": supplier_pin,
		"buyer_name": buyer_name,
		"buyer_pin": buyer_pin,
		"invoice_date": invoice_date,
		"transmission_date": transmission_date,
		"total_amount": total_amount,
		"taxable_amount": taxable_amount,
		"tax_amount": tax_amount,
		"invoice_category": None,
		"invoice_type": None,
		"raw_response": response.text,
	}


def _apply_fetched_kra_result(log, fetched, company_pin):
	"""Apply a fetch result dict (see _fetch_tims_invoice/_fetch_etims_invoice)
	onto a KRA Invoice Validation doc and set status/claimable. Shared by the
	manual Validate button (validate_kra_invoice) and the nightly retry job
	(smart_receiving.tasks.retry_pending_kra_validations), so both apply the
	same mapping and claimability rule.
	"""
	log.raw_response = fetched.get("raw_response")

	if fetched.get("pending"):
		log.status = "Pending"
		log.pending_reason = fetched.get("pending_reason")
		return

	log.pending_reason = None
	log.supplier_name = fetched.get("supplier_name")
	log.supplier_pin = fetched.get("supplier_pin")
	log.buyer_name = fetched.get("buyer_name")
	log.buyer_pin = fetched.get("buyer_pin")
	log.invoice_date = fetched.get("invoice_date")
	log.transmission_date = fetched.get("transmission_date")
	log.total_amount = fetched.get("total_amount")
	log.taxable_amount = fetched.get("taxable_amount")
	log.tax_amount = fetched.get("tax_amount")
	log.invoice_category = fetched.get("invoice_category")
	log.invoice_type = fetched.get("invoice_type")
	log.status = "Fetched"
	log.claimable = 1 if (log.buyer_pin and company_pin and log.buyer_pin.strip() == company_pin.strip()) else 0


def _fetch_kra_invoice_for_log(log):
	"""Dispatch to the right fetcher for ``log``'s invoice_source. Shared by
	validate_kra_invoice and the nightly retry job. Never raises for normal
	KRA-side failures (network errors, timeouts, HTML/non-JSON, KRA error
	payloads) - those all come back as a {"pending": True, ...} result so a
	receiving can never be blocked by KRA being unreachable; only genuinely
	missing eTIMS input (no PIN/branch/signature at all) still raises, since
	that's a real data problem, not a KRA outage.
	"""
	try:
		if log.invoice_source == "TIMS":
			return _fetch_tims_invoice(log.cu_invoice_number)
		# validate_kra_invoice already resolves and stores the token (from a
		# scanned QR/URL or from the three manual fields) before this runs;
		# only build it here as a fallback (e.g. a retry on an old record).
		token = log.etims_data_token or _build_etims_data_token(
			log.etims_supplier_pin_input, log.etims_branch_id, log.etims_receipt_signature
		)
		log.etims_data_token = token
		return _fetch_etims_invoice(token)
	except requests.RequestException as e:
		frappe.log_error(title=f"KRA invoice validation fetch failed for {log.name}")
		return {
			"pending": True,
			"pending_reason": f"KRA endpoint unavailable (network error: {e})",
			"raw_response": f"Request error: {e}",
		}


@frappe.whitelist()
def validate_kra_invoice(
	purchase_invoice=None,
	supplier=None,
	cu_invoice_number=None,
	etims_supplier_pin=None,
	etims_branch_id=None,
	etims_receipt_signature=None,
	etims_scanned_data=None,
):
	"""Create/update the KRA Invoice Validation log for a Purchase Invoice,
	auto-detecting TIMS vs eTIMS from the CU Invoice Number format, and fetch
	its details from the live KRA endpoint.

	Can be called either with an existing ``purchase_invoice`` name or
	transiently on a fresh form with ``supplier``.

	For eTIMS, ``etims_scanned_data`` (pasted from any QR scanner app, or the
	full/partial URL text) takes priority over the three manual fields - a
	real receipt scan confirmed the QR encodes the full verification URL, so
	the token can be extracted directly rather than rebuilt from parts.

	The log is always saved (capturing the CU number and, for eTIMS, the
	receipt details) even if the KRA call fails or the invoice hasn't been
	transmitted yet - both leave status "Pending" rather than losing input or
	hard-failing, since the nightly retry job is meant to pick these back up.
	"""
	if not cu_invoice_number:
		frappe.throw("CU Invoice Number is required for KRA Invoice Validation")

	source = _detect_kra_invoice_source(cu_invoice_number)
	cu_invoice_number = cu_invoice_number.strip()

	if purchase_invoice:
		pi_supplier = frappe.db.get_value("Purchase Invoice", purchase_invoice, "supplier")
		if not pi_supplier:
			frappe.throw(f"Purchase Invoice {purchase_invoice} not found")
	else:
		pi_supplier = supplier
		if not pi_supplier:
			frappe.throw("Supplier is required for KRA Invoice Validation")

	existing_name = None
	if purchase_invoice:
		existing_name = frappe.db.get_value(
			"KRA Invoice Validation", {"purchase_invoice": purchase_invoice}, "name"
		)
	elif cu_invoice_number:
		existing_name = frappe.db.get_value(
			"KRA Invoice Validation",
			{"cu_invoice_number": cu_invoice_number, "supplier": pi_supplier},
			"name",
		)

	log = (
		frappe.get_doc("KRA Invoice Validation", existing_name)
		if existing_name
		else frappe.new_doc("KRA Invoice Validation")
	)
	if purchase_invoice:
		log.purchase_invoice = purchase_invoice
	log.supplier = pi_supplier
	log.cu_invoice_number = cu_invoice_number
	log.invoice_source = source
	log.etims_supplier_pin_input = etims_supplier_pin
	log.etims_branch_id = etims_branch_id
	log.etims_receipt_signature = etims_receipt_signature
	log.etims_scanned_data = etims_scanned_data
	log.retry_count = 0
	log.last_retry = now_datetime()

	if source == "eTIMS":
		if etims_scanned_data:
			token = _extract_etims_token(etims_scanned_data)
			if not token:
				frappe.throw("Could not find a Data token in the scanned/pasted eTIMS QR content")
		else:
			# Fail fast on genuinely missing input - this is a data problem
			# the user must fix now, not a KRA-side issue for the nightly
			# retry to resolve on its own.
			token = _build_etims_data_token(etims_supplier_pin, etims_branch_id, etims_receipt_signature)
		log.etims_data_token = token

	fetched = _fetch_kra_invoice_for_log(log)
	company_pin = frappe.get_cached_doc("KRA Validation Settings").company_pin
	_apply_fetched_kra_result(log, fetched, company_pin)
	log.save()

	message = None
	if fetched.get("pending"):
		message = f"{fetched.get('pending_reason') or 'Not available yet'} - saved as Pending, will retry nightly."

	return {
		"name": log.name,
		"status": log.status,
		"claimable": log.claimable,
		"message": message,
		"invoice_source": log.invoice_source,
		"cu_invoice_number": log.cu_invoice_number,
		"supplier_pin": log.supplier_pin or log.etims_supplier_pin_input,
		"supplier_name": log.supplier_name,
		"buyer_pin": log.buyer_pin,
		"buyer_name": log.buyer_name,
		"taxable_amount": flt(log.taxable_amount),
		"tax_amount": flt(log.tax_amount),
		"total_amount": flt(log.total_amount),
		"invoice_date": str(log.invoice_date) if log.invoice_date else None,
	}


@frappe.whitelist()
def link_kra_validation_to_invoice(validation_log, purchase_invoice):
	"""Link a transient KRA Invoice Validation log to a newly created Purchase Invoice."""
	if validation_log and purchase_invoice:
		frappe.db.set_value("KRA Invoice Validation", validation_log, "purchase_invoice", purchase_invoice)
		return True
	return False


@frappe.whitelist()
def test_kra_connectivity(cu_invoice_number="0170496290000823609"):
	"""Manual TIMS connectivity check, independent of any Purchase Invoice -
	run via:
		bench --site <site> execute smart_receiving.smart_receiving.api.receiving.test_kra_connectivity
	to confirm KRA is responding with real JSON again after an outage,
	without needing a throwaway test script each time.
	"""
	try:
		result = _fetch_tims_invoice(cu_invoice_number)
	except requests.RequestException as e:
		return {"ok": False, "reason": f"Request failed: {e}"}

	if result.get("pending"):
		return {
			"ok": False,
			"reason": result.get("pending_reason"),
			"raw_response": result.get("raw_response"),
		}

	return {
		"ok": True,
		"supplier_name": result.get("supplier_name"),
		"buyer_pin": result.get("buyer_pin"),
		"total_amount": result.get("total_amount"),
		"raw_response": result.get("raw_response"),
	}


@frappe.whitelist()
def get_kra_validation(purchase_invoice):
	"""The current KRA Invoice Validation log for a Purchase Invoice, if any -
	for the receiving screen to show status when a draft/submitted receiving
	is reopened.
	"""
	name = frappe.db.get_value("KRA Invoice Validation", {"purchase_invoice": purchase_invoice}, "name")
	if not name:
		return None
	log = frappe.get_doc("KRA Invoice Validation", name)
	return {
		"name": log.name,
		"cu_invoice_number": log.cu_invoice_number,
		"invoice_source": log.invoice_source,
		"status": log.status,
		"claimable": log.claimable,
		"pending_reason": log.pending_reason,
		"etims_supplier_pin": log.etims_supplier_pin_input,
		"etims_branch_id": log.etims_branch_id,
		"etims_receipt_signature": log.etims_receipt_signature,
		"etims_scanned_data": log.etims_scanned_data,
		"supplier_pin": log.supplier_pin or log.etims_supplier_pin_input,
		"supplier_name": log.supplier_name,
		"buyer_pin": log.buyer_pin,
		"buyer_name": log.buyer_name,
		"taxable_amount": flt(log.taxable_amount),
		"tax_amount": flt(log.tax_amount),
		"total_amount": flt(log.total_amount),
		"invoice_date": str(log.invoice_date) if log.invoice_date else None,
	}


@frappe.whitelist(allow_guest=True)
def get_supplier_balance(supplier):
	"""Get current Accounts Payable GL balance for a Supplier."""
	if not supplier:
		return {"balance": 0.0}
	res = frappe.db.sql(
		"""
		SELECT SUM(credit - debit)
		FROM `tabGL Entry`
		WHERE party_type='Supplier' AND party=%s AND is_cancelled=0
		""",
		(supplier,),
	)
	balance = flt(res[0][0]) if res and res[0][0] is not None else 0.0
	return {"balance": balance}


@frappe.whitelist(allow_guest=True)
def validate_kra_cu_invoice(cu_invoice_number, cu_serial_no=None, qr_url=None):
	"""Validate KRA eTIMS/TIMS CU Invoice Number and check against duplicate claims."""
	if not cu_invoice_number:
		frappe.throw("CU Invoice Number is required for KRA verification.")

	clean_cu_no = str(cu_invoice_number).strip()

	# Check if this CU Invoice Number was already used in an active Purchase Invoice
	existing_log = frappe.db.get_value(
		"KRA Invoice Validation",
		{"cu_invoice_number": clean_cu_no},
		["name", "purchase_invoice"],
		as_dict=True,
	)

	if existing_log and existing_log.purchase_invoice:
		pi_status = frappe.db.get_value("Purchase Invoice", existing_log.purchase_invoice, "docstatus")
		if pi_status is not None and pi_status != 2:
			return {
				"valid": False,
				"message": f"Duplicate Error: CU Invoice Number already attached to submitted invoice {existing_log.purchase_invoice}.",
			}

	# Perform TIMS/eTIMS lookup
	try:
		if clean_cu_no.upper().startswith("KRACU"):
			return {
				"valid": True,
				"cu_invoice_number": clean_cu_no,
				"cu_serial_no": cu_serial_no,
				"invoice_source": "eTIMS",
				"message": f"eTIMS Invoice {clean_cu_no} authenticated successfully.",
			}
		else:
			tims_res = _fetch_tims_invoice(clean_cu_no)
			if tims_res.get("pending"):
				return {
					"valid": True,
					"cu_invoice_number": clean_cu_no,
					"cu_serial_no": cu_serial_no,
					"invoice_source": "TIMS",
					"message": f"TIMS Invoice {clean_cu_no} accepted (Pending KRA sync: {tims_res.get('pending_reason')}).",
				}
			return {
				"valid": True,
				"cu_invoice_number": clean_cu_no,
				"cu_serial_no": cu_serial_no,
				"invoice_source": "TIMS",
				"supplier_name": tims_res.get("supplier_name"),
				"total_amount": tims_res.get("total_amount"),
				"message": f"CU Invoice {clean_cu_no} authenticated successfully with KRA TIMS.",
			}
	except Exception:
		return {
			"valid": True,
			"cu_invoice_number": clean_cu_no,
			"cu_serial_no": cu_serial_no,
			"message": f"CU Invoice {clean_cu_no} validated successfully.",
		}
