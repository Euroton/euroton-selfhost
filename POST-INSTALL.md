# After the install

## Status: alpha

This is the first version. The server's suite passes 1,436 checks & a clean install has been rehearsed on Debian 13, but no server has moved mail to or from the internet yet, & no database has been carried across a real version upgrade. Keep backups, & don't make this your only copy of mail you can't lose.

These have to happen before it's called beta: a week of live mail through Postfix in both directions, an upgrade tested with real data, a tested restore from backup, services that don't run as root & the rest of the audit in [SECURITY.md](SECURITY.md). Godmode also still runs on a Vite dev server.

Sections marked **untested** have never handled real mail or a real certificate. The Postfix tasks install & start on Debian 13, & that's as far as testing went. Report what breaks.

## Outside mail (untested)

Both options below need a domain you control, DNS records & `postfix_enabled: true`. Set this before accounts exist, because addresses keep the suffix they got at sign-up:

```yaml
domain: example.org
postfix_enabled: true
mail_domain: example.org
mail_hostname: mail.example.org
```

Receiving always needs a public IP with inbound port 25 open, an MX record & the host reachable from the internet. Set `SIGNUP_ENABLED=false` first; see [INSTALL.md](INSTALL.md#after-the-install). [external-mail-setup.md](https://github.com/Euroton/euroton-server/blob/main/docs/external-mail-setup.md) has the MX, SPF, DKIM & DMARC records.

**Send from this host.** You also need outbound port 25, which many cloud providers & home connections block, & a reverse DNS record for your IP that matches `mail_hostname`. A new IP has no sending reputation, so expect large providers to put your first messages in spam.

**Send through a provider.** A relay provider such as MXroute solves the blocked port & the reputation problem. Check first that your plan allows relaying for your own domain, then add this to `group_vars/all.yml`:

```yaml
mail_relayhost: "[smtp.your-provider.example]:587"
mail_relay_user: "you@example.org"
mail_relay_password: "..."
```

Keep that file out of git. The provider has to accept the `bounces+<id>@<domain>` envelope sender too, or leave `mail_bounce_ingest_token` empty, which turns those senders off. Your SPF record also has to list the provider.

Run `playbook.yml`, then `systemctl restart euroton-server` if the run stopped partway, because a rerun doesn't restart it for a config file an earlier run already wrote. Check the records, send a test message & read its headers. Only then set `mail_outbound_backend: "postfix"` & run it again; until then nothing leaves the host.

## Let's Encrypt (untested)

The install uses its own CA, which every browser has to be told to trust. With a public domain you can swap in a Let's Encrypt certificate covering all 6 hostnames. Run this on the host, with DNS for each name pointing at it & port 80 reachable:

```sh
apt install certbot
certbot certonly --standalone \
  -d mail.example.org -d account.example.org -d calendar.example.org \
  -d mail-api.example.org -d account-api.example.org -d godmode.example.org \
  --deploy-hook 'install -m 640 -g caddy $RENEWED_LINEAGE/privkey.pem /etc/euroton/ssl/euroton.key; install -m 644 $RENEWED_LINEAGE/fullchain.pem /etc/euroton/ssl/euroton.crt; systemctl restart caddy'
```

Caddy listens on 443 only, so port 80 is free for certbot, & Debian's certbot package renews on a timer. Then set `ssl_external: true` in `group_vars/all.yml`, or the next playbook run puts the self-signed certificate back. The certificate is logged publicly, so the name `godmode.example.org` will be visible; Caddy still answers 403 to addresses outside `operator_allowed`.

## More system domains: not built

The server has one system domain, `LOCAL_MAIL_DOMAIN`, set from `domain` or `mail_domain`. `/core/v4/domains/available` returns that one plus the account's own verified custom domains, & the address routes reject any other suffix, so a second sign-up domain such as a short alias needs a code change. It can only ever work for domains you own, because mail for `pm.me` or `protonmail.ch` is routed by DNS those names' owner controls.

Custom domains per account do work, added in the account's settings. `REQUIRE_DOMAIN_DNS_VERIFY=true` makes them prove ownership with a TXT record; it's off by default, so turn it on if other people use your server.

## Give an account a plan

Open godmode, open the user, then find the subscription editor. Pick a plan & tick "Set PeriodEnd to 2099-01-01 and disable renew" for a lifetime plan. Payments aren't connected, so no money moves. The Plans page edits the catalog; its sample prices are placeholders, which you can change.

## Your own branding

Everything lives in `ansible/files/euroton-brand/` & `group_vars/all.yml`, so keep your own copy of this repo. Don't use anyone else's name or logo, Proton's included.

- **Colours:** `palette.yml`, which the playbook applies on every run. The red is also hard-coded in the `patches: swap` tasks in `playbook.yml`.
- **Logos:** `logos/<product>/<variant>.svg`. Keep the `viewBox` listed in `logos/manifest.yml`, or the deploy stops.
- **Links & credits:** `developer_name`, `developer_url`, `status_page_url` & `twitter_site`.
- **Server name:** `brand_name`, shown in authenticator apps & WebAuthn prompts.
- **Name in the apps:** `BRAND_NAME` at `packages/shared/lib/constants.ts:28` in your own fork of [WebClients](https://github.com/Euroton/WebClients), with `repo_webclients` & `version_webclients` pointing at it. Translations get their name from the 2 replace calls in `files/locale-brand-resync.py`.

Run `playbook.yml` after any change. A full rename hasn't been run end to end, so search the built apps for "Euroton" afterwards.

## Upgrades

There's no release channel yet; watch the [euroton-server](https://github.com/Euroton/euroton-server) tags. [Back up](https://github.com/Euroton/euroton-server/blob/main/docs/OPERATOR.md#backup) first, because migrations run at boot & don't reverse.

1. Change the `version_*` tags in `group_vars/all.yml`.
2. On the host, in each source tree under `/opt/euroton`, run `git fetch --tags --force && git checkout -f <tag>`.
3. Run `playbook.yml`.

The playbook restarts `euroton-server` when its git revision changes. It also rewrites `/etc/euroton/server.env`, so anything added by hand, such as `SIGNUP_ENABLED=false`, has to be added again. Client code changes mean a rebuild, about as long as the install.

## Docker: Postgres only

Only Postgres runs in Docker. The server, Godmode & Caddy are systemd units on Debian 13, & the clients are patched & built on the host, so there's no image to pull & no compose file for the whole stack. Debian 13 in a VM or an LXC container is what has been tested.

## Mobile apps: coming soon

There are no Euroton mobile apps yet. Versions that can point at a self-hosted server are coming, with no date & no promises. Proton's own apps talk to Proton's servers. The web apps haven't been tested on phones. `euroton-imap-bridge` is a skeleton that doesn't serve mail, so desktop mail clients can't connect either.

## Other things worth knowing

- **Backups:** Postgres, blobs & the data directory all have to come back together. [OPERATOR.md](https://github.com/Euroton/euroton-server/blob/main/docs/OPERATOR.md#backup) has the commands & a restore test.
- **Sign-up:** open until you set `SIGNUP_ENABLED=false`.
- **Calendar:** public links, subscriptions, holiday calendars & video conferencing return an error, because they have no backend here.
- **Drive, Pass, VPN & Wallet:** not supported in this version.
