# OneLake R17.1 isolated qualification candidate

**Latest receiving result, 22 October 2026: TEST refresh failed.** The operator
subsequently copied the complete error: calculated tables/columns referring to
Direct Lake require an explicit connection with granular access control (GAC).
Continue with [FIX TEST CONNECTION - STEPS.txt](FIX%20TEST%20CONNECTION%20-%20STEPS.txt).
It maps only this TEST model to a matching shareable cloud connection, then
requests one refresh. Microsoft states that shareable connections always enforce
GAC. The current actual binding is not yet known; no company connection was
changed by this host. Do not recreate the model, convert source mode, disable
SSO, or change tenant/workspace settings from this error. A successful connection
fix and processing result must still be received before native report acceptance.

**Receiving update, 22 October 2026:** the operator supplied a successful creation
and readback result for **ForecastMaster Native OneLake R17.1 - TEST**, ID
`31d00232-ac03-48fe-af39-f2e4bae82443`. The original model was unchanged and the
20 helper definitions were confirmed. Successful processing and rendering remain unverified.
Continue with [NEXT - REFRESH AND OPEN TEST.txt](NEXT%20-%20REFRESH%20AND%20OPEN%20TEST.txt);
do not rerun creation.

The separate `candidate/ForecastMaster Native Review R17.1 TEST.zip` is connected
to that TEST model. `bind_test_report.py` changes only the copied project path
and model connection; 136 report payloads, including every visual and the original
Refresh Demand page, retain their bytes. The ZIP contains the thin report and
current instructions, with the obsolete SQL installer/probe excluded. The old
R17 ZIP stays unchanged. Five local package tests verify binding and preservation;
they do not establish company refresh, rendering or export success. This copy
does not address the previously documented R17 feature/calculation gaps.

Start with [OPEN FIRST - ONELAKE.txt](OPEN%20FIRST%20-%20ONELAKE.txt). The operator's
22 October 2026 source-route result confirmed the fact partition references an
M `AzureStorage.DataLake` expression, with `directLake` storage. This is Direct
Lake on OneLake. The frozen R17 SQL installer cannot serve that source route.

This package creates a **new** semantic model named **ForecastMaster Native
OneLake R17.1 - TEST** in the same workspace. It does not apply changes to the
existing semantic model, lakehouse, pipelines, permissions or published report.
The original report ZIP and R17 candidate ZIP remain byte-preserved.

The source tables keep their original Direct Lake partitions. Twenty reporting
metadata helpers become calculated/import tables in the separate candidate.
Only source identities, sectors, source-preference metadata and constant control
tokens are used to construct them. There is no sales-amount query, SQL endpoint,
new Delta table, separate metadata snapshot or new refresh schedule in this step.

Microsoft documents `AzureStorage.DataLake` as the OneLake connector and currently
lists calculated tables referencing Direct Lake as a **preview** modeling
capability. This package deliberately tests it on a separate model. Existing
workspace permissions are used; it does not ask for tenant-admin changes.
Creation acceptance, actual processing and refresh propagation are distinct
receiving gates. [Microsoft Direct Lake development documentation](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-develop).

## Scope and freshness

`onelake_model.py` reuses R17's 41 measures and static control catalogue. It changes
only chart selection to check the chosen RowID/Display independently of the drag
rank. It removes the chart's state-token relationship; table ordering still uses
all 7,560 row-rank tokens in the original state/rows mechanism.

The chart metadata crosses the 36 catalogue entries rather than all 7,560 rank
variants. Each group/scenario therefore needs 82 chart rows (72 S&OP + 10 Demand),
instead of 15,130. For one cycle, 10 drivers and 500 sectors, 1,021 presentation
groups and 11 scenarios would produce 920,942 rows rather than 169,925,030 rows in
the old expanded approach. This is a cardinality calculation, **not a measured
Fabric performance result**. Actual cold/warm behavior remains a receiving gate.

Calculated metadata is processed in the model dependency graph. This avoids a
second independently maintained physical metadata snapshot, but its actual
behavior with OneLake framing and the existing automatic model refresh request
must be tested. This separate TEST model is not connected to the hourly/ad hoc
worker. Do not assume it stays current when the production model refreshes. A
later production installation would need explicit qualification of source-change
propagation using the existing refresh path before becoming acceptable.

The source-preference policy remains Plan ADS > ADS > highest numeric ADS revision
> imported time, within Country/cycle/driver. Exact timestamp ties stay ambiguous.
Scope comes from actual source-revision/sector pairs, including blank tiers.
The source filename scenario parser follows the frozen R17 SQL parser; actual
company file-label/scenario reconciliation remains a gate.

## Local evidence and remaining limits

- Eleven synthetic/mock tests verify additive preservation, source-mode guards,
  duplicate/concurrent-change refusal, creation-only API scope, LRO handling,
  readable delivery and matching Python/notebook code.
- 2,654 checks pass in a local Power BI Analysis Services engine: the existing
  aggregate/leaf numeric oracle, dynamic source parsing/ranking/ties/time zones,
  scope availability and chart selection at different drag ranks.
- All local source facts were fabricated calculated/import tables. These tests
  **do not** demonstrate Direct Lake preview processing, company credentials,
  Desktop/Service rendering, export, native zoom or company performance.

[R17's capability comparison](../report-native-r17/CAPABILITIES-VS-R16.6.md) still
applies. In particular, this source adapter does not resolve the eight recorded
feature gaps or the cross-year/mixed-cutoff/negative-benchmark calculation cases.
R17.1 is a compatibility test candidate, **not a replacement release**.

## Files and reproduction

`build_candidate.py` produces readable `CREATE ONELAKE TEST MODEL.py` and the
single-code-cell notebook `ForecastMaster OneLake Test - CREATE ONLY.ipynb`.
There are no runtime downloads, encoded code blobs, credentials or cached data.
The new model is created through the [documented Fabric create API](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/create-semantic-model).
Item/platform identity is not copied. The original model is never an update API
target. A creation is never retried automatically, and existing TEST names are
refused rather than overwritten. Short receipts contain IDs/counts, not source
connection values or sales amounts.

```bash
python3 handoff/report-native-onelake-r17.1/build_candidate.py
python3 handoff/report-native-onelake-r17.1/tests/check_candidate.py
```

`tests/engine_fixture.py` generates only fabricated source tables. Use the
existing R17 `tests/run_native_engine.ps1` with a task-owned engine port, then
pass its queries-results JSON to `engine_fixture.py --verify`. Keep private
company model definitions and receiving execution caches outside this public
repository. The engine fixture and validation receipt are qualification evidence,
not an office-laptop run result.
