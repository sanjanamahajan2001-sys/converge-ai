#!/usr/bin/env bash
set -e

echo '=== 1. Building Frontend Dist ==='
cd /home/sanjana/converge-ai/frontend
npm run build

echo '=== 2. Syncing Backend Files ==='
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='tests' --exclude='.env*'   -e 'ssh -i /home/sanjana/.ssh/linode_prod' /home/sanjana/converge-ai/backend/ root@192.46.210.48:/opt/apps/converge-ai/backend/

echo '=== 3. Syncing Frontend Dist ==='
rsync -avz --delete   -e 'ssh -i /home/sanjana/.ssh/linode_prod' /home/sanjana/converge-ai/frontend/dist/ root@192.46.210.48:/opt/apps/converge-ai/frontend/dist/

echo '=== 4. Remote Migration, Permissions & Service Restart ==='
ssh -i /home/sanjana/.ssh/linode_prod root@192.46.210.48 bash << 'REMOTE_EOF'
set -e
chmod -R 755 /opt/apps/converge-ai/frontend/dist
chown -R www-data:www-data /opt/apps/converge-ai/frontend/dist
mkdir -p /opt/apps/converge-ai/uploads/brochures
chown -R converge-ai:converge-ai /opt/apps/converge-ai/uploads
chmod -R 775 /opt/apps/converge-ai/uploads
if ! grep -q "ReadWritePaths=/opt/apps/converge-ai/uploads" /etc/systemd/system/converge-ai.service; then
  sed -i '/PrivateTmp=true/a ReadWritePaths=/opt/apps/converge-ai/uploads' /etc/systemd/system/converge-ai.service
  systemctl daemon-reload
fi
cd /opt/apps/converge-ai/backend
set -a
. /opt/apps/converge-ai/.env.migration
set +a
.venv/bin/alembic upgrade head
systemctl restart converge-ai.service
nginx -t
systemctl reload nginx
REMOTE_EOF

echo '=== 5. Health Check ==='
sleep 4
curl -sk https://192.46.210.48/converge-api/v1/health/ready
echo ''
echo 'Deployment Complete!'
