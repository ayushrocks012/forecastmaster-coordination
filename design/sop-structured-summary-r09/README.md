# Second page R09 — Audited contexts and structured S&OP summary

Open [index.html](index.html). The user requested checking every remaining
Channel/Sub-channel and measure/order against the bridge, and replacing the
summary's repeated heading lines with a clearer standard table. R08 and all
earlier designs remain preserved. Power BI is unchanged.

## Bridge audit and scope

`audit_bridge.py` read both retained neutral Core Oral and Paed SIP definitions,
covering all **29 sector definitions, 13 Channel/Sub-channel contexts and 18
displayed executive measures** in Units and Value. It inspected 10,179 structural
data rows and verified 1,044 full binding identities and 58 per-sector/dimension
orders. No differences were found in the displayed measure identities or their
order. `bridge-audit.json` records the counts, descriptor hashes, context
coverage and limits. Only whitelisted structural identities are copied; not
Product/Manufacturer/Sector identities, source values or formulas.

Source context order is:

1. Community blank, Wholesaler, Northern Ireland
2. Contracts: Homecare, Hospital, Healthcare Logistics, Competitor, Nursing Home
3. Out of Pocket: Retail
4. Contracts resumes: Private Order, Internal Account
5. Unassigned: Unassigned
6. Sector total: blank

The selector now follows this same source order rather than grouping Private
Order/Internal Account before Retail. The second Contracts segment is labelled
as a continuation, with one Channel toggle controlling both segments. It is
not an extra Channel. The summary uses the same order for selected records.

Community blank retains Share → Abbott IMS → Market → PI → IMS minus PI → ADS.
Other source contexts each have their own ADS Units/Value. The user explicitly
chose **ADS Units/Value only for Homecare and Hospital**, so baseline/day,
new-contract and shipment-adjustment workings remain outside this GM page.
Cur/Pub and extra diagnostics remain excluded. This is the reviewed executive
subset, not an assertion that every bridge input/working is displayed.

Physical row numbers can differ across sector layouts. The catalogue now records
observed row ranges per source driver instead of presenting one example row as
universal. Matching uses Channel, Sub-channel, role, Section and Measure. Share
above Abbott IMS remains confirmed in both dimensions.

To repeat the read-only audit with authorized retained definitions available:

```bash
python3 audit_bridge.py --source-root /absolute/path/to/neutral-definitions
```

The metadata audit does not qualify a current live workbook or receiving Fabric
source. GitNexus again reported stale authority/index; direct retained identities
and the current neutral-binding reader supplied the bounded evidence. No shared
index was refreshed and no application checkout or workbook was modified.

## Summary structure

There is one column-header row: **Channel | Sub-channel | Measure | selected
periods**. Channel and Sub-channel labels merge vertically across their measures.
Numeric rows use short measure labels rather than repeating full paths. There
are no full-width Channel/context heading lines among numeric records. If a
Channel resumes later in source order, its label appears in the relevant Channel
column block. A selected child does not create an unselected parent-total row.

Total/Drivers/Sectors remains a presentation choice beside the graph. Multiple
groups or cycles add a merged Review scope column rather than extra header-like
lines. FY/YTD/YTG periods and Monthly columns retain their independent calendar
roles. Units/Value updates measure labels and formats; Share stays on the graph's
right percentage axis. Calendar basis is available on each measure's tooltip;
net IMS keeps its IMS cutoff despite its Ex-Factory source Section.

Explicit selection gates, empty initial results, source totals and independent
context toggles are retained. Source totals already include their sub-channels;
no additive grand total is manufactured from overlapping selected rows.

## Validation and preservation

`validation.json` records 13 browser integration groups, 216 raw fixture values
matching saved R08 and 64 reconciliation comparisons. It checks the source audit,
all context orders and independent ADS toggles, merged summary labels, one header
row, absence of context-heading records, dynamic labels, multi-driver grouping,
calendar/period independence, responsive light/dark layouts, hover and no warm
network requests/script errors. `preservation.json` checks prior saved designs
against their existing manifest hashes.

All numeric observations remain synthetic. The audit verifies retained metadata;
it is not live source binding, report installation or Power BI performance
qualification. Edit `page.fragment.html` and the audited catalogue, build with
`build.py`, and run `check-sop.cjs` in Playwright (Microsoft Edge on Windows).
