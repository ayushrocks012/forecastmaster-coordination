# Second page R02 — S&OP side panel

Open [index.html](index.html). This is the left/right revision of the separate
S&OP page. It uses synthetic data. R01 and the approved first-page R11 remain
available with their original bytes.

- Top: demand cycle, summary periods, Units/Value and combined/driver/sector
  presentation, with the month calendars and shared growth-driver/sector scope.
- Left: a floating-style, anchored panel of channel and subchannel buttons.
  Click once to add a measure to the graph and table; click again to remove it.
  Selected buttons show a checkmark and a filled state. No Ctrl key is needed.
- Community retains Market/share/Abbott/PI/net/factor observations, its
  Ex-factory ADS and Wholesaler / Northern Ireland children. Contracts retains
  its seven source subchannels. Parent buttons add the total only; they do not
  silently select or deselect their children.
- Search finds choices without changing existing selections. Select all shown
  adds the visible matches. Clear all selects no measures and shows an empty
  review, rather than silently treating no selection as all measures.
- Right: the graph above the FY/YTD/YTG or monthly table. The optional
  Ex-factory build-up counts each publishing leaf once, as in R01.
- Hide selector / Show selector changes space, not the selected data. On narrow
  screens, the panel moves above the graph; the same Hide control remains usable.

The established [R01 business meaning](../sop-build-up-r01/README.md) and its
synthetic fixture are retained: Community = Wholesaler + Northern Ireland;
Contracts = seven leaves; Total ADS = eleven leaves once; weighted share and
effective uplift; distinct IMS/EF cutoffs; unavailable values stay blank.

The panel is styled as a floating surface and sticks alongside a scrolling
desktop preview. It is not a freely draggable window. The
[Power BI feasibility note](powerbi-feasibility.md) separates that design from
the eventual report implementation. No Power BI content was changed.

## Evidence

`check-sop.cjs` verifies single-click and keyboard toggles, graph/table sync,
left/right placement, periods at the top, panel hiding without data loss,
parent context, Units/Value and ratio graphs, FY/YTD/YTG versus monthly,
driver/sector/cycle grouping, leaf allocation, hover/touch details, empty states,
responsive widths and light/dark rendering. It retains the 58 reconciliation
comparisons and checks raw/formatted numeric parity against R01 across five
scenarios. Results are in `validation.json`; screenshots are alongside it.

Run with Node.js and Playwright (Windows uses Microsoft Edge):

```bash
node check-sop.cjs
```

`preservation.json` verifies the old design files and unchanged calculation
functions. Source is `page.fragment.html`; `build.py` inserts the pinned,
MIT-licensed D3 source retained under the R01 vendor folder, then produces
`review.fragment.html`. The standalone `index.html` is ready to open without
network data access. Warm render timings describe this synthetic page only.

Review of this revision and actual Power BI implementation, source binding,
freshness and performance validation remain pending.
