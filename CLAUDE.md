# CLAUDE.md — Smart Receiving (project brief for Claude Code)

Read this file fully at the start of every session before doing anything.

## Who and what
- You are helping **Antony Kiplimo** build **Smart Receiving**, a custom ERPNext/Frappe **v15** app.
- Antony runs **Structured Data** (the dev company). **Bevali Online** is the retail client whose data we develop against.
- Antony is a careful, non-professional developer. **Work one step at a time. Let him confirm (often by screenshot) before the next step. Never batch many steps.**
- Explain what each command/change does and *why*, in plain language, before running it.
- When unsure of an exact DocType name, fieldname, or setup detail: **ask, do not guess.**
- Prefer the ERPNext Desk UI when it can genuinely do the job; reach for code only when it can't.
- When editing scripts/code, give **full file replacements**, not partial diffs.

## What Smart Receiving is (one paragraph)
A UltimatePOS-style single-screen goods-receiving UI that, on save, creates **standard ERPNext documents** underneath — a **Purchase Invoice** (`update_stock=1`) and optional **Payment Entry** — exactly the way POS Awesome creates a standard Sales Invoice + Payment Entry. It never invents its own accounting or stock. Its extra value: setting selling price + profit margin at receiving time, editing multiple selling price lists per item, and (Phase 2) KRA invoice validation. See `smart_receiving_spec.md` for the full spec.

## Environment — TEST BENCH (this is where we build)
- **Host:** Contabo VM, SSH `frappe@45.85.250.200`.
- **Bench:** `/home/frappe/frappe-bench`. Linux user: `frappe`.
- **Site:** `online.bevalicore.com` (folder name), reachable in browser at **`http://bevali.co.ke`**.
- This is a **restored copy of live**, deliberately **neutralized**:
  - `mute_emails=1`, scheduler paused/disabled.
  - Kopokopo Settings disarmed: `stk_enabled=0`, environment Sandbox, creds `DISABLED_ON_TEST`.
  - `host_name=http://bevali.co.ke`.
  - **Do not re-enable emails, the scheduler, or payment credentials on this box.**
- Real nginx config in use is `/etc/nginx/conf.d/frappe-bench.conf` (NOT the bench-generated path). `access_log ... main;` was removed from it (undefined log format).
- **Never point anything at the live Google VM.** Live is a separate machine serving real customers.

## Installed apps (test bench, aligned to live)
`frappe 15.109.0`, `erpnext 15.109.3`, `hrms 15.60.3`, `posawesome 15.30.0` (branch `bevali-live-stk-15.30.0`, our fork), `kopokopo_erpnext 3.0.0`, `cash_management 0.0.1`. Python 3.12, Node 20, MariaDB 10.11.

## Bevali facts you will need
- Company: `BEVALI ONLINE` (abbr `BO`). Company KRA PIN: `P052216114Z`.
- Warehouses: `Rupa - BO` (receiving/source — default for receiving), `Zion Mall - BO` (selling store).
- Primary selling price list: `Zion Retail Price` (+ 2 test lists Antony will add). Auto-discover all **enabled Selling** price lists.
- VAT: `Purchase VAT 16% - BO`; item tax templates `V - BO` / `E - BO` / `Z - BO`; suppliers use tax category `Purchase`.
- Item codes are **numeric strings with significant leading zeros** (e.g. `0004`). Never coerce to int; keep as text.

## The proven pattern to mirror (from posawesome on this bench)
Study, don't reinvent. Relevant files (note nested path `apps/posawesome/posawesome/posawesome/api/...`):
- `invoice_processing/creation.py` → `update_invoice` (line ~764), `submit_invoice` (~990): cart → Sales Invoice.
- `payment_processing/creation.py` → `create_payment_entry`: builds Payment Entry; **already supports our case** via `payment_type="Pay"`, `party_type="Supplier"`; resolves Mode of Payment → account via `get_bank_cash_account`.
- `api/idempotency.py`: `client_request_id` pattern to prevent double-posting.

**Smart Receiving inverts these into a buying flow:**
- `build_purchase_invoice(cart)` → `new_doc("Purchase Invoice")`, `update_stock=1`, warehouse, rows, taxes; `set_missing_values()` then `calculate_taxes_and_totals()`; set `ignore_pricing_rule=1` so entered costs win.
- `make_supplier_payment(...)` → mirror `create_payment_entry` with Pay/Supplier.

### CRITICAL code-ordering rules (learned the hard way)
- On Payment Entry: call `setup_party_account_field()` **before** `set_missing_values()`. HRMS wraps PE as `EmployeePaymentEntry`; the wrong order breaks it.
- Never hand-roll tax/total math — always `calculate_taxes_and_totals()`.
- Carry `client_request_id` on submit for idempotency.

## Safety rules for this project
- **Backup before any bulk/data operation:** `bench --site online.bevalicore.com backup`.
- Test every change against **both** the document view **and** Stock Ledger + General Ledger — quantity on screen does NOT prove the ledger is right.
- Reversible / commented changes preferred.
- `git clean -fd` and `rm -rf` are dangerous — only on the test box, only when explicitly agreed.
- Custom fields on third-party doctypes: add via **fixtures** / `create_custom_fields` in `after_migrate` (idempotent), never by hand on live.
- After frontend changes: `bench build`; after code/hook changes: `bench --site online.bevalicore.com clear-cache && bench restart`. Stale workers cause phantom ImportErrors — restart when in doubt.

## Git / GitHub
- GitHub user `antonykiplimo`, HTTPS + classic PAT, remote conventionally named `github` (not `origin`).
- posawesome fork: `antonykiplimo/bevali-posawesome-V15`, remote `bevali`, branch `bevali-live-stk-15.30.0`. Do not lose this patch on posawesome upgrades.
- Smart Receiving will get its own private repo. Push often. Pin deploys to a tested commit/tag.

## Deploy path (later)
Build & test on Contabo → push to GitHub → on live Google VM: backup → `bench get-app` (pinned) → `install-app` / `migrate` → verify ledgers. Never develop on live.

## Build order (do NOT jump ahead)
1. **Phase 1 — Receiving core** (server methods first, then Vue UI). ← current
2. Phase 2 — KRA validation module (field maps already verified against live KRA endpoints; see spec §5).
3. Phase 3 — Reporting & delivery.

## Housekeeping owed on Contabo (remind Antony)
- `history -c` (MariaDB root pw + KopoKopo client_id appeared in shell history).
- Rotate Contabo **MariaDB root password**; consider rotating **KopoKopo API creds**.

---
*Keep this file updated as the app evolves. It is the single source of truth for any Claude Code session on Smart Receiving.*
