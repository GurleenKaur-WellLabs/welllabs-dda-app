#!/bin/bash
set -e
echo "=== BeforeInstall: Preparing for deployment ==="

# Create app directories if they don't exist (first deployment)
mkdir -p /opt/welllabs/{releases,shared,logs}

# Install python3.12-venv so `python3 -m venv` works on this instance
apt-get install -y -qq python3.12-venv

echo "=== Ready for new release ==="
