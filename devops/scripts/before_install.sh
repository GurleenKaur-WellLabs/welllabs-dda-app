#!/bin/bash
set -e
echo "=== BeforeInstall: Preparing for deployment ==="

# Create app directories if they don't exist (first deployment)
mkdir -p /opt/welllabs/{releases,shared,logs}

# Clean up any previous deploy staging directory so CodeDeploy can
# copy the new revision cleanly during the Install phase.
rm -rf /tmp/welllabs-deploy
mkdir -p /tmp/welllabs-deploy

echo "=== Ready for new release ==="
