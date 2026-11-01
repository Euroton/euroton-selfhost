#!/bin/sh
# Usage: ./setup.sh <domain>. Writes .env once, with secrets generated here.
set -eu
[ $# -eq 1 ] || { echo "usage: $0 <domain>" >&2; exit 2; }
[ ! -e .env ] || { echo ".env exists; delete it only if you mean to lose access to the database" >&2; exit 1; }
umask 077
cat > .env <<ENV
EUROTON_DOMAIN=$1
POSTGRES_PASSWORD=$(openssl rand -hex 24)
OPERATOR_TOKEN=$(openssl rand -hex 32)
ENV
echo "wrote .env; next: docker compose up -d"
