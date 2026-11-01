# Docker install

This install runs 3 containers: Postgres 17, the API & a Caddy image holding the built web clients. It skips the client build, the slow part of the Ansible install, which took 721 s on the test box. On that box the first web container start took 42 s & a restart of the whole stack took 15 s.

Docker covers local mail only. There's no Postfix in this stack, so mail between accounts on the server works & mail to or from the internet doesn't. Use the [Ansible install](../INSTALL.md) for outside mail.

## Images

`ghcr.io/euroton/euroton-server:0.2.0` is 638 MB & `ghcr.io/euroton/euroton-web:0.2.0` is 414 MB, source maps removed. Until those tags are on the registry, build them yourself & set `EUROTON_SERVER_IMAGE` & `EUROTON_WEB_IMAGE` in `.env`:

```sh
docker build -t euroton-server:local path/to/euroton-server
./build-web-image.sh path/to/WebClients path/to/euroton-godmode \
    path/to/srp-modulus-key.pub.asc euroton.internal euroton-web:local
```

`build-web-image.sh` packs clients the playbook already built. Its 3rd & 4th arguments are the SRP key & domain baked into those bundles.

## Start

Point `mail.`, `account.`, `calendar.`, `mail-api.`, `account-api.` & `godmode.` under your domain at the host, then:

```sh
./setup.sh example.internal
docker compose up -d
```

`setup.sh` writes `.env` once, with a generated database password & operator token. Don't delete that file: the database password in it is the one Postgres was created with.

The server creates its SRP keypair on first boot. The web container then copies the clients into a volume & swaps the baked domain & SRP key for yours, so every install keeps its own key without a rebuild.

## TLS

`EUROTON_TLS` defaults to `internal`, Caddy's own CA. Browsers won't trust it until you import the root, which you can copy out with:

```sh
docker compose cp web:/data/caddy/pki/authorities/local/root.crt euroton-root.crt
```

Set `EUROTON_TLS` in `.env` to an email address for Let's Encrypt on public hostnames.

## Admin UI

Godmode has a SQL console, so port 8443 binds to `127.0.0.1` only. `/admin` returns 404 on every public hostname. Reach it through a tunnel, with `godmode.<domain>` resolving to `127.0.0.1` on your machine:

```sh
ssh -L 8443:127.0.0.1:8443 you@host
```

Then open `https://godmode.<domain>:8443` & paste `OPERATOR_TOKEN` from `.env`.

## Upgrade & backup

Change the image tags, then run `docker compose pull && docker compose up -d`. Migrations run when the server starts.

Back up the `postgres-data` & `server-data` volumes together. `server-data` holds attachment blobs & the SRP private key; a database restored without that key can't log anyone in.
