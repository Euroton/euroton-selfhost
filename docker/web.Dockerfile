# Prebuilt clients behind Caddy. build-web-image.sh prepares the context from a
# tree the playbook has already patched & built; see README.md in this folder.
FROM caddy:2-alpine
RUN apk add --no-cache nodejs
COPY dist/ /srv/dist/
COPY baked-domain baked-srp-key.asc /srv/
COPY patch-web.mjs /srv/patch-web.mjs
COPY Caddyfile /etc/caddy/Caddyfile
COPY web-entrypoint.sh /usr/local/bin/web-entrypoint.sh
RUN chmod 755 /usr/local/bin/web-entrypoint.sh
VOLUME /srv/web
ENTRYPOINT ["/usr/local/bin/web-entrypoint.sh"]
