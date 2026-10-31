# Euroton brand assets

The playbook applies these to the client source before building. The artwork is original: an "E" tile with the product name, and none of Proton AG's marks.

`palette.yml` holds hex & RGB substitutions, applied across `packages/colors/themes/src/*.css`. Each `proton_hex: euroton_hex` pair is a literal string replace, so keep the list to brand colors. Success green, error red & the neutral grays are functional and should stay.

`logos/<product>/<variant>.svg` holds one SVG per app & variant. Each has to keep the `viewBox` listed in `logos/manifest.yml`, or the deploy stops. `logos/inject-logos.py` rewrites the `id="logo-X"` references to the per-render `${uid}-X` form upstream uses, so two logos on one page don't collide, then writes the body into the matching `<Product>Logo.tsx`.

Each product's `glyph.svg` also becomes the app's favicon. Account uses `proton/glyph.svg`, the directory name upstream gives its cross-product mark.
