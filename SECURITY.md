# Security

Report vulnerabilities through a private GitHub security advisory on the affected repo.

## What has been reviewed

Before the first release, a partial source-only audit produced 46 candidates: 42 unconfirmed leads & 4 rejected. 3 rounds of independent review then found 8 more defects, all fixed. The leads weren't each proven by a live exploit, so they carry no severity. The server's end-to-end suite runs 1,436 checks.

## Open items

- The SQL console runs as the Postgres bootstrap superuser, so `OPERATOR_TOKEN` can run shell commands in the database container with `COPY ... PROGRAM`.
- A logged-in session can change credentials without re-entering the password, and bridge sessions hold full scope.
- Sign-up is open by default. `SIGNUP_ENABLED=false` closes it.
- Services run as root.
- 4 mail paths need work before Postfix goes on: forged bounce notices through the bounce pipe, forwarding loops with no hop limit, multi-address `From` headers against DMARC, & DMARC alignment based on the last 2 domain labels. Postfix is off by default.

## What nobody has reviewed yet

Session fork selectors, rendering of inbound HTML mail, a route-by-route check of authentication, recovery email change, capability tokens, secrets at rest, account & address deletion, the dependency supply chain, payments modules, the Sieve, vCard & import parsers, state-changing GET routes, and LMTP limits.

Caddy's admin deny rules passed probes for encoded, repeated-slash, dot-segment & mixed-case paths on one Caddy version, using the real token. Re-run that after upgrading Caddy.
