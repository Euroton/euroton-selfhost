#!/usr/bin/env bash
# Fails if a WebClients checkout still ships Proton's logos or claims that only
# describe Proton AG's hosted service. Usage: check-proton-marks.sh <webclients-dir>
set -u
dir=${1:?usage: check-proton-marks.sh <webclients-dir>}
fail=0

# Claims, in shipped source for the apps Euroton builds. Locale catalogs are
# keyed by the English string, so removing it from source removes the translations.
claims='Swiss privacy|Protected by Swiss|Based in Switzerland|Swiss[- ]based|100 million|100M\+|4\.8\+ rating'
if hits=$(grep -rIlE "$claims" \
    "$dir/applications/account/src" "$dir/applications/mail/src" \
    "$dir/applications/calendar/src" "$dir/packages/components" \
    --include='*.ts' --include='*.tsx' --exclude='*.test.*'); then
    echo "False hosted-service claims:"; echo "$hits"; fail=1
fi

# Logos: replaced artwork is the Euroton "E" tile, so no logo may spell the name.
if hits=$(grep -rIl 'aria-label="Proton\|<title>Proton' \
    "$dir/packages/components/components/logo" --include='*.tsx' --include='*.svg'); then
    echo "Proton logo markup:"; echo "$hits"; fail=1
fi

# The loading splash is drawn inline, outside the logo components.
if grep -q 'M5.88 41.353' "$dir/packages/atoms/src/ProtonLoader/ProtonLoader.tsx"; then
    echo "Proton P glyph in ProtonLoader.tsx"; fail=1
fi

# Press awards & the refund badge are binary art a text search can't read.
for f in "$dir"/applications/account/src/app/single-signup/ratings/*.png \
    "$dir"/applications/account/src/app/single-signup/guarantee-illustration.png; do
    if [ "$(wc -c < "$f")" -gt 200 ]; then echo "Press or guarantee badge: $f"; fail=1; fi
done
if strings "$dir/packages/recovery-kit/templates/empty_template.pdf" | grep -qi proton; then
    echo "Proton text in the recovery kit"; fail=1
fi

[ "$fail" = 0 ] && echo "No Proton marks or hosted-service claims found."
exit "$fail"
