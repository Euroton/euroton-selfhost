# euroton-selfhost

Ansible playbooks that take a bare Debian 13 host to a running Euroton server: Node 22, Docker, Postgres, Caddy, the API, the admin UI & production builds of the Mail, Account & Calendar clients.

[INSTALL.md](INSTALL.md) has every command, & [POST-INSTALL.md](POST-INSTALL.md) covers what comes after it. `ansible/README.md` covers what the playbooks do & how to run the server afterwards.

## Limits

Local mail only. Accounts on one server can mail each other, with end-to-end encryption intact; the Postfix path for outside mail has only been syntax-checked (ADR 232 in `euroton-server`), so it's off by default.

TLS is self-signed unless you bring your own certificates. Your browser needs the generated CA installed; clicking through the warning breaks sign-up.

Help, legal & some upgrade links in the clients still point to `proton.me`, inherited from upstream: 13 distinct URLs in the Mail & Calendar builds, 61 in Account. Those pages describe Proton's service, not your server.

The server & Godmode run as the `euroton` system user, which can write only `data/` & its logs.

## Licence

GPL-3.0-or-later. See `LICENSE` & `NOTICE`. The client fork at [Euroton/WebClients](https://github.com/Euroton/WebClients) inherits GPL-3.0 from Proton AG's upstream.
