# ForecastMaster GM Desktop candidate R16

This is the first production-feed port of the approved paired R15 HTML design.
The user authorized a fresh Desktop report, removal of the old Review meeting
page, and retention of the separate native Refresh Demand page. Publication is
the user's next receiving action, after company verification.

`prepare_project.py` reads a supplied thin PBIX without altering it. It writes a
new PBIP/PBIR report, retaining the existing model connection and every byte of
Refresh Demand. It includes an unchanged source PBIX rollback copy. The actual
company-bound output is private, outside this public repository. Do not commit
that output, its connection metadata, or company screenshots/data here.

The new Power BI pages are Demand review, S&OP review and Refresh Demand. Each
native page has its own visual session. The visual's internal Demand review /
Explore in S&OP navigation carries the shared selection, source choices and FX
between the two approved views. Native page-tab switching does not synchronize
their separate instances; this distinction is explicit in the receiving guide.

## Source binding and calculations

The visual consumes complete monthly components from the existing `fm_review`
tables through four report-local DAX measures. It does not require a semantic
model definition replacement. All seven original reporting rules remain;
`SETUP REPORTING FEED.py` adds twelve exact-identity component rules for the
approved S&OP subset. It preserves custom rules, rejects conflicting identities,
holds the existing shared OneLake writer lease, backs up/read-verifies rules,
and rechecks for a concurrent change before writing. It does not start a job.
One normal native request then rebuilds the derived projection and refreshes
the existing model using the unchanged R05.4/native worker.

The approved neutral bridge catalogue owns Channel/Sub-channel/Measure order.
Community's own total and the sector total read their direct identities;
parent and child selections never become an additive stack. PI/net are saved
source measures, not demo percentages or new calculations. Share is the ratio
of summed Abbott and Market components. Source blanks, missing months,
ambiguous source cohorts, missing training windows and zero denominators remain
unavailable. Numeric zero is valid. The same numeric engine feeds both views.

Review years follow the visible month calendars, while named FY/YTD/YTG windows
retain their full meaning and separate saved IMS/EF cutoffs. Trend fits require
all 6/12/24 training observations. Run rate and same-period growth retain R15
rules. All synthetic generators and allocation weights are removed from the
production bundle. `build_fixture.py` alone creates explicitly synthetic tests.

Plan rates are review-session inputs, initially blank. UK amounts use the
existing projection's business GBP basis; monetary conversion is applied once.
Units, share and business growth retain their basis. Future non-UK monetary
sources need qualified currency metadata; this candidate does not infer a
currency from an unfamiliar Affiliate or claim future multi-currency business
acceptance. The generic conversion controls retain missing/zero safeguards.

## Performance and limitations

The complete transport groups by source/month/component/context, rather than
cross-joining the metric catalogue. After load, this visual never calls
`applyJsonFilter` for local choices. It caches component lookup and trend fits.
A changed host delivery invalidates the entire derived cache. Segmented feeds
are accumulated before render; refused pagination withholds partial totals.
Initial loading, host memory limits and company model latency are receiving
checks, not established by browser tests. The existing report's row/dimension
filters must not be reused to silently narrow the new visual's feed.

Both top-level Power BI pages embed the new private visual; there is no CDN,
network privilege or evaluation of downloaded JavaScript. Runtime source text
is escaped/sanitized before DOM insertion. TypeScript compilation, the Power
BI packaging linter, synthetic packaged-browser tests, edge-case arithmetic,
schema validation and exact rollback/refresh-page preservation are local gates.
Native Desktop opening, live DAX evaluation, company total reconciliation,
published button operation and measured company-laptop performance remain
unexecuted receiving gates.

The local Computer Use probe failed before Desktop inspection with
`sandboxCwd is not a local file URI`. Consequently the deliverable is an honest
PBIP candidate, not a claimed Desktop-saved PBIX. Power BI can open its `.pbip`
or `definition.pbir`; the user can Save As PBIX after validating the connection.

## Reproduce

From `Visual/`, run `npm ci --ignore-scripts`, then from this folder run:

```text
python3 build_setup.py
python3 build_visual.py
Visual/node_modules/.bin/tsc -p Visual --noEmit
```

From `Visual/`, run `node_modules/.bin/pbiviz package` (zero lint errors).
From this folder, `python3 build_fixture.py` prepares synthetic data for the
packaged visual. `check-package.cjs` uses the installed Windows test browser;
its runtime path may need adapting on a different host. Compile `live.ts` to
`local-test/math` and run `node check-math.cjs` for the numeric edge cases.

```text
python3 prepare_project.py <private-source.pbix> <new-private-output-folder>
python3 check_project.py <private-source.pbix> <private-output-folder>
```

`OPEN FIRST.txt` gives beginner receiving steps. Preserve R15, R04.2 and every
earlier package. GitNexus's bounded impact probe for `decode` returned
ACTIONABLE_PARTIAL / UNKNOWN; direct tracing of the host decoder, source
projection and canonical BR-005/S&OP contract supplemented that incomplete
graph result. No zero-impact assertion is made. The application checkout and
workbooks were read only throughout this task.

The final GitNexus `detect_changes` probe returned UNAVAILABLE with
AUTHORITY_DRIFT_BLOCKS_CONCLUSION, rather than a clean impact result. The
project's source visualContainer schema 2.14.0 URL returns HTTP 404; eleven
other report/project files validated against their public Microsoft schemas.
Retain that version and verify those visual containers in Desktop.
