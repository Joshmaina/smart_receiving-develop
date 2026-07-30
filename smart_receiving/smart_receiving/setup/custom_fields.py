import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Invoice": [
		{
			"fieldname": "custom_smart_receiving",
			"label": "Smart Receiving",
			"fieldtype": "Check",
			"insert_after": "title",
			"read_only": 1,
			"print_hide": 1,
			"description": "Set when this Purchase Invoice was created by the Smart Receiving app.",
		},
		{
			"fieldname": "custom_client_request_id",
			"label": "Smart Receiving Client Request ID",
			"fieldtype": "Data",
			"insert_after": "custom_smart_receiving",
			"read_only": 1,
			"print_hide": 1,
			"description": "Idempotency key used by Smart Receiving to avoid duplicate submissions.",
		},
		{
			"fieldname": "custom_planned_payment",
			"label": "Smart Receiving Planned Payment",
			"fieldtype": "Long Text",
			"insert_after": "custom_client_request_id",
			"hidden": 1,
			"no_copy": 1,
			"print_hide": 1,
			"description": "JSON snapshot of the payment the user entered but hasn't submitted yet, so it survives a Save as Draft/resume cycle.",
		},
	]
}


def create_smart_receiving_custom_fields():
	"""Idempotently create the custom fields Smart Receiving depends on.

	Called from after_migrate. Never add these by hand on live - this is the
	single source of truth, also exported to fixtures/custom_field.json.
	"""
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=frappe.flags.in_patch, update=True)
