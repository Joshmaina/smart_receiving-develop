# Smart Receiving — Alignment Spec (v0.1)

**Owner:** Antony Kiplimo (Structured Data)
**Primary client / test data:** Bevali Online (`BEVALI ONLINE`, abbr `BO`)
**Status:** Spec for review — **no code until this is agreed**
**Author of build:** Claude Code, on the Contabo test bench (`bevali.co.ke`)
**Model mirrored:** POS Awesome (selling side) → Smart Receiving (buying side)

---

## 1. What Smart Receiving is

Smart Receiving is a custom ERPNext/Frappe app that provides a **fast, single-screen goods-receiving interface** modelled on UltimatePOS's "Add Purchase" screen, but built the way POS Awesome is built: a purpose-made UI that, on save, creates **standard ERPNext documents** underneath.

**The core principle (non-negotiable):** Smart Receiving never invents its own accounting or stock logic. It is an *interface*. The real records are standard ERPNext **Purchase Invoices** (with `update_stock = 1`) and **Payment Entries**. This mirrors exactly how POS Awesome completing a sale produces a standard Sales Invoice, and "Pay & Submit" produces a standard Payment Entry.

Because the underlying records are standard ERPNext:
- Stock ledger, GL, tax, and supplier-balance logic all work for free.
- Standard reports work.
- KRA validation attaches to the real Purchase Invoice.
- The app is sellable because it is "just ERPNext underneath."

### Why it exists (the value over native ERPNext)
The native Purchase Invoice form does not surface the two things that make UltimatePOS receiving good for a retail/minimart business:
1. **Setting the selling price at the moment of receiving**, with **live profit-margin %** visibility.
2. **Editing multiple price lists' selling prices** for each item in one place, at receiving time.

Plus the Kenya-specific need:
3. **KRA invoice validation** (CU number lookup) built into the receiving flow.

---

## 2. Confirmed design decisions (locked with Antony)

| # | Decision | Detail |
|---|----------|--------|
| 1 | **Custom UI** from the start | A Frappe page (Vue / Frappe UI) over a clean server-method layer — not enhanced-native-PI. |
| 2 | **Underlying record** | Standard **Purchase Invoice**, `update_stock = 1`. Mirrors POS Awesome ↔ Sales Invoice. |
| 3 | **Multi-price-list editing** | Each line expands (vertical panel) to show every *Selling* price list's current price for that item; all editable; on save, **only changed prices are written** to Item Price (unchanged = no write). |
| 4 | **Margin** | Two-way live binding (type margin% → selling price; type selling price → margin%) tied to the **primary selling price list** (`Zion Retail Price`). Other price lists are plain editable prices (no margin column). |
| 5 | **Payment** | Optional. Uses **Mode of Payment** (already mapped to cash/bank accounts). **Reference mandatory.** Full → PI `Paid`; partial → `Partly Paid`; none → `Unpaid`. Creates a standard **Payment Entry** (`payment_type="Pay"`, `party_type="Supplier"`). |
| 6 | **Price lists today** | `Zion Retail Price` (primary) + 2 test lists Antony will add. Screen **auto-discovers** all enabled Selling price lists so new ones appear automatically. |
| 7 | **KRA** | A **module inside** Smart Receiving (not a separate app). Built **after** the receiving core. |
| 8 | **Build order** | Receiving core first → KRA validation second → reporting/delivery third. |

---

## 3. Architecture

```
┌─────────────────────────────────────────────┐
│  Smart Receiving UI  (Frappe page, Vue)      │
│  - supplier, ref, date, warehouse, MOP       │
│  - item grid: qty, cost, disc, tax           │
│  - per-line expandable multi-price-list panel│
│  - margin% ↔ selling price (primary list)    │
│  - optional payment block                    │
└───────────────┬─────────────────────────────┘
                │  calls whitelisted server methods
                ▼
┌─────────────────────────────────────────────┐
│  Server layer (Python, @frappe.whitelist)    │
│  - item search / price / margin helpers      │
│  - build_purchase_invoice(cart)  → std PI    │
│  - upsert_item_prices(changed)   → Item Price│
│  - make_supplier_payment(...)    → Pay. Entry│
│  - (Phase 2) kra_validate(cu_no) → KRA log   │
│  - idempotency via client_request_id         │
└───────────────┬─────────────────────────────┘
                │  creates / updates
                ▼
┌─────────────────────────────────────────────┐
│  STANDARD ERPNext documents                  │
│  - Purchase Invoice (update_stock=1)         │
│  - Item Price (per selling price list)       │
│  - Payment Entry (Pay / Supplier)            │
│  - (Phase 2) KRA Invoice Validation (custom) │
└─────────────────────────────────────────────┘
```

