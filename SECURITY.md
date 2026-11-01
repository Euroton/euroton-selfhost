# Security

Report vulnerabilities through a private GitHub security advisory on the affected repo.

## What has been reviewed

Before the first release, a partial source-only audit produced 46 candidates: 42 unconfirmed leads & 4 rejected. 3 rounds of independent review then found 8 more defects, all fixed. The leads weren't each proven by a live exploit, so they carry no severity. The server's end-to-end suite runs 1,464 checks. `pnpm audit --prod` reports no known advisories for the server or Godmode.

## Open items

- The server itself still connects as the Postgres bootstrap superuser, so SQL injection in the server would reach shell commands in the database container. The SQL console doesn't: it connects as `euroton_console`, which has every table & no superuser rights.
- Sign-up is open by default. `SIGNUP_ENABLED=false` closes it.
- Postfix is off by default & has never moved a real message. A recipient can forge one false bounce notice for their own copy of a message.

## What nobody has reviewed yet

Rendering of inbound HTML mail by the client's sanitizer, secrets at rest, account & address deletion, the WebClients dependency tree, payments modules, and the Sieve, vCard & import parsers.

`pnpm run test:routes` calls every route with no credentials: 455 of 542 refuse, & the other 87 are login, sign-up, public keys, token links & fixed stubs. Check 314 in the suite calls all 166 routes with a parameter as a second user, with ids from 12 of the owner's tables, & fails on any success outside its list. That catches a route that ignores ownership on an id in the path, not ids in a body or query string. Session forks were read by hand: selectors are single-use, expire, die with the parent & don't inherit the unlock window.

Caddy's admin deny rules passed probes for encoded, repeated-slash, dot-segment & mixed-case paths on one Caddy version, using the real token. Re-run that after upgrading Caddy.
