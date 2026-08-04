# Smart Receiving — Technical Summary & Problem Explainer

**Project:** Smart Receiving Custom App for ERPNext / Frappe v15  
**Client / Entity:** BEVALI ONLINE (`BO`) / Structured Data  
**Environment:** Local Docker Development Environment (`erpnext-v15-clean-...`)  
**Document Purpose:** Comprehensive technical breakdown of architectural design, empirical issues encountered, root-cause analyses, and implemented solutions.

---

## 1. Executive Overview & Architecture

**Smart Receiving** is a custom ERPNext/Frappe v15 application designed to provide a single-screen Goods Receiving interface (modelled on POS Awesome and UltimatePOS). 

### Core Architectural Principle
Smart Receiving does **not** invent custom stock or accounting ledgers. Instead, it acts as a streamlined user interface that produces **standard ERPNext documents**:
- **Purchase Invoice (`update_stock = 1`)**: Handles inventory quantity updates, valuation rates, line item taxes, discounts, and custom expenses (freight/handling).
- **Payment Entry (`payment_type = "Pay"`, `party_type = "Supplier"`)**: Handles supplier payments using mapped Modes of Payment (Cash/Bank accounts).
- **Item Price (`selling = 1`)**: Updates selling prices across multiple selling price lists (`Zion Retail Price`, etc.) at the moment of goods receipt.

```
┌─────────────────────────────────────────────────────────┐
│              Smart Receiving UI (Vue 3)                 │
│  - Supplier, bill_no, warehouse, MOP, reference         │
│  - Item grid: qty, rate, discount %, VAT, margin %      │
│  - Multi-price list expansion panel                     │
└────────────────────────────┬────────────────────────────┘
                             │ Whitelisted Frappe Server API
                             ▼
┌─────────────────────────────────────────────────────────┐
│               Python API (receiving.py)                 │
│  - build_purchase_invoice()   --> Draft Purchase Invoice│
│  - submit_receiving()         --> Submit Invoice + PE   │
│  - make_supplier_payment()    --> Payment Entry         │
│  - upsert_item_prices()       --> Item Price updates    │
│  - validate_kra_invoice()     --> KRA TIMS/eTIMS Log    │
└────────────────────────────┬────────────────────────────┘
                             │ Native ERPNext Engine
                             ▼
┌─────────────────────────────────────────────────────────┐
│                 Standard ERPNext Records                │
│  - Purchase Invoice (Stock + GL Ledger posted)          │
│  - Payment Entry (Pay / Supplier allocated)             │
│  - Item Price (Per Selling Price List)                  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Comprehensive Problem & Solution Breakdown

During development, deployment, and testing on the local Docker stack, several critical technical issues were identified and resolved. Below is an exhaustive breakdown of each problem, its empirical root cause, and the exact solution applied.

---

### Problem 1: Code Isolation Between Local Repository & Backend Container

#### Symptom
Edits made in the local repository workspace (`/home/joshuamainadev/Documents/Projects/smart_receiving-develop`) were not taking effect inside the running ERPNext application.

#### Root Cause Analysis
Docker inspection revealed that `erpnext-v15-clean-backend-1` did **not** use a live bind-mount for the app folder `/home/frappe/frappe-bench/apps/smart_receiving`. Instead, the container contained a static copy of the files from image creation. Consequently, local code changes remained isolated on the host system.

#### Solution
1. Configured direct workspace file synchronization via `docker cp` to copy local app files (`smart_receiving` & `frontend`) directly into `/home/frappe/frappe-bench/apps/smart_receiving/` inside the container.
2. Built the Vue 3 frontend bundle directly inside the container context (`yarn build`).
3. Extracted the compiled `dist` directory back to the local repository ([`smart_receiving/public/dist`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/smart_receiving/public/dist)) so local git tracking remains 100% aligned.

---

### Problem 2: Broken Nginx Volume Symlink & 404 Asset Errors

#### Symptom
Browser requests for static assets (`/assets/smart_receiving/dist/js/smart_receiving.js` and `.css`) returned `404 Not Found`, causing the page to fail rendering.

#### Root Cause Analysis
Docker volume inspection showed two different mount points:
- **Backend Container:** Mounted volume `erpnext-v15-clean_sites-data` to `/home/frappe/frappe-bench/sites`.
- **Frontend Container (Nginx):** Mounted volume `erpnext-v15-clean_sites-data` to `/usr/share/nginx/html/sites`.

Inside the Nginx container, `/usr/share/nginx/html/sites/assets` was a broken symbolic link (`assets -> /home/frappe/frappe-bench/assets`). Because `/home/frappe/frappe-bench/assets` did not exist on the frontend container's filesystem, Nginx failed to resolve the symlink target.

#### Solution
1. Replaced the broken symbolic link with a **physical directory** on the shared volume `erpnext-v15-clean_sites-data` at `/home/frappe/frappe-bench/sites/assets/smart_receiving`.
2. Updated asset deployment logic to copy compiled JS/CSS bundles directly into the physical directory on the shared volume.
3. Reloaded Nginx (`nginx -s reload`). HTTP checks (`curl -I`) confirmed **HTTP 200 OK** responses for all assets.

---

### Problem 3: Blank Page Display Due to Page Wrapper JS 404

#### Symptom
Even after JS and CSS bundles returned HTTP 200 OK, navigating to `http://localhost:8080/app/smart-receiving` rendered a completely blank workspace.

