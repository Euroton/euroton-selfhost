#!/bin/sh
# The server creates the SRP keypair on first boot; wait for its public half.
set -eu
KEY=/srv/server-data/srp-modulus-key.pub.asc
i=0
until [ -s "$KEY" ]; do
    i=$((i + 1))
    [ "$i" -le 120 ] || { echo "no SRP key at $KEY after 120 s" >&2; exit 1; }
    sleep 1
done
node /srv/patch-web.mjs /srv/dist /srv/web "$(cat /srv/baked-domain)" "$EUROTON_DOMAIN" /srv/baked-srp-key.asc "$KEY"
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
