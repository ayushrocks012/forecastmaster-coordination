# Second page R04 — Channel, Sub-channel, Measure

Open [index.html](index.html). Three toggle-button columns separate the business
roles that were mixed in R03. All figures remain synthetic.

- **Channel:** Community, Contracts, Retail, Unassigned and Total ADS totals.
- **Sub-channel:** Community's Wholesaler/Northern Ireland and the seven
  Contracts publishing members. Parent totals and children remain independent
  views of the same demand; they are never summed together as an extra total.
- **Measure:** Ex-factory ADS plus Market, share, Abbott IMS, PI, net IMS,
  effective uplift and the matched Community diagnostic.

Ex-factory ADS controls visibility of the chosen channel/subchannel ADS series.
Switching it off preserves those choices, uses a softer selected state and
explicitly says that their ADS measure is off. Switching back restores them.
Clear all removes choices and turns that measure off; Select all restores it.

IMS measures remain shared **Community** references for the chosen drivers or
sectors. They do not invent a Market, share or PI allocation for Homecare,
Hospital or Wholesaler. Units/Value is still the top display selector, distinct
from the business measure. These are grouped report-view choices, not a newly
defined source taxonomy or a claim that every combination is a valid fact filter.

The thin actual/forecast lines, percentage graph, FY/YTD/YTG or monthly summary,
calendar independence, top driver/sector scope, search and Hide selector remain.
On narrow screens, the three labelled groups stack rather than squeeze labels.

Run `node check-sop.cjs` with Playwright installed (Windows uses Microsoft Edge).
`validation.json` records 12 behavior groups, 58 reconciliation comparisons and
385 raw/formatted cells matching R01 across five scenarios, plus responsive
light/dark rendering. These checks describe this synthetic preview, not company
Power BI performance. `preservation.json` binds unchanged fixture/calculation
definitions and the earlier saved packages. R03 and the approved first page
remain available; no application or live Power BI content changed.

Edit `page.fragment.html`; `build.py` inserts the pinned, MIT-licensed D3 source
from R01's preserved vendor folder. `index.html` is the prepared standalone
preview. R04 review and live source/performance qualification remain pending.