#### Root Cause Analysis
Frappe Desk pages load a wrapper script (`smart_receiving.js`) when opening page routes. When navigating to `/app/smart-receiving`, Frappe requested:
- `/assets/smart_receiving/page/smart_receiving/smart_receiving.js`
- `/assets/smart_receiving/js/smart_receiving.js`

Because only `public/dist` was copied to the Nginx volume, the request for the page glue script returned **404 Not Found**. Frappe could not invoke `frappe.pages['smart-receiving'].on_page_load`, leaving the DOM wrapper empty.

#### Solution
1. Synced the page wrapper script ([`smart_receiving.js`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/smart_receiving/page/smart_receiving/smart_receiving.js)) into Nginx volume paths `/assets/smart_receiving/page/smart_receiving/` and `/assets/smart_receiving/js/`.
2. Updated [`debug_erpnext.sh`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/debug_erpnext.sh) to copy both `page/` and `public/` assets on all rebuilds.
3. Confirmed via `curl -I` that both Page JS endpoints return **HTTP 200 OK**.

---

### Problem 4: Asynchronous ES Module Loading vs Synchronous Frappe Page Boot

#### Symptom
Intermittent blank page on initial load when the module script loaded asynchronously after Frappe page lifecycle events executed.

#### Root Cause Analysis
Vite's default build configuration targeted ES Modules (`format: "es"`), loaded via `<script type="module">`. In browser environments, ES module evaluation is deferred. If Frappe's `script.onload` callback executed before the module registered `window.smart_receiving_mount`, the boot method failed silently.

#### Solution
1. Re-architected [`frontend/vite.config.js`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/frontend/vite.config.js) to compile a **self-executing IIFE bundle** (`format: "iife"`, `name: "SmartReceivingBundle"`).
2. Updated [`smart_receiving.js`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/smart_receiving/page/smart_receiving/smart_receiving.js) to mount immediately if `window.smart_receiving_mount` is present.

---

### Problem 5: Missing MariaDB Columns (`tabContact` & `tabAddress`)

#### Symptom
Backend API calls failed with database errors:
- `pymysql.err.OperationalError: (1054, "Unknown column 'tabContact.is_billing_contact' in 'WHERE'")`
- `pymysql.err.OperationalError: (1054, "Unknown column 'tabAddress.is_your_company_address' in 'WHERE'")`

#### Root Cause Analysis
The clean database instance lacked specific schema migrations that ERPNext / HRMS / POS Awesome expect on core party tables.

#### Solution
1. Ran `bench --site site1.localhost migrate` to update standard DocType schemas.
2. Explicitly patched missing columns `is_billing_contact` on `tabContact` and `is_your_company_address` on `tabAddress`.
3. Cleared site cache and restarted backend workers.

---

## 3. Full Integration Test Suite Verification

A comprehensive backend test suite was executed against `site1.localhost` to verify all end-to-end capabilities:

| Test ID | Module / Feature | Verification Target | Status |
| :--- | :--- | :--- | :--- |
| **TEST 1** | `search_items` | Barcode/code/name search for item `0004` | **PASSED** |
| **TEST 2** | `get_item_receiving_context` | Prefetch cost, stock, selling price lists | **PASSED** |
| **TEST 3** | `build_purchase_invoice` | Draft PI `ACC-PINV-2026-0003` + Item Price `300.0` | **PASSED** |
| **TEST 4** | `list_draft_receivings` | List & reload draft cart state | **PASSED** |
| **TEST 5** | `submit_receiving` | Submit PI `ACC-PINV-2026-0004` | **PASSED** |
| **TEST 6** | `make_supplier_payment` | Payment Entry `ACC-PAY-2026-0002` (Paid status) | **PASSED** |
| **TEST 7** | Ledger Verification | Stock Ledger (+5.0 in `Rupa - BO`), Item Price (`300.0`) | **PASSED** |

---

## 4. One-Click Container Lifecycle Script ([`boot_docker.sh`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/boot_docker.sh))

To ensure effortless startup whenever you shut down or reboot your environment, a automated startup script was created in your project root:

```bash
./boot_docker.sh
```

### Automated Steps Performed by [`boot_docker.sh`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/boot_docker.sh):
1. **Container Startup:** Starts `erpnext-v15-clean-db-1`, `redis-1`, `backend-1`, and `frontend-1`.
2. **Code Synchronization:** Copies latest local repo code (`smart_receiving` & `frontend`) to backend container.
3. **Frontend Compilation:** Runs `yarn build` inside container to produce updated IIFE assets.
4. **Asset Web Volume Deployment:** Copies compiled CSS, JS, and Page loader scripts to shared Nginx volume.
5. **Cache & Server Refresh:** Clears site cache and reloads Nginx.

---

## 5. Quick Access Links & Commands

- **Local Web App:** `http://localhost:8080/app/smart-receiving`
- **Boot Script:** [`./boot_docker.sh`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/boot_docker.sh)
- **Diagnostic Script:** [`./debug_erpnext.sh`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/debug_erpnext.sh)
- **Backend API:** [`smart_receiving/api/receiving.py`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/smart_receiving/api/receiving.py)
- **Frontend App:** [`frontend/src/App.vue`](file:///home/joshuamainadev/Documents/Projects/smart_receiving-develop/frontend/src/App.vue)
