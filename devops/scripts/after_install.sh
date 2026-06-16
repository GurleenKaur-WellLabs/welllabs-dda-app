#!/bin/bash
set -e

echo ""
echo "============================================================"
echo " AfterInstall started : $(date)"
echo "============================================================"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RELEASE_DIR="/opt/welllabs/releases/$TIMESTAMP"
SHARED_DIR="/opt/welllabs/shared"
SHARED_ENV="${SHARED_DIR}/.env"

# Derive the deployment archive root from this script's own location:
# Script is at <archive>/devops/scripts/after_install.sh  →  go up 2 levels.
DEPLOY_ARCHIVE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Normalize all deployment scripts to Unix (LF) line endings (safety for Windows checkouts)
find "${DEPLOY_ARCHIVE}/devops/scripts" -type f -name "*.sh" -exec sed -i 's/\r$//' {} +

# ──────────────────────────────────────────────────────────────────────────────
# [1/7] Read deploy-env from build artifact  →  gets the secret ARN
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "--- [1/7] Reading deploy-env from artifact ---"

[[ -f "${DEPLOY_ARCHIVE}/deploy-env" ]] || {
  echo "ERROR: deploy-env not found in ${DEPLOY_ARCHIVE}."
  echo "Check: buildspec.yml post_build step writes this file."
  exit 1
}

# Strip leading whitespace (heredoc indentation written by buildspec cat <<EOF)
sed -i 's/^[[:space:]]*//' "${DEPLOY_ARCHIVE}/deploy-env"

source "${DEPLOY_ARCHIVE}/deploy-env"

for var in PROJECT_NAME APP_CONFIG_SECRET_ARN; do
  [[ -n "${!var:-}" ]] || {
    echo "ERROR: '${var}' is missing or empty in deploy-env."
    echo "Check: Terraform pipeline module injects APP_CONFIG_SECRET_ARN and PROJECT_NAME."
    exit 1
  }
done

echo "Project        : ${PROJECT_NAME}"
echo "App Config ARN : ${APP_CONFIG_SECRET_ARN}"

# ──────────────────────────────────────────────────────────────────────────────
# [2/7] Fetch the app-config secret from Secrets Manager
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "--- [2/7] Fetching secret from AWS Secrets Manager ---"

APP_CONFIG_JSON=$(aws secretsmanager get-secret-value \
  --secret-id "${APP_CONFIG_SECRET_ARN}" \
  --query SecretString \
  --output text 2>&1) || {
  echo "ERROR: Failed to fetch secret '${APP_CONFIG_SECRET_ARN}'."
  echo "Check: EC2 IAM role has secretsmanager:GetSecretValue on this ARN."
  echo "Run:   aws sts get-caller-identity   (to confirm role is attached)"
  exit 1
}

# ──────────────────────────────────────────────────────────────────────────────
# [3/7] Validate JSON
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "--- [3/7] Validating secret JSON ---"

jq -e . > /dev/null 2>&1 <<< "${APP_CONFIG_JSON}" || {
  echo "ERROR: Secret value is not valid JSON."
  echo "Check: Add secret values as JSON in AWS Console → Secrets Manager."
  exit 1
}

echo "Keys in secret : $(jq -r 'keys | join(", ")' <<< "${APP_CONFIG_JSON}")"

# ──────────────────────────────────────────────────────────────────────────────
# [4/7] Validate critical required fields  (Django / PostgreSQL keys)
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "--- [4/7] Validating required fields ---"

# These are the exact keys Django settings.py reads via django-environ
REQUIRED_FIELDS=("DB_NAME" "DB_USER" "DB_PASSWORD" "DB_HOST" "DB_PORT" "SECRET_KEY" "ALLOWED_HOSTS")

for field in "${REQUIRED_FIELDS[@]}"; do
  VALUE=$(jq -r ".${field} // empty" <<< "${APP_CONFIG_JSON}")
  [[ -n "${VALUE}" ]] || {
    echo "ERROR: Required field '${field}' is missing or empty in Secrets Manager."
    echo "Fix:   AWS Console → Secrets Manager → ${APP_CONFIG_SECRET_ARN} → Edit secret value"
    echo "       Add key: ${field}"
    exit 1
  }
  echo "  ✓ ${field} is present"
done

# ──────────────────────────────────────────────────────────────────────────────
# [5/7] Write /opt/welllabs/shared/.env  (all keys from JSON, dynamically)
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "--- [5/7] Writing ${SHARED_ENV} ---"

mkdir -p "${SHARED_DIR}"

# Generate .env from every key in the JSON — no hardcoded key list needed
jq -r 'to_entries | .[] | "\(.key)=\(.value)"' <<< "${APP_CONFIG_JSON}" > "${SHARED_ENV}"

# Secure: only root can read it
chmod 600 "${SHARED_ENV}"
chown root:root "${SHARED_ENV}"

echo ".env written  : ${SHARED_ENV}"
echo "─────────────────────────────────────────────────────────────"
# Log keys — mask values that look sensitive
while IFS='=' read -r key value; do
  if [[ "$key" =~ (SECRET|PASSWORD|TOKEN|KEY) ]]; then
    echo "  $key=[REDACTED, ${#value} chars]"
  else
    echo "  $key=$value"
  fi
