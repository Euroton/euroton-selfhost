#!/usr/bin/env python3
# Inject Euroton-modified logo SVGs into upstream `<Product>Logo.tsx`.
#
# Invoked by the ansible playbook. Restructured by ADR 177 to drop
# the overlay/reference split — every SVG under
# `euroton-brand/logos/<product>/<variant>.svg` is editable artwork
# and gets injected as-is.
#
# Run with:
#
#   inject-logos.py --mirror /path/to/proton-webclients-mirror \
#       --logos-dir /path/to/euroton-brand/logos \
#       --manifest /path/to/euroton-brand/logos/manifest.yml
#
# Exit codes:
#   0 — success, with a JSON summary on stdout:
#       {"changed": bool, "applied": [...], "skipped": [...]}
#   2 — validation error (manifest mismatch, malformed SVG, etc.).
#   3 — flag / path error.
#
# Idempotent: re-running against an already-substituted .tsx
# reports `changed: false` via the
# `/* euroton-brand:inject begin/end */` markers. All on-container .tsx edits flow
# through this script; never hand-patch the mirror.

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        json.dumps({
            "error": "PyYAML not installed; ansible should "
                     "provide it via the python-yaml interpreter",
        }),
        file=sys.stderr,
    )
    sys.exit(3)


# Marker that wraps an injected variant body so we can detect
# already-applied substitutions on re-runs (idempotency).
MARKER_OPEN = "/* euroton-brand:inject begin */"
MARKER_CLOSE = "/* euroton-brand:inject end */"

# Tokens that betray JSX accidentally copied into authored SVG artwork
# — most commonly the closing `)}` of upstream's `{color === 'brand' &&
# (<defs>…</defs>)}` wrapper. The injector splices the SVG body verbatim
# into the *Logo.tsx, so such a token yields invalid JSX. The webpack
# dev-server loader only flags that as a dismissable overlay, but the
# production swc-loader (ADR 245) hard-fails ("Unexpected token }"), so
# the break stays invisible until a prod build. Reject at inject-time
# with a clear, actionable message instead. (Valid template-string fills
# like `fill={`url(#${uid}-a)`}` never produce a literal `)}` — the
# backtick sits between the `)` and the `}` — so this is false-positive
# safe for the rewritten body, and authored SVGs are pure SVG anyway.)
JSX_LEFTOVER_TOKENS = (")}", "&& (", "&&(")


