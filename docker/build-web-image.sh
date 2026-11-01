#!/bin/sh
# Usage: build-web-image.sh <WebClients tree> <godmode tree> <SRP public key> <baked domain> <image tag>
# Run where the playbook built the clients. Source maps stay out: they're 2/3 of the size.
set -eu
TREE=$1 GODMODE=$2 KEY=$3 DOMAIN=$4 TAG=$5
HERE=$(cd "$(dirname "$0")" && pwd)
CTX=$(mktemp -d)
trap 'rm -rf "$CTX"' EXIT
for app in mail account calendar; do
    mkdir -p "$CTX/dist/$app"
    tar -C "$TREE/applications/$app/dist" --exclude='*.map' -cf - . | tar -C "$CTX/dist/$app" -xf -
done
mkdir -p "$CTX/dist/godmode"
tar -C "$GODMODE/dist" --exclude='*.map' -cf - . | tar -C "$CTX/dist/godmode" -xf -
cp "$KEY" "$CTX/baked-srp-key.asc"
printf '%s' "$DOMAIN" > "$CTX/baked-domain"
cp "$HERE/patch-web.mjs" "$HERE/Caddyfile" "$HERE/web-entrypoint.sh" "$CTX/"
docker build -f "$HERE/web.Dockerfile" -t "$TAG" "$CTX"
