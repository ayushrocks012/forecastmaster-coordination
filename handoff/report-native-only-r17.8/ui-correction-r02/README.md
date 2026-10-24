# R17.8 R02 — local native repair and expanded fabricated qualification

The local repair is qualified within its declared fabricated scope. The selected
company TEST handoff is [receiving-r01/OPEN FIRST.txt](receiving-r01/OPEN%20FIRST.txt).
Company execution and UI/business/performance acceptance remain pending; production
R16.6 stays unchanged. The maintained reference remains ../UNDERSTANDING.md.

Latest superseding scope: one isolated custom overlay is explicitly authorized;
the user rejected the six-panel grid and a 20-sector exception. All controls,
file selection and both summaries remain native. See custom-overlay-r01/ for
source/package and current source-bound native-feed/browser receipts. A larger
30-sector-per-driver fixture checks 150 sectors / 450 series / 18,900 points.
Actual and Forecast are now solid in different stable colours; Trend is dashed.
The actuals cutoff line and selected-period shading are restored. GM summary
fills classify ABS(relative variance): ≤5% green, >5–10% amber, >10% red; Plan
and unavailable cells remain uncoloured. Seventy-one native colour-boundary and admission/window cases pass. The
optimized mixed-matrix population passes 75 queries and 11,592 independent
value/colour checks. No amount arithmetic is changed.

SAMPLE04 actual Desktop checks pass Total, Share, Ex-factory/GBP Value, all
150 sectors and a single driver's 30 sectors, independent table trends, driver
expansion, file scope/clear/restore, native alert fills and compatible measures.
SAMPLE05 adds optimized colour evaluation and CSV-safe summary display formats;
40 Microsoft schema documents pass. Its native Market Units export now passes all 150 sectors / 1,500 cells;
Review export passes ten cells. Share also passes all 1,500 exported cells
and renders both expanded summaries. Ex-factory GBP Value also passes all 1,500 exported cells. Native timings are
recorded: graph about 2.1–2.2s, Review 4.3–4.9s, Executive 9.9–16.3s, depending
on context/expansion. Company performance is unqualified; Executive remains slow.
Native save/reopen passes. The guarded receiving cell/template are now locally
qualified: 41 schemas, five fake-client tests, 51 exact native queries. Company
installation remains unexecuted. Preserve older failed Share/hierarchy/export
and harness attempts; details are in the receiving qualification receipts.

The expanded sample contains **20 files total over two cycles**, five growth
drivers, ADS plus an alternative for each driver/cycle, 30 sectors per file in the largest fixture,
84 months and 504,000 component facts (earlier 25-sector fixture: 420,000). All data is generated. Both cycles are
tested individually; this does not authorize summing multiple versions/cycles
into one forecast or claim complete R16.6/S&OP/FX feature parity.

The matching pure adapter changes 15 unique selection/admission and matrix
cell-evaluation expressions plus two summary dynamic-format definitions. Numeric
Plan/Benchmark/fit/monthly formulas, raw measure values, tables, dates,
relationships and sources remain unchanged. Summary literal display sections
correct native CSV k/m scaling and signs while keeping the cells numeric. Cleared files no longer invoke Automatic ADS. The report has a
searchable native List slicer with explicit ADS file defaults, driver-scoped
choices and import UTC times; compatible Section bookmarks; driver→sector rows;
three visible Review rows; an external dynamic heading and bottom chart legend;
compact independent trend selectors; no Apply or source-mode dropdown. An optional
Reset files action was rejected after Desktop showed it cleared the visual
availability condition; the current build omits that optional action. The sector selector's
old Forecast tiers label is corrected to Sectors / forecast tiers.

Current evidence:

- VALIDATION-SMALL.json: 212 logical contexts / 1,865 assertions, including the
  preserved 96 independent oracle/baseline/candidate scalar contexts. The original
  two malformed empty-filter checker queries are retained; two extra native reads
  fix only typed empty-table construction against identical candidate bytes.
- VALIDATION-LARGE.json: 12 native reads verify exact population, readable import
  times/default labels, weighted share, Market/Ex-factory and no-file blanks.
- VALIDATION-LARGE-WORKFLOWS.json: 144 contexts / 576 independent arithmetic
  comparisons across six metrics, Units/Value, both cycles, three windows and
  two FY years. Complete 125-sector / 625-cell Executive contexts and chart /
  mixed-version populations are also checked. Eight corrected categorical chart
  grouping reads supplement, rather than overwrite, the original checker run.
- Fourteen focused Python contracts pass; the latest generated SAMPLE has 40
  Microsoft schema documents checked. Schema checks are separate from Desktop.
- Actual expanded SAMPLE Desktop inspection is recorded in UNDERSTANDING/STATUS.
  A crowded 25-sector legend and expanded table query cost remain improvement
  work. Local calculated-model refresh/query timings cannot qualify Fabric.

For maintainers, from the Coordination root:

```bash
python3 handoff/report-native-only-r17.8/ui-correction-r02/test_correction.py
python3 handoff/report-native-only-r17.8/ui-correction-r02/native_cases.py NEW_SMALL_DIRECTORY
python3 handoff/report-native-only-r17.8/ui-correction-r02/large_fixture.py NEW_LARGE_DIRECTORY
python3 handoff/report-native-only-r17.8/ui-correction-r02/large_workflow_cases.py NEW_WORKFLOW_DIRECTORY
```

Each builder refuses an existing destination. Windows run_synthetic_engine.ps1
uses a task-owned calculated-only loopback engine and never attaches an existing
Desktop model. run_large_engine.ps1 processes only the candidate. Both checkpoint
each query and use an explicitly allocated loopback port; a previous Port=0 run
attempted the already occupied default 2383 socket. Keep stopped runs. The launch
helper decouples long Windows qualification from a WSL command session's lifetime;
two earlier WSL sessions ended with exit 143, without DAX failure evidence.

Do not substitute this fabricated BIM for company metadata or reuse an older
installer. Any later receiving adapter needs private default-label metadata,
exact installed-R01 guards, numerical preflight, full backup/readback/cloud
preservation and the separate company UI/performance gates.
