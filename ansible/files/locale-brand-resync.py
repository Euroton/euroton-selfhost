#!/usr/bin/env python3
"""ADR 112 -- locale catalog brand-resync.

Walks JSON ttag catalogs under <mirror_dir>/applications/{mail, account,
calendar, pass, vpn-settings, wallet}/locales/*.json and replaces
literal "Proton" with "Euroton" in msgstr values only.

ADR 168 (H6) extends the APPS list from the original three (mail,
account, calendar) to also cover pass, vpn-settings, and wallet --
the discovery-mode apps ADR 126 deployed. The script's regex +
catalog-walk logic is unchanged; only the apps walked differ.

Preserved:

  - Top-level "contexts.<name>" keys (addressed by source code as
    c('<name>') and must match -- only `Onboarding Proton` and
    `familyOffer_2023:Onboarding Proton` currently qualify).
  - ${ ... } placeholder identifiers inside any string (resolved at
    runtime against source-code-defined bindings; renaming would break
    the lookup).

ADR 108's BRAND_NAME swap already covers every ttag template that uses
${BRAND_NAME} interpolation. This script handles the remaining cases:
non-English translators who inlined the literal brand into msgstr,
leaving "Proton Mail" / "Proton Drive" / etc. in the catalog even
though the source-code msgid uses the BRAND_NAME placeholder.

Idempotent: re-running on an already-resynced tree makes zero changes
and prints a 0/0 summary.

argv: <mirror_dir>
"""
import json
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r'\$\{[^}]*\}')

APPS = ['mail', 'account', 'calendar', 'pass', 'vpn-settings', 'wallet']


def replace_outside_placeholders(s: str) -> str:
    out = []
    last = 0
    for m in PLACEHOLDER_RE.finditer(s):
        out.append(s[last:m.start()].replace('Proton', 'Euroton'))
        out.append(m.group(0))
        last = m.end()
    out.append(s[last:].replace('Proton', 'Euroton'))
    return ''.join(out)


def resync_catalog(catalog: dict) -> int:
    n = 0
    contexts = catalog.get('contexts')
    if not isinstance(contexts, dict):
        return 0
    for _ctx_name, msgs in contexts.items():
        if not isinstance(msgs, dict):
            continue
        for _msgid, msgstrs in msgs.items():
            if not isinstance(msgstrs, list):
                continue
            for i, s in enumerate(msgstrs):
                if not isinstance(s, str) or 'Proton' not in s:
                    continue
                new = replace_outside_placeholders(s)
                if new != s:
                    msgstrs[i] = new
                    n += 1
    return n


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: locale-brand-resync.py <mirror_dir>', file=sys.stderr)
        return 2
    mirror = Path(sys.argv[1])
    total_files = 0
    total_changes = 0
    for app in APPS:
        loc_dir = mirror / 'applications' / app / 'locales'
        if not loc_dir.is_dir():
            continue
        for path in sorted(loc_dir.glob('*.json')):
            text = path.read_text(encoding='utf-8')
            catalog = json.loads(text)
            n = resync_catalog(catalog)
            if n == 0:
                continue
            new_text = json.dumps(catalog, ensure_ascii=False, indent=2)
            if new_text != text:
                path.write_text(new_text, encoding='utf-8')
                total_files += 1
                total_changes += n
    print(f'locale-brand-resync: {total_changes} msgstr substitutions across {total_files} files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
