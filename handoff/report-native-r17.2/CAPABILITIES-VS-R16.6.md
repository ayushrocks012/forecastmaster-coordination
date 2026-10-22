# R17.2 TEST compared with R16.6

Checked from source and synthetic native-engine execution on 22 October 2026.
The published R16.6 remains the production report. This candidate is closer;
it is **not yet a fully equivalent native replacement**.

| Area | R17.2 change | Evidence / remaining check |
| --- | --- | --- |
| Blank blue buttons | Visible default-state labels, teal/white formatting, correct container-level PageNavigation/Bookmark actions | Definitions and target references checked; Desktop Ctrl+click and Service click still need receiving verification |
| Query cost | Retrieve facts once per selected file/month/component, then check missing cells by sector; remove redundant whole-fact availability scans; prefilter chart lines | 2,675 synthetic engine checks; 500-sector headline query tested on 816,000 fabricated rows; company capacity still pending |
| R16.6 layout | Matching top geometry, separate driver/tier dropdowns on the same dimension, shared summary period position, header plan rates, concise period summary, numeric m/k/currency formatting | PBIR schema/structural checks pass; visual appearance still needs Desktop screenshots |
| Opening chart scope | Selected cycle year's Jan–Dec range; suppress empty categories outside Review months | Source/schema checked; receiving interaction pending |
| Multiple 6/12/24M chart trends | Chart uses the selected Trend comparisons, alongside the independent headline window | Native DAX compiled; simultaneous native line rendering remains a receiving check |
| H1/H2 and cross-year YTD/YTG | New native period metadata and month masks match the saved cutoff month in the named year | Synthetic current/historical/future period arithmetic passes |
| S&OP driver/sector breakdown | Native grouped matrix follows Total/Drivers/Sectors/Both | Synthetic driver arithmetic passes; visual expansion/order needs receiving checks |
| Mixed saved cutoffs | Plan/period uses earliest saved cutoff; aggregate trend requires a common saved cutoff | Separate mixed-cutoff engine case passes; this follows R16.6 `scopeFit`, not an invented fit across different cutoffs |
| Negative benchmark % | Divide plan-minus-benchmark by absolute benchmark | Separate negative-history/future-plan fixture returns the expected -20% |
| Missing vs zero / weighted shares | Preserve missing leaves, available aggregate members, independent available numerator/denominator sums and true numeric zero | Existing synthetic arithmetic/FX/source checks retained; company reconciliation still pending |
| Monthly readout | Native chart point selection can feed a monthly readout while chart-to-summary filtering is disabled | DAX and interaction definitions checked; not the exact R16.6 pinned tooltip |

The local 500-sector query returned ten numeric cells across four periods in
approximately 0.7 seconds. This is one synthetic local import/calculated-engine
observation, not a company Direct Lake benchmark, a guarantee for every visual,
or evidence that 500 simultaneous sector lines are readable.

## Native gaps still open

- Demand selects one measure at a time; S&OP supports multiple selected measures.
- The exact largest-gap shortcut with explicit ranking period/window is absent;
  native ordinary sorting is available.
- Click-to-pin R16.6 tooltip and linked legend/table/line hover are not reproduced.
- Hide/Show uses fixed native canvas geometry. It does not reflow surrounding
  objects; native Focus mode supplies a larger chart/table view.
- Company figures, multi-cycle/version/rate interactions, source propagation,
  genuine export output, zoom/focus, visual styling, accessibility and capacity
  remain receiving gates. Engine checks do not establish these.

The small custom control for sibling drag order, hierarchy gating and explicit
FX entry is retained unchanged; charts, matrices, slicers, buttons and exports
are native. These control exceptions have **not** been proven unavoidable native
limitations. The untouched R16.6 Advanced workspace is a fallback, not parity.

Two native report pages share selections and navigation. This gives each page
native export/focus capabilities. It is an intentional architecture difference
from the R16.6 HTML workspace switch. Unavailable native cells stay blank; real
zero stays numeric zero. Neither presentation choice authorizes inventing data.

## Scope and rollback

The updater only targets existing TEST model
`31d00232-ac03-48fe-af39-f2e4bae82443`. Its name remains **ForecastMaster Native
OneLake R17.1 - TEST**. It preserves original source tables, inherited repaired
feed measures, roles, source mode, connection mapping and unrelated metadata.
The complete before/candidate definitions and mapping stay in a verified private
OneLake backup. No production update, publish or explicit refresh is automated.

Previous ZIPs and installers are frozen. Keep using published R16.6 while this
candidate is qualified. A new thin report and a TEST-only updater are shipped
together; opening R17.2 before applying its model update can show missing fields.