done < "${SHARED_ENV}"
echo "─────────────────────────────────────────────────────────────"

# ──────────────────────────────────────────────────────────────────────────────
# [6/7] Build the new release
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "--- [6/7] Creating release $TIMESTAMP ---"
mkdir -p "$RELEASE_DIR"
cp -r "$DEPLOY_ARCHIVE/." "$RELEASE_DIR/"

# Symlink the shared .env into the release backend directory
ln -sf "${SHARED_ENV}" "${RELEASE_DIR}/backend/.env"
echo "  .env symlinked → ${RELEASE_DIR}/backend/.env"

# ──────────────────────────────────────────────────────────────────────────────
# Backend: Python virtual environment
# ──────────────────────────────────────────────────────────────────────────────
echo "Setting up Python virtual environment..."
cd "$RELEASE_DIR/backend"

PYTHON_BIN=$(command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3 || true)
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: No Python 3 interpreter found on this instance."
  exit 1
fi
echo "Using Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

"$PYTHON_BIN" -m venv venv
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip -q

# GDAL pip package must match the system libgdal version exactly
GDAL_SYS_VERSION=$(gdal-config --version)
echo "Installing GDAL==$GDAL_SYS_VERSION (matching system library)..."
pip install GDAL==$GDAL_SYS_VERSION -q

# Install remaining requirements (skip the GDAL line to avoid version conflict)
grep -iv "^gdal" requirements.txt | pip install -r /dev/stdin -q

# ──────────────────────────────────────────────────────────────────────────────
# Database setup & Django migrations
# ──────────────────────────────────────────────────────────────────────────────
# Read DB_PASSWORD from the freshly written .env
DB_PASS=$(grep ^DB_PASSWORD "${SHARED_ENV}" | cut -d= -f2 | tr -d '\r')
DB_NAME_VAL=$(grep ^DB_NAME "${SHARED_ENV}" | cut -d= -f2 | tr -d '\r')

echo "Configuring database user password..."
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '$DB_PASS';"

if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME_VAL}"; then
  echo "Database '${DB_NAME_VAL}' does not exist. Creating it now..."
  sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME_VAL};"
  sudo -u postgres psql -d "${DB_NAME_VAL}" -c "CREATE EXTENSION postgis;"
fi

echo "Running Django migrations & collectstatic..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput
python manage.py collectstatic --noinput

deactivate

# ──────────────────────────────────────────────────────────────────────────────
# Frontend: Node.js / SvelteKit build
# ──────────────────────────────────────────────────────────────────────────────
echo "Building SvelteKit frontend..."
cd "$RELEASE_DIR/frontend"

export PATH="/usr/local/bin:/usr/bin:$PATH"

NPM_BIN=$(command -v npm || true)
if [ -z "$NPM_BIN" ]; then
  echo "ERROR: npm not found. Ensure before_install.sh ran successfully."
  exit 1
fi
echo "Using npm: $NPM_BIN ($(npm --version)), Node: $(node --version)"

npm install --os=linux --cpu=x64

# Read EC2 IP and set VITE_API_URL for static env replacement during build
if [ -f "$DEPLOY_ARCHIVE/allowed_hosts.txt" ]; then
  EC2_IP=$(cat "$DEPLOY_ARCHIVE/allowed_hosts.txt" | tr -d '\r' | xargs)
  if [ -n "$EC2_IP" ]; then
    export VITE_API_URL="http://$EC2_IP"
    echo "Exported VITE_API_URL=$VITE_API_URL for frontend build"
  fi
fi

npm run build

──────────────────────────────────────────────────────────────────────────────
Nginx & systemd configs
──────────────────────────────────────────────────────────────────────────────
echo "Installing Nginx & systemd configs..."

cp /etc/nginx/conf.d/welllabs.conf /etc/nginx/conf.d/welllabs.conf.bak 2>/dev/null || true

cp "$RELEASE_DIR/devops/nginx/welllabs.conf" /etc/nginx/conf.d/welllabs.conf
rm -f /etc/nginx/conf.d/default.conf
rm -f /etc/nginx/sites-enabled/default

if ! nginx -t; then
  echo "ERROR: Nginx config invalid — restoring previous config..."
  mv /etc/nginx/conf.d/welllabs.conf.bak /etc/nginx/conf.d/welllabs.conf
  exit 1
fi
rm -f /etc/nginx/conf.d/welllabs.conf.bak

cp "$RELEASE_DIR/devops/systemd/welllabs-backend.service"  /etc/systemd/system/
cp "$RELEASE_DIR/devops/systemd/welllabs-frontend.service" /etc/systemd/system/
systemctl daemon-reload

# ──────────────────────────────────────────────────────────────────────────────
# [7/7] Atomic symlink swap to new release
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "--- [7/7] Swapping symlink to new release: $TIMESTAMP ---"
ln -sfn "$RELEASE_DIR" /opt/welllabs/current

# Cleanup: keep only last 3 releases
echo "Cleaning up old releases..."
cd /opt/welllabs/releases
ls -dt */ | tail -n +4 | xargs rm -rf 2>/dev/null || echo "Warning: cleanup had issues, continuing..."

echo ""
echo "============================================================"
echo " AfterInstall DONE : $(date)"
echo " Release : $TIMESTAMP"
echo "============================================================"