def assert_no_jsx_leftovers(product: str, variant: str, body: str) -> None:
    """Raise ValueError if the SVG body carries stray JSX tokens."""
    found = [tok for tok in JSX_LEFTOVER_TOKENS if tok in body]
    if found:
        raise ValueError(
            f"{product}/{variant}: SVG body contains leftover JSX "
            f"token(s) {found} — looks like JSX (e.g. the closing of a "
            "{cond && (...)} wrapper) was copied into the artwork. "
            "Author the SVG as pure SVG; inject-logos.py adds the JSX "
            "framing itself."
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--mirror", required=True, type=Path)
    p.add_argument("--logos-dir", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    return p.parse_args()


def load_manifest(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def read_svg_body(svg_text: str) -> tuple[str, str]:
    """Return (viewBox, inner body) for the SVG.

    Inner body is everything inside the outer `<svg>...</svg>`.
    """
    m = re.search(
        r"<svg\b([^>]*)>([\s\S]*?)</svg>",
        svg_text,
        flags=re.IGNORECASE,
    )
    if not m:
        raise ValueError("no <svg> root element found")
    attrs = m.group(1)
    body = m.group(2).strip()
    vb_match = re.search(
        r'viewBox\s*=\s*"([^"]+)"',
        attrs,
    )
    if not vb_match:
        raise ValueError("missing viewBox attribute on <svg>")
    return vb_match.group(1).strip(), body


def rewrite_uid_refs(body: str) -> str:
    """Re-template `id="logo-X"` and `url(#logo-X)` to JSX form.

    Operators author overlay SVGs as if `${uid}` were the literal
    string `logo`. The substitution rewrites those back to JSX
    template-string interpolation so the per-render uid still
    namespaces gradient ids across multiple logo instances on the
    same page.
    """
    body = re.sub(
        r'id="logo-([A-Za-z0-9_]+)"',
        r'id={`${uid}-\1`}',
        body,
    )
    body = re.sub(
        r'fill="url\(#logo-([A-Za-z0-9_]+)\)"',
        r'fill={`url(#${uid}-\1)`}',
        body,
    )
    body = re.sub(
        r'stroke="url\(#logo-([A-Za-z0-9_]+)\)"',
        r'stroke={`url(#${uid}-\1)`}',
        body,
    )
    # SVG → JSX attribute renames.
    body = body.replace("stop-color=", "stopColor=")
    body = body.replace("fill-rule=", "fillRule=")
    body = body.replace("clip-rule=", "clipRule=")
    body = body.replace("xlink:href=", "xlinkHref=")
    return body


def build_replacement(tsx_variant: str, body: str) -> str:
    """Build the new `{variant === 'X' && (<>…</>)}` block."""
    return (
        f"{{variant === '{tsx_variant}' && (\n"
        "                <>\n"
        f"                    {MARKER_OPEN}\n"
        f"{body}\n"
        f"                    {MARKER_CLOSE}\n"
        "                </>\n"
        "            )}"
    )


def variant_block_re(tsx_variant: str) -> re.Pattern:
    """Default 6-product pattern: `{variant === 'X' && (<>…</>)}`."""
    return re.compile(
        r"\{variant === '" + re.escape(tsx_variant) +
        r"' && \(\s*<>([\s\S]*?)</>\s*\)\}",
    )


# ADR 184: ProtonLogo.tsx uses an if/else shape rather than the
# `{variant === 'X' && (<>…</>)}` pattern the other 6 product logos
# share. Two patterns cover its two branches:
#
#   with-wordmark — `if (variant === 'with-wordmark') { return
#                    (<LogoBase …>CHILDREN</LogoBase>); }`
#   glyph-only    — the trailing `return (<LogoBase …>CHILDREN
#                    </LogoBase>);` after the if block (the
#                    "else" branch — upstream uses an early-return
#                    style, no explicit `else` keyword).
#
# Each pattern's group 1 captures the opening (up to and including
# the `<LogoBase …>`), group 2 captures the children to replace,
# group 3 captures the closing `</LogoBase>);` (+ whatever
# trails). Substitution rebuilds the block as
# `group1 + marker + new_children + marker + group3`.

PROTON_WORDMARK_RE = re.compile(
    r"(if \(variant === 'with-wordmark'\) \{\s*"
    r"return \(\s*<LogoBase[^>]*>)"
    r"([\s\S]*?)"
    r"(</LogoBase>\s*\)\s*;\s*\})"
)

PROTON_GLYPH_RE = re.compile(
    r"(const logoWidth = \d+;\s*const logoHeight = \d+;\s*"
    r"return \(\s*<LogoBase[\s\S]*?>)"
    r"([\s\S]*?)"
    r"(</LogoBase>\s*\)\s*;)"
)


def proton_block_re(tsx_variant: str) -> re.Pattern | None:
    """Pattern for the matching branch of ProtonLogo's if/else."""
    if tsx_variant == "with-wordmark":
        return PROTON_WORDMARK_RE
    if tsx_variant == "glyph-only":
        return PROTON_GLYPH_RE
    return None  # ProtonLogo has no wordmark-only variant upstream.


def build_proton_replacement(prefix: str, body: str, suffix: str) -> str:
    """Wrap the new SVG body with markers, between captured edges."""
    return (
        f"{prefix}\n"
        f"                {MARKER_OPEN}\n"
        f"{body}\n"
        f"                {MARKER_CLOSE}\n"
        f"            {suffix}"
    )


def already_applied(existing_block: str, body: str) -> bool:
    """Cheap idempotency check.

    Compare the marker-bounded body inside an already-injected
    block to what we'd inject now. Misses on whitespace shifts
    but that's fine — the worst case is a no-op rewrite that
    still reports `changed`, which ansible's task-level
    register will pick up.
    """
    if MARKER_OPEN not in existing_block:
        return False
    m = re.search(
        re.escape(MARKER_OPEN) + r"([\s\S]*?)" + re.escape(MARKER_CLOSE),
        existing_block,
    )
    if not m:
        return False
    return m.group(1).strip() == body.strip()


def inject(
    product: str,
    variant: str,
    spec: dict,
    svg_path: Path,
    mirror: Path,
) -> tuple[bool, str]:
    """Return (changed, status_message)."""
    tsx_rel = spec["tsx"]
    tsx_path = mirror / tsx_rel
    if not tsx_path.is_file():
        return False, f"{product}/{variant}: tsx missing at {tsx_rel}"

    variant_spec = spec["variants"].get(variant)
    if not variant_spec:
        return False, f"{product}/{variant}: not in manifest"
    tsx_variant = variant_spec["tsx_variant"]
    expected_viewbox = variant_spec["viewBox"]

    try:
        svg_text = svg_path.read_text()
    except OSError as e:
        return False, f"{product}/{variant}: read error: {e}"

    try:
        actual_viewbox, body = read_svg_body(svg_text)
    except ValueError as e:
        raise SystemExit(
            f"validation failed: {product}/{variant}: {e}"
        )

    if actual_viewbox != expected_viewbox:
        raise SystemExit(
            f"validation failed: {product}/{variant}: viewBox "
            f"mismatch (svg='{actual_viewbox}', "
            f"manifest='{expected_viewbox}')"
        )

    try:
        assert_no_jsx_leftovers(product, variant, body)
    except ValueError as e:
        raise SystemExit(f"validation failed: {e}")

    jsx_body = rewrite_uid_refs(body)

    text = tsx_path.read_text()
    tsx_template = spec.get("tsx_template", "switch")

    if tsx_template == "if-else":
        # ADR 184: ProtonLogo's two-branch shape.
        block_re = proton_block_re(tsx_variant)
        if block_re is None:
            return False, (
                f"{product}/{variant}: ProtonLogo has no "
                f"'{tsx_variant}' branch (only with-wordmark "
                "and glyph-only)"
            )
        m = block_re.search(text)
        if not m:
            return False, (
                f"{product}/{variant}: if/else pattern didn't "
                f"match in {tsx_rel} (upstream drift?)"
            )
        if already_applied(m.group(2), jsx_body):
            return False, f"{product}/{variant}: already injected"
        new_block = build_proton_replacement(
            m.group(1), jsx_body, m.group(3),
        )
        new_text = text[: m.start()] + new_block + text[m.end():]
        tsx_path.write_text(new_text)
        return True, (
            f"{product}/{variant}: injected (if/else) into {tsx_rel}"
        )

    # Default: 6-product `{variant === 'X' && (<>…</>)}` shape.
    block_re = variant_block_re(tsx_variant)
    m = block_re.search(text)
    if not m:
        return False, (
            f"{product}/{variant}: no `variant === '{tsx_variant}'"
            f" && (<>…</>)` block in {tsx_rel}"
        )
    if already_applied(m.group(0), jsx_body):
        return False, f"{product}/{variant}: already injected"
    new_block = build_replacement(tsx_variant, jsx_body)
    new_text = text[: m.start()] + new_block + text[m.end():]
    tsx_path.write_text(new_text)
    return True, f"{product}/{variant}: injected into {tsx_rel}"


def main() -> int:
    args = parse_args()
    mirror = args.mirror.resolve()
    logos_dir = args.logos_dir.resolve()
    manifest_path = args.manifest.resolve()

    if not mirror.is_dir():
        print(json.dumps({"error": f"mirror missing: {mirror}"}))
        return 3
    if not manifest_path.is_file():
        print(json.dumps({"error": f"manifest missing: {manifest_path}"}))
        return 3
    if not logos_dir.is_dir():
        # No logos dir = no-op. Not an error.
        print(json.dumps({"changed": False, "applied": [], "skipped": []}))
        return 0

    manifest = load_manifest(manifest_path)
    products = manifest.get("products", {})

    applied: list[str] = []
    skipped: list[str] = []
    changed = False

    for product, spec in products.items():
        product_dir = logos_dir / product
        if not product_dir.is_dir():
            continue
        for variant in spec["variants"]:
            svg_path = product_dir / f"{variant}.svg"
            if not svg_path.is_file():
                continue
            did_change, msg = inject(
                product, variant, spec, svg_path, mirror,
            )
            if did_change:
                applied.append(msg)
                changed = True
            else:
                skipped.append(msg)

    print(json.dumps({
        "changed": changed,
        "applied": applied,
        "skipped": skipped,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
