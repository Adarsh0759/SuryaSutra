#!/usr/bin/env bash
# Downloads prototype source documents into data/raw/ and records their SHA-256
# hashes in data/raw/checksums.sha256 (D-13: never redistribute vendor manuals —
# commit this script + hashes, not the PDFs themselves).
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p data/raw

NREL_URL="https://www.nrel.gov/docs/fy19osti/73822.pdf"
NREL_OUT="data/raw/nrel_pv_om_best_practices_3rd_ed.pdf"

SUNGROW_URL="https://info-support.sungrowpower.com/cms/af994f1d-bb0d-408a-b310-6ad732402c99/GUID-D2B323B4-885F-43CE-AA2D-F51E34E85DC3_1_en-US_PDF%20(%E4%BA%A7%E5%93%81%E4%BF%A1%E6%81%AF%E8%AE%BE%E8%AE%A1%E9%83%A8_%E5%9F%BA%E7%A1%80%E7%89%88)_1781846823856_compressed.pdf"
SUNGROW_OUT="data/raw/sungrow_sg150cx_user_manual.pdf"

download() {
    local url="$1" out="$2" label="$3"
    if [ -f "$out" ]; then
        echo "[skip] $label already at $out"
        return
    fi
    echo "[get]  $label -> $out"
    if ! curl -fsSL "$url" -o "$out" --max-time 120; then
        echo "[FAIL] could not download $label from:" >&2
        echo "       $url" >&2
        echo "       Download it by hand in a browser and save it to $out" >&2
        return 1
    fi
}

download "$NREL_URL" "$NREL_OUT" "NREL PV O&M Best Practices (3rd ed.)" || true
download "$SUNGROW_URL" "$SUNGROW_OUT" "Sungrow SG150CX user manual" || true

echo
echo "Recomputing data/raw/checksums.sha256 ..."
{
    for f in data/raw/*.pdf; do
        [ -f "$f" ] && sha256sum "$f"
    done
} > data/raw/checksums.sha256

echo "Done. Verify against data/raw/SOURCES.md:"
cat data/raw/checksums.sha256
