# ForecastMaster Review R04.2: load a cycle once

R04.1 requests another model query when Section/Measure, driver or profile changes.
R04.2 loads all seven monthly measures, drivers and profiles for the selected
affiliate and demand-cycle set. These loaded selections then run locally:
Growth driver, Sector, Channel, Sub channel, Section, Measure, Ext/Local, months,
periods, plotted files and benchmark Base. Changing affiliate or demand cycles
loads a new feed. A report reload after a completed model refresh loads fresh data.

**Prepared and tested locally; company installation and interaction speed are
still pending.** The first cycle load still depends on the model and network.

## Receiving steps, in order

1. On the office laptop, pull the latest `main` in `forecastmaster-coordination`.
   Open `handoff/report-cycle-cache-r04.2/` in File Explorer. The two operator
   files are `ForecastMaster_Review_R04.2.pbiviz` and
   `Install_Cycle_Feed_R04.2.ipynb`.
2. In Fabric, open the **existing ForecastMaster Review report**, select **Edit**,
   then its **Review meeting** page. In the Visualizations pane select **… >
   Import a visual from a file** and choose `ForecastMaster_Review_R04.2.pbiviz`.
   Accept Import/Replace if shown, then **Save** the existing report. The GUID is
   unchanged, so this updates the existing review visual. Keep the existing
   visual on the page with its current fields. If it has not changed to R04.2,
   retain the screenshot and check that before continuing.
3. Return to workspace **UK-ANI-Demand**. Select **Import > Notebook** and choose
   `Install_Cycle_Feed_R04.2.ipynb`. Open it and select **Run all** once.
   Use this separate, unscheduled setup notebook. Its only model target is the
   existing **ForecastMaster Demand Model**. It backs up and verifies the
   current definition before updating six feed expressions. If an API or
   definition check fails, retain the full output for the next step.
4. Below the code cell, wait for `Status: INSTALLED` (or `ALREADY_INSTALLED`)
   and `READY: R04.2 cycle feed verified...`. The backup/receipt path is printed
   in the same output. The setup notebook does not start a source refresh.
5. Reload the existing report. On **Review meeting**, select **Oct 2026** and
   allow that cycle to finish loading. Then change Section/Measure, Channel,
   Sector and Growth driver. These changes should use the loaded cycle without
   the yellow loading bar. Changing demand cycles can show the loading bar.
   Confirm your normal saved-file selection, benchmark and business values.
6. Return the installer output and the observed response times. Local test
   timings do not establish speed on the company capacity.

Import the visual **before** running the model installer: the new visual also
supports the existing schema-4 feed during this step. The new feed uses schema 5.
The existing report URL, pages and native Refresh Demand button remain in the
existing saved report. No Desktop report or semantic model republish is involved.
The hourly schedule, ad hoc listener, Functions and refresh notebooks retain
their current setup. No tenant-admin or IT setup is part of these steps.

Microsoft's import steps: [Import a visual from a file](https://learn.microsoft.com/en-us/power-bi/developer/visuals/import-visual).
The model installer uses the operator's notebook session and the documented
[Get definition](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/get-semantic-model-definition)
and [Update definition](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/update-semantic-model-definition)
APIs. Their availability for this company model is a receiving check.

## Calculation and refresh contract

Each metric has its own map of file/month/dimension numerator and denominator
components. Section or Measure never reuses another measure's values. Saved
actuals cutoffs, path identities, comparisons, weighted shares, zero values,
blanks, missing-contributor rules, and 12/24-month trends use the retained R04.1
arithmetic. `Visual/src/cohorts.ts` and `files.ts` are unchanged.

Availability is derived from all numeric cycle rows for the selected
driver/profile cohort, independently of the current measure. A ratio requires
reported numerator and denominator components. Zero is reported data. A wholly
unreported month remains blank; a zero denominator still gives an undefined ratio.

The complete-feed flag verifies all measures and every reference file in the
selected country/cycle set. Old narrow filters trigger a complete-cycle request
instead of treating that partial scope as loaded. Only complete accumulated feeds replace the previous complete view. A late response for another cycle cannot
replace the current cycle. Every new complete model feed replaces the maps and
availability index; there is no persisted cross-refresh data cache.

Power BI's aggregate fetch limit still applies. If reached, the visual reports
that the result is incomplete and requests a smaller cycle set. It does not
present partial values as a complete result. See [fetchMoreData](https://learn.microsoft.com/en-us/power-bi/developer/visuals/fetch-more-data).

## Maintainer sources and checks

- `Visual/src/`: updated visual source; `Visual/package-lock.json`: exact dependencies.
- `baseline/`: retained R04.1 feed generator and legacy renderer used by regressions.
- `build_feed.py`: generates the nine-measure feed payload and optional TMDL script.
  Six expressions differ. Numeric aggregation bodies are byte-identical after
  their transport-scope guard. Metadata catalogue/file/bounds expressions remain.
- `install_feed.py`: TMSL expression-only model patch, backup/readback/concurrency
  checks, existing-data retention, idempotent verification and bounded LRO polling.
  Partitions, source tables and non-feed definitions are compared before/after.
- `build_notebook.py`: produces the standalone Fabric installer.
- `tests/`: arithmetic, browser, native-engine fixture, load/race and installer checks.
- `validation/`: dated results and a synthetic rendered screenshot.
- `MANIFEST.json`: package file hashes; the repository handoff manifest adds this
  package without changing earlier handoff entries.

To rebuild, run `npm ci` in `Visual/`, `npx tsc --noEmit`, and `npx pbiviz package`.
Run the Python installer tests with pytest. For browser checks, install Playwright
and esbuild in a QA tool directory, set `FM_QA_NODE_MODULES` to its `node_modules`,
and run `node tests/run.cjs`; `PLAYWRIGHT_BROWSERS_PATH` can select browser storage.
`python build_feed.py` and `python build_notebook.py` reproduce the model payload.
The native DAX fixture was executed against an isolated CSV-only Power BI Desktop
model, including stored expressions; it is synthetic, not a company model export.

GitNexus quick query and pre-impact were attempted against the actual visual
source but failed with ENOSPC in shared state storage. Direct tracing covered
decode -> scope/filter -> availability -> CohortMath -> render; graph impact
remains unavailable. This is recorded in `VALIDATION.json`, not reported as zero
impact. The original R04.1 delivery source and SDM checkout remain unchanged.
