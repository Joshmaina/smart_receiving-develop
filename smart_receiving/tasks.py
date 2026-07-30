import time

import frappe
from frappe.utils import get_datetime, now_datetime

from smart_receiving.smart_receiving.api.receiving import _apply_fetched_kra_result, _fetch_kra_invoice_for_log

# Politely spaced, one at a time - never parallel - so we don't hammer a
# government tax portal with a batch job.
RETRY_DELAY_SECONDS = 4


def retry_pending_kra_validations():
	"""Nightly job: retry every "Pending" KRA Invoice Validation, throttled
	and sequential. Anything still Pending after the configured age-out
	(default 30 days from KRA Validation Settings) is switched to "Manual
	Review Needed" instead of being retried forever.

	Only ever touches Pending records - once a validation is "Fetched" it is
	never re-fetched here, so an already-validated invoice never causes a
	repeat KRA call.
	"""
	settings = frappe.get_cached_doc("KRA Validation Settings")
	if not settings.enable_nightly_retry:
		return

	age_out_days = settings.retry_age_out_days or 30
	company_pin = settings.company_pin

	pending_names = frappe.get_all(
		"KRA Invoice Validation", filters={"status": "Pending"}, pluck="name"
	)

	for name in pending_names:
		log = frappe.get_doc("KRA Invoice Validation", name)
		age_days = (now_datetime() - get_datetime(log.creation)).days

		if age_days > age_out_days:
			log.status = "Manual Review Needed"
			log.save()
			continue

		fetched = _fetch_kra_invoice_for_log(log)
		_apply_fetched_kra_result(log, fetched, company_pin)
		log.retry_count = (log.retry_count or 0) + 1
		log.last_retry = now_datetime()
		log.save()
		frappe.db.commit()

		time.sleep(RETRY_DELAY_SECONDS)