**Key rule:** the UI holds *no* business logic beyond input/display. All creation/validation lives in whitelisted server methods, so it is testable and reusable even if the UI is replaced.

---

## 4. The pattern we mirror from POS Awesome (verified in code)

Studied on the live-patched posawesome (`bevali-live-stk-15.30.0`). Smart Receiving inverts the selling flow into a buying flow.

### 4.1 Invoice creation — from `invoice_processing/creation.py::update_invoice`
- Take cart JSON → build a mutable invoice doc (new or loaded draft).
- Auto-create the party if it doesn't exist (Customer there → **Supplier** here; later populate Tax ID from KRA supplier PIN).
- Set `ignore_pricing_rule = 1` so the operator's explicit entered costs/rates win over auto-pricing.
- Call `set_missing_values()` to let ERPNext fill defaults.
- Call `calculate_taxes_and_totals()` — never hand-roll tax math.
- Carry a `client_request_id` for **idempotency** (no double-post on double-click).

**Smart Receiving equivalent:** `build_purchase_invoice(cart)` → new_doc("Purchase Invoice"), map rows, `update_stock=1`, `set_warehouse`, taxes, `set_missing_values()`, `calculate_taxes_and_totals()`.

### 4.2 Payment — from `payment_processing/creation.py::create_payment_entry`
This function already supports our exact case via parameters:
- `payment_type="Pay"`, `party_type="Supplier"`.
- `paid_from = bank.account` (the MOP's cash/bank account), `paid_to = party_account` (supplier payable).
- Mode of Payment → account resolved via `get_bank_cash_account(company, mode_of_payment, ...)`.
- `reference_no` / `reference_date` set from the screen.
- **Critical ordering (also in Antony's handover notes):** call `pe.setup_party_account_field()` **before** `pe.set_missing_values()` — HRMS wraps PE as `EmployeePaymentEntry` and reversing this order breaks it.

**Smart Receiving equivalent:** `make_supplier_payment(pi_name, mode_of_payment, amount, reference_no, reference_date)` → reuse this exact recipe with `payment_type="Pay"`.

---

## 5. Phased build plan

### Phase 1 — Receiving core (start here)
Goal: a working receiving screen that creates a real Purchase Invoice + optional Payment Entry, with margin & multi-price-list editing.

1. **App scaffold** — `bench new-app smart_receiving`; install on `bevali.co.ke`; GitHub repo; `CLAUDE.md` in place.
2. **Server layer (build & test headless first, before the UI):**
   - `search_items(term, warehouse)` — name / code / barcode lookup (can reference posawesome item_processing).
   - `get_item_receiving_context(item_code)` — current cost, current selling prices across **all enabled Selling price lists**, primary list, tax template, current stock.
   - `build_purchase_invoice(cart)` — draft PI, `update_stock=1`, warehouse, rows, taxes; returns totals for the screen.
   - `submit_receiving(cart, payment=None, client_request_id)` — submit PI; if payment given, `make_supplier_payment`; upsert changed Item Prices; return result. Idempotent.
   - `upsert_item_prices(item_code, prices_by_list)` — write only changed selling prices.
   - `make_supplier_payment(...)` — mirror `create_payment_entry` (Pay/Supplier).
3. **UI (Frappe page + Vue):**
   - Header: Supplier (with quick-create), Reference No, Date, Warehouse (default `Rupa - BO`), Company.
   - Item grid: search/scan add; columns qty, unit cost, discount %, tax, line total, **margin %**, **primary selling price**.
   - **Expandable per-line panel:** all Selling price lists with editable prices.
   - Optional payment block: Mode of Payment (from mapped MOPs), amount, **reference (required)**, date.
   - Save → `submit_receiving`.
4. **Verify** on test data: PI posts, stock moves (`Rupa - BO`), GL correct, Item Prices updated only where changed, Payment Entry posts to right account, PI status Paid/Partly Paid/Unpaid.

### Phase 2 — KRA validation module (inside Smart Receiving)
Built once the receiving core is solid. Uses the field maps we verified against live KRA endpoints.

- **`KRA Invoice Validation`** DocType (log): `cu_invoice_number`, `invoice_source` (TIMS/eTIMS, from format), `etims_data_token`, `status` (Pending/Fetched/Failed), `claimable` (Check), fetched fields (`supplier_name`, `supplier_pin` [eTIMS only], `buyer_name`, `buyer_pin`, `invoice_date`, `transmission_date`, `total_amount`, `taxable_amount`, `tax_amount`, `invoice_category`, `invoice_type`), `raw_response`, `supplier` (link, matched by PIN/name), `purchase_invoice` (link), `retry_count`, `last_retry`.
- **`KRA Validation Settings`** (single): company PIN (`P052216114Z`), retry on/off, retry age-out (default 30 days).
- **Two fetch functions:**
  - TIMS (19-digit) → POST `itax.kra.go.ke/.../fetchInvoiceDtl` → JSON.
  - eTIMS (`KRACU…`) → build `Data` token (supplier PIN + branch + receipt signature, from QR) → GET `etims.kra.go.ke/common/link/etims/receipt/...` → parse HTML.
- **Claimability:** `buyer_pin == company PIN`.
- **Pending → nightly retry** for both types, up to 30 days, then flag for manual handling. Polite spacing between calls; graceful Pending on failure.
- **On the receiving screen:** CU number field + "Validate with KRA" button (TIMS text or eTIMS QR scan); result stored + linked to the PI; `claimable` shown.

### Phase 3 — Reporting & delivery
- Customizable report: confirmed vs unconfirmed KRA invoices, receivings by period, margins, etc.
- Delivery: scheduled **email** (native Auto Email Report) and/or push to a **channel** (Antony to specify: WhatsApp/Telegram/Slack).

---

## 6. Key ERPNext facts to respect (from Bevali handover)
- Company `BEVALI ONLINE` (`BO`); warehouses `Rupa - BO` (receiving/source), `Zion Mall - BO` (selling).
- Primary selling price list: `Zion Retail Price`.
- VAT via `Purchase VAT 16% - BO` / item tax templates `V/E/Z - BO`; tax category `Purchase` on suppliers.
- Company KRA PIN: `P052216114Z`.
- Item codes are numeric with **significant leading zeros** — never coerce to int.
- Frappe `safe_exec` sandbox blocks `.format()`, nested-scope functions, `FORMAT` attribute — not relevant to app code (only server scripts), but noted.
- Always test on the bench; PI must be verified against Stock Ledger **and** GL, not just the document view.

---

## 7. Resolved decisions (were open — now confirmed)
1. **Cost source** — screen **prefills each item's last purchase cost** (most recent purchase rate); operator can override. Core part of `get_item_receiving_context`. **(Important.)**
2. **Supplier** — picked from existing ERPNext Supplier list. **No quick-create in v1** (possible future feature).
3. **Warehouse** — defaults to `Rupa - BO`, with a **dropdown to select any warehouse** to receive into.
4. **UI stack** — **full Vue SPA page**, like posawesome's `posapp`.
5. **Discount + additional expenses (landed cost)** — **included, not mandatory**; additional expenses post to a **selectable expense account**.

## 8. Document lifecycle (draft / submit / cancel / amend)
The underlying **Purchase Invoice is a native submittable ERPNext document**, so we map onto its lifecycle rather than reinventing it.

- **Save / Save as Draft** (screen) → create/update a **draft PI** (`docstatus=0`). Nothing posts to stock or GL. Editable, resumable. After saving a draft, the **screen stays open on that draft** for continued editing; a **Return** button navigates to a **list of draft receivings** to resume later.
- **Submit** (screen) → submit the PI (`docstatus=1`): stock moves, GL posts, and if a payment was entered, the **Payment Entry** is created + submitted here (idempotent).
- **Cancel / Amend** → done on the **native Purchase Invoice form** in Desk (safer, native linked-document checks). Submitted receivings show an **"Open in ERPNext"** link. In-screen cancel/amend deferred to a later version.

Notes:
- Draft PIs with `update_stock=1` do **not** move stock until submitted — drafts are safe, and don't affect stock or KRA claims.
- Draft receivings **do** consume PINV numbering (expected).
- v1 therefore includes a lightweight **"Draft Receivings" landing list**.

---

*End of spec v0.2 — decisions resolved, ready for Phase 1 build sheet.*
