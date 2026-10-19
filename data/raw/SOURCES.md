# Prototype source documents (D-12, D-13)

Not committed to git (see `.gitignore`). Run `scripts/download_docs.sh` to fetch them;
verify each download against the SHA-256 in `checksums.sha256`.

## 1. Sungrow SG150CX user manual
- **Brand / model:** Sungrow, SG150CX (string inverter)
- **Doc type:** manual (includes §9 Troubleshooting and Maintenance: fault-code table + safety procedures)
- **Why this brand:** Sungrow leads India's utility-scale inverter market — ~50%+ share of central inverters, ~20% of string inverters, per JMK Research 2025 data (D-02 target market). Manual is publicly downloadable from Sungrow's own site, no login required.
- **Source URL:** https://www.sungrowpower.com/en/products/string-inverter/sg150cx (page hosting the manual; direct PDF link in `download_docs.sh`)
- **Local path:** `sungrow_sg150cx_user_manual.pdf`
- **Downloaded:** 2026-10-19
- **License note:** © Sungrow Power Supply Co., Ltd. Public manual, downloaded for internal R&D/prototyping use. Not redistributed — see D-13.
- **Verified content:** 118 pages; pages 96–110 are "9 Troubleshooting and Maintenance" with a Fault Code / Fault Name / Corrective Measures table and DC-isolation / DANGER / CAUTION safety blocks.

## 2. NREL — Best Practices for O&M of Photovoltaic and Energy Storage Systems, 3rd ed.
- **Doc type:** safety / procedure reference (cross-brand)
- **Report number:** NREL/TP-7A40-73822 (Dec 2018), authored by NREL, Sandia, SunSpec Alliance, SuNLaMP PV O&M Best Practices Working Group
- **Source URL:** https://www.nrel.gov/docs/fy19osti/73822.pdf
- **Local path:** `nrel_pv_om_best_practices_3rd_ed.pdf`
- **License note:** Public NREL technical report, no-cost. Not redistributed — see D-13.
- **Verification note:** this sandbox's network cannot resolve `.gov` domains (confirmed: `nrel.gov`, `osti.gov` both fail DNS here; a SunSpec mirror also blocked the request as a bot). The URL itself is correct per NREL's own publication listing — verify the download succeeds on your machine when you run `scripts/download_docs.sh`.
