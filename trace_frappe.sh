#!/usr/bin/env bash
set -e

BACKEND="erpnext-v15-clean-backend-1"
FRONTEND="erpnext-v15-clean-frontend-1"

echo "=================================================="
echo "  Frappe Python & Asset Resolution Tracer"
echo "=================================================="

echo -e "\n1. Checking '/sites/assets' Type on Backend:"
docker exec -it $BACKEND ls -ld /home/frappe/frappe-bench/sites/assets

echo -e "\n2. Checking 'assets.json' File Existence on Backend:"
docker exec -it $BACKEND ls -la /home/frappe/frappe-bench/sites/assets/assets.json 2>/dev/null || echo "NOT FOUND: /sites/assets/assets.json"
docker exec -it $BACKEND ls -la /home/frappe/frappe-bench/sites/assets.json 2>/dev/null || echo "NOT FOUND: /sites/assets.json"

echo -e "\n3. Testing Frappe Python Internal Asset Resolver:"
docker exec -it -w /home/frappe/frappe-bench/sites $BACKEND python3 -c "
import frappe
frappe.init(site='site1.localhost')
frappe.connect()

print('\n--- Python Path & Asset Check ---')
print('frappe.get_site_path():', frappe.get_site_path())
print('frappe.get_site_path(\"assets\"):', frappe.get_site_path('assets'))
print('frappe.get_site_path(\"assets\", \"assets.json\"):', frappe.get_site_path('assets', 'assets.json'))

import os
target = frappe.get_site_path('assets', 'assets.json')
print('Does target exist via os.path.exists?:', os.path.exists(target))
print('Is target a symlink?:', os.path.islink(target))

try:
    from frappe.utils.jinja_globals import get_assets_json
    print('get_assets_json() output:', get_assets_json())
except Exception as e:
    print('Error calling get_assets_json():', e)
"

echo -e "\n4. Checking Nginx Mounted Filesystem Perspective:"
docker exec -it $FRONTEND ls -ld /usr/share/nginx/html/sites/assets

echo "=================================================="
