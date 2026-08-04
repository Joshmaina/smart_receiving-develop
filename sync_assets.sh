#!/usr/bin/env bash
set -e

BACKEND="erpnext-v15-clean-backend-1"
FRONTEND="erpnext-v15-clean-frontend-1"

echo "=================================================="
echo "  Smart Receiving Asset Dereferencing & Nginx Sync"
echo "=================================================="

# 1. Ensure frappe user owns backend assets
docker exec -u 0 $BACKEND chown -R frappe:frappe /home/frappe/frappe-bench/sites/assets 2>/dev/null || true

# 2. Extract dereferenced assets to temporary host folder
TMP_DIR=$(mktemp -d)
docker exec $BACKEND tar -C /home/frappe/frappe-bench/sites -chf - assets | tar -xf - -C "$TMP_DIR/"

# 3. Deploy dereferenced assets to Nginx web volume
docker exec -u 0 $FRONTEND sh -c "rm -rf /usr/share/nginx/html/sites/assets/*"
docker cp "$TMP_DIR/assets/." $FRONTEND:/usr/share/nginx/html/sites/assets/
rm -rf "$TMP_DIR"

# 4. Set Nginx permissions, clear cache, and reload Nginx
docker exec -u 0 $FRONTEND chmod -R 755 /usr/share/nginx/html/sites/assets 2>/dev/null || true
docker exec -w /home/frappe/frappe-bench/sites $BACKEND bench --site site1.localhost clear-cache 2>/dev/null || true
docker exec $FRONTEND nginx -s reload 2>/dev/null || true

echo "=================================================="
echo "  Assets synced and dereferenced successfully!"
echo "=================================================="
