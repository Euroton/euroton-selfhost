# Ansible playbooks

Two playbooks. `provision.yml` turns bare Debian 13 into a host with Node, Docker, Postgres & the source trees. `playbook.yml` builds the clients and starts the services. [INSTALL.md](../INSTALL.md) has the commands in order; this file explains what they do & how to run the server afterwards.

## What gets installed

`provision.yml` installs the apt packages, a checksummed Node tarball & Corepack, clones `WebClients`, `euroton-server` & `euroton-godmode` at the tags pinned in `group_vars/all.yml`, writes a generated Postgres password to `euroton-server/.env` and starts Postgres on `127.0.0.1:54320`.

`playbook.yml` then does this, in order:

1. Installs Caddy.
2. Generates a CA & leaf certificate on your control machine in `files/ssl/`, and copies the leaf & the CA certificate to `/etc/euroton/ssl/`. The CA private key stays on your machine.
3. Installs dependencies, then generates the install's SRP modulus keypair & writes the public half into `node_modules/@protontech/crypto/src/srp/constants.ts`. The upstream client only accepts modulus signatures from the key it was built with, so this has to happen before the build (ADR 004).
4. Applies the Euroton palette, logos & locale names, then builds Mail, Account & Calendar as static files.
5. Writes `/etc/euroton/server.env` & the systemd units, starts `euroton-server` & `godmode-dev`, writes the Caddyfile, and checks every hostname answers.

Re-running is safe. Secrets in `files/secrets/` & the SRP keypair stay as they are, and a client rebuilds only when its inputs changed.

## Hostnames

Everything comes from one variable, `domain`, default `euroton.internal`. ICANN reserved `.internal` for private use, so these names never resolve publicly. The playbook serves `mail.`, `account.`, `calendar.`, `mail-api.`, `account-api.` & `godmode.` under it. Point those at the host in `/etc/hosts` or your LAN's DNS.

Signup addresses use the same domain, so changing it after accounts exist leaves those accounts on the old suffix.

## Trusting the CA

Browsers warn on every hostname until you trust `files/ssl/euroton-ca.crt`. Firefox has its own store: Settings, Privacy & Security, Certificates, View Certificates, Authorities, Import. Chromium on Linux uses NSS:

```sh
certutil -d sql:$HOME/.pki/nssdb -A -t "CT,," -n euroton-ca -i files/ssl/euroton-ca.crt
```

The API hostnames need trusting too. If you click through warnings instead of installing the CA, sign-up fails, because its hidden frames load from `account-api.<domain>` and browsers don't show a warning for a frame.

## Running the services

```sh
journalctl -fu euroton-server
journalctl -fu godmode-dev
systemctl status caddy euroton-server godmode-dev
systemctl restart euroton-server
```

Logs also go to `/var/log/euroton/`. Units restart 3 seconds after a crash and start at boot; Postgres comes back through its Docker restart policy.

To upgrade, change the `version_*` tags in `group_vars/all.yml`, then on the host run `git fetch --tags --force && git checkout -f <tag>` in each source tree, and re-run `playbook.yml`. The `-f` is needed because the playbook patches the WebClients tree in place, leaving 107 modified files that a plain checkout refuses to overwrite. A rebuild took 13 min 32 s in testing.

## Godmode

`godmode.<domain>` is the admin UI, with the token in `files/secrets/operator_token`. Caddy answers 403 to any address outside `operator_allowed`, default `private_ranges`, and it's the only hostname that routes `/admin/*` to the server. Every other hostname returns 404 or the static app page for those paths, and the server binds `127.0.0.1`.

The console can read every row in the database, so **don't widen `operator_allowed` to the internet**. If a reverse proxy sits in front of this host, every request arrives from a private address and the check passes for everyone; in that setup, block the godmode hostname at the proxy.

To rotate the token, delete `files/secrets/operator_token` & re-run the playbook. Each browser then asks for the new one.

## Outside mail

Off by default & untested. `postfix_enabled: true` installs Postfix, spamd & postgrey, which installed & started on Debian 13 in a rehearsal, but no real message has gone through it. It needs a public IP, inbound port 25, real DNS & a `domain` other than `.internal`, because remote servers reject that suffix. `euroton-server/docs/external-mail-setup.md` lists the DNS records.

[POST-INSTALL.md](../POST-INSTALL.md) has the steps, including a relay provider. `mail_outbound_backend` stays `none` until inbound is verified. Setting it to `postfix` releases the queue.

## Known limits

- The playbook manages no firewall. Only ports 22 & 443 listen on public interfaces after an install, and 5355 if `systemd-resolved` has LLMNR on.
- Pass, VPN & Wallet aren't built, because they 404-loop on most actions. Drive needs a private upstream package.
