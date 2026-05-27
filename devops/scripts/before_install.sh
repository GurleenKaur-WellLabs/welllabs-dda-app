#!/bin/bash
set -e
echo "=== BeforeInstall: Preparing for deployment ==="

# Create app directories if they don't exist (first deployment)
mkdir -p /opt/welllabs/{releases,shared,logs}

# Install system dependencies required by the deployment
apt-get update -qq
apt-get install -y -qq python3.12-venv libgdal-dev gdal-bin

echo "=== Ready for new release ==="
