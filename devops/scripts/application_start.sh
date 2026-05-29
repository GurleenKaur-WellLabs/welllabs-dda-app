#!/bin/bash
set -e

echo "=== ApplicationStart: Zero-downtime reload ==="

# Backend
echo "→ Reloading Gunicorn backend..."
if ! systemctl is-enabled --quiet welllabs-backend.service; then
    systemctl enable welllabs-backend.service
fi

systemctl reload welllabs-backend.service

sleep 5

if ! systemctl is-active --quiet welllabs-backend.service; then
    echo "ERROR: Backend failed to reload"
    journalctl -u welllabs-backend.service --no-pager -n 50
    exit 1
fi

echo "✓ Backend reload successful"

# Frontend
echo "→ Restarting frontend..."
if ! systemctl is-enabled --quiet welllabs-frontend.service; then
    systemctl enable welllabs-frontend.service
fi

systemctl restart welllabs-frontend.service

sleep 5

if ! systemctl is-active --quiet welllabs-frontend.service; then
    echo "ERROR: Frontend failed to start"
    journalctl -u welllabs-frontend.service --no-pager -n 50
    exit 1
fi

echo "✓ Frontend running"

# Nginx
echo "→ Reloading Nginx..."
nginx -t
systemctl reload nginx

echo "✓ Nginx reloaded"

echo "=== Deployment completed ==="