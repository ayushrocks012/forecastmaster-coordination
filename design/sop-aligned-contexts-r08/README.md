# Second page R08 — Aligned source contexts

Open [index.html](index.html). This separately saved revision removes the top
Section and Selected scope controls, removes Cur/Pub from this executive page,
and gives each real Sub-channel a separate aligned row. R07 and every earlier
design remain preserved. Power BI is unchanged.

## Read the selector down the bridge

Community's **blank Sub-channel** owns these six choices, in order:

1. Share %
2. Abbott IMS
3. Market
4. PI
5. IMS minus PI
6. ADS

Wholesaler starts below all six blank-context measures and has its **own ADS**
button. Northern Ireland follows with its own ADS. Subsequent Channels contain
their actual source Sub-channels with their own ADS choices. The Channel cell
spans its contexts; spacing and horizontal separators show each relationship.
IMS is never visually aligned with Wholesaler or allocated into it.

Every source context and measure toggles independently. Turning off Wholesaler
ADS, including via the legend, does not turn off Community total or Northern
Ireland ADS. Channel off removes only its descendants. Re-enabling restores
the user's valid choices. Channel, context and measure remain explicit, with
no automatic selections. Graph and table start empty and share those choices.

## Bridge order confirmation

The retained neutral V18 bindings put **Abbott Volume Share at row 66**, above
**IMS Abbott Selling units at row 67**. Value Share is at row 81, above IMS
Abbott Value at row 82. The descriptor SHA256 values recorded in the catalogue
were checked against the retained source descriptors during this revision.
This confirms Share above Abbott IMS in the bounded retained bridge definitions;
it is not a new live workbook audit.

`bridge-catalog.json` now exposes only the 18 direct identities requested for
this executive subset: five IMS/share/net measures and 13 source ADS contexts.
Cur/Pub observations and controls are excluded, rather than renamed to ADS.
The existing source hierarchy, Out of Pocket → Retail and real blank contexts
remain intact. There is no derived Contracts total or extra diagnostic measure.
Only neutral identities and row positions are copied, not real workbook values.

## Filters and presentation

Affiliate, Demand cycle and Units/Value are the only top dropdowns. The visible
From/To month calendars and shared searchable Growth-driver/sector choices
remain. Affiliate contains only the confirmed UK sample. No Section filter is
needed because the source context determines applicable measures and cutoffs.

The old Selected scope dropdown was a **presentation control**, not another
data filter: it combined selected sectors or separated them by driver/sector.
That capability is now the compact **Total / Drivers / Sectors** control beside
the graph. It changes the graph and summary presentation while preserving the
same included sectors and measures. FY/YTD/YTG periods stay beside the summary;
Monthly follows the calendars. Summary periods and chart dates stay independent.

Changing Units/Value renames Share, Abbott IMS, Market, PI, IMS minus PI and each
ADS button/legend/tooltip/table row. Share stays on the right percentage axis;
amounts use the left axis. Net IMS retains the IMS cutoff, despite its source
Section being Ex-Factory. Parent totals include their children; selecting both
shows both lines/rows and does not create a second additive total.

## Verification and limits

`validation.json` records 11 integration groups, 216 retained fixture values
matching saved R07 and 64 reconciliation comparisons. Checks include separate
context geometry, Share-first source order, independent ADS toggles, disabled
parent/context gates, removed controls and measures, dynamic labels, source-only
bulk selection, Affiliate, view modes, calendars, responsive light/dark layouts,
cross-series hover and no warm network requests/script errors.

All numbers are synthetic design observations. Source metadata does not prove
live data binding, every bridge-measure coverage or Power BI performance.
`preservation.json` checks prior saved designs against their previous manifest
hashes. No application source, workbook, Fabric item or Power BI content changed.
Edit `page.fragment.html` and `bridge-catalog.json`, build with `build.py`, and
run `check-sop.cjs` with Playwright (Microsoft Edge on Windows).
