#!/usr/bin/env bash
set -e

BACKEND="erpnext-v15-clean-backend-1"
FRONTEND="erpnext-v15-clean-frontend-1"
REDIS="erpnext-v15-clean-redis-1"
DB="erpnext-v15-clean-db-1"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================="
echo "  Booting Smart Receiving Local Docker Environment"
echo "=================================================="

echo -e "\n1. Starting Docker Containers..."
docker start $DB $REDIS $BACKEND $FRONTEND

echo -e "\n2. Syncing Local Repo Files to Container..."
docker cp ./smart_receiving $BACKEND:/home/frappe/frappe-bench/apps/smart_receiving/
docker cp ./frontend $BACKEND:/home/frappe/frappe-bench/apps/smart_receiving/

echo -e "\n3. Building Frontend Vite Bundle..."
docker exec -w /home/frappe/frappe-bench/apps/smart_receiving/frontend $BACKEND yarn build
docker cp $BACKEND:/home/frappe/frappe-bench/apps/smart_receiving/smart_receiving/public/dist ./smart_receiving/public/ 2>/dev/null || true

echo -e "\n4. Deploying Assets to Shared Nginx Web Volume..."
docker exec -u 0 $BACKEND sh -c "
  if [ -L /home/frappe/frappe-bench/sites/assets ]; then
    rm -f /home/frappe/frappe-bench/sites/assets
  fi
  mkdir -p /home/frappe/frappe-bench/sites/assets/frappe \
           /home/frappe/frappe-bench/sites/assets/erpnext \
           /home/frappe/frappe-bench/sites/assets/hrms \
           /home/frappe/frappe-bench/sites/assets/posawesome \
           /home/frappe/frappe-bench/sites/assets/smart_receiving/page/smart_receiving \
           /home/frappe/frappe-bench/sites/assets/smart_receiving/js
  cp -rL /home/frappe/frappe-bench/apps/frappe/frappe/public/* /home/frappe/frappe-bench/sites/assets/frappe/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/erpnext/erpnext/public/* /home/frappe/frappe-bench/sites/assets/erpnext/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/hrms/hrms/public/* /home/frappe/frappe-bench/sites/assets/hrms/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/posawesome/posawesome/public/* /home/frappe/frappe-bench/sites/assets/posawesome/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/smart_receiving/smart_receiving/public/* /home/frappe/frappe-bench/sites/assets/smart_receiving/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/smart_receiving/smart_receiving/page/* /home/frappe/frappe-bench/sites/assets/smart_receiving/page/ 2>/dev/null || true
  cp -rL /home/frappe/frappe-bench/apps/smart_receiving/smart_receiving/page/smart_receiving/smart_receiving.js /home/frappe/frappe-bench/sites/assets/smart_receiving/js/ 2>/dev/null || true
  find /home/frappe/frappe-bench/apps -name 'assets.json' -exec cp {} /home/frappe/frappe-bench/sites/assets/assets.json \; 2>/dev/null || true
  chown -R frappe:frappe /home/frappe/frappe-bench/sites/assets
  chmod -R 755 /home/frappe/frappe-bench/sites/assets
"

echo -e "\n5. Clearing Cache & Reloading Nginx..."
docker exec -w /home/frappe/frappe-bench/sites $BACKEND bench --site site1.localhost clear-cache
docker exec $FRONTEND nginx -s reload

echo -e "\n=================================================="
echo "  SUCCESS! Open in browser: http://localhost:8080/app/smart-receiving"
echo "=================================================="
