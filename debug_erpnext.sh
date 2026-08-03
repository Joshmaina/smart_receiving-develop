#!/usr/bin/env bash
set -e

BACKEND="erpnext-v15-clean-backend-1"
FRONTEND="erpnext-v15-clean-frontend-1"

echo "=================================================="
echo "  ERPNext Container & Assets Diagnostic Health Check"
echo "=================================================="

echo -e "\n1. Checking Container Status..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "$BACKEND|$FRONTEND" || echo "Containers not running!"

echo -e "\n2. Cleaning Broken Symlinks & Rebuilding Physical Assets..."
docker exec -u 0 -it $BACKEND sh -c "
  rm -rf /home/frappe/frappe-bench/sites/assets
  mkdir -p /home/frappe/frappe-bench/sites/assets/frappe \
           /home/frappe/frappe-bench/sites/assets/erpnext \
           /home/frappe/frappe-bench/sites/assets/hrms \
           /home/frappe/frappe-bench/sites/assets/posawesome \
           /home/frappe/frappe-bench/sites/assets/smart_receiving

  cp -rL /home/frappe/frappe-bench/apps/frappe/frappe/public/* /home/frappe/frappe-bench/sites/assets/frappe/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/erpnext/erpnext/public/* /home/frappe/frappe-bench/sites/assets/erpnext/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/hrms/hrms/public/* /home/frappe/frappe-bench/sites/assets/hrms/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/posawesome/posawesome/public/* /home/frappe/frappe-bench/sites/assets/posawesome/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/smart_receiving/smart_receiving/public/* /home/frappe/frappe-bench/sites/assets/smart_receiving/ 2>/dev/null || true

  find /home/frappe/frappe-bench/apps -name 'assets.json' -exec cp {} /home/frappe/frappe-bench/sites/assets/assets.json \; 2>/dev/null || true

  chown -R frappe:frappe /home/frappe/frappe-bench/sites/assets
  chmod -R 755 /home/frappe/frappe-bench/sites/assets
"

echo -e "\n3. Checking Frontend Assets Directory (Nginx perspective)..."
docker exec -it $FRONTEND ls -la /usr/share/nginx/html/sites/assets/ || echo "Failed to read sites/assets on frontend"

echo -e "\n4. Checking Compiled JS/CSS Bundles & Media..."
docker exec -it $FRONTEND ls -la /usr/share/nginx/html/sites/assets/frappe/dist/css/ 2>/dev/null || echo "MISSING: frappe/dist/css"
docker exec -it $FRONTEND ls -la /usr/share/nginx/html/sites/assets/frappe/sounds/ 2>/dev/null || echo "MISSING: frappe/sounds"

echo -e "\n5. Reloading Nginx & Clearing Backend Cache..."
docker exec -u 0 -it $FRONTEND chmod -R 755 /usr/share/nginx/html/sites
docker exec $FRONTEND nginx -s reload
docker restart $BACKEND > /dev/null
sleep 4
docker exec -it -w /home/frappe/frappe-bench/sites $BACKEND bench --site site1.localhost clear-cache

echo -e "\n=================================================="
echo "SUCCESS! Hard refresh browser (Ctrl + Shift + R)."
echo "=================================================="
