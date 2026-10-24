# R17.8 performance work and qualified R03 TEST handoff

Local fabricated work only. Released R02 report/cell, company TEST and production
R16.6 remain unchanged. The user authorized this prototype after reviewing the
local 12–16 second expanded Executive Summary timings.

The selected R03 candidate is `strictcells.py` over `cells.py`: compute a
cell's Plan and Benchmark once, then derive its variance and percentage. It
changes two expressions only; no table, relationship, source, amount kernel,
period, cutoff, colour or format definition changes. Initial native parity and
speed, mixed regression, repeated comparisons and actual Desktop/export/reopen
checks are closed for their declared local scope. Company gates remain open.
The same 20-file/two-cycle/five-driver/30-sector, 504,000-fact sample is used.

Prepared grouping (`prepared.py`), vectorized periods, star/physical serving
tables, source-centered regression moments and the narrow metadata pushdown
were not selected: checked values matched but latency did not improve. Their
source and rejected receipts are retained for diagnosis, not deployment.
`decompose.py` and `guard_cost.py` contain intentionally simplified diagnostics;
their constant/removed guards are never acceptable report candidates.

`probe.py` freezes each NEW run directory, queries both models, and compares
every result set including native values, formats, colours and row populations.
`run_profile.ps1` uses one task-owned calculated-only native engine, requests
native QueryEnd/storage/plan/execution-metric events and closes the engine in
`finally`. It never attaches to an existing Desktop or company connection.
Only QueryEnd/storage events have been observed. Inputs are hashed before
launch; per-query checkpoints are immutable. Empty outputs cannot pass parity.
`regression.py` reuses the exact independent 75-query/11,592-cell mixed-period
population; `benchmark.py` alternates baseline/candidate order and checks scalar
zero/negative/blank boundaries. Repeated timings are descriptive, not p95 proof.
`prepare_desktop.py` creates a new fabricated sample for native inspection.

The new guarded TEST handoff is in `receiving-r03/OPEN FIRST.txt`; use it directly
instead of R02. This is not a Direct Lake benchmark or an Import-vs-Direct Lake
A/B result. No company serving-layer change is installed. Preserve failed attempts separately; do not
modify bound code/inputs during a run or infer a warm cache from query order.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 handoff/report-native-only-r17.8/performance-r01/test_prepared.py
PYTHONDONTWRITEBYTECODE=1 python3 handoff/report-native-only-r17.8/performance-r01/probe.py build NEW_DIRECTORY PATH_TO_FROZEN_SAMPLE05 strictcells
PYTHONDONTWRITEBYTECODE=1 python3 handoff/report-native-only-r17.8/performance-r01/probe.py verify RUN_DIRECTORY
```

Only closed source-bound results belong in a qualification receipt. The R03
cell is locally qualified; company installation is pending. The existing
UNDERSTANDING.md and feedback/STATUS.md remain the current project checkpoint;
do not create a parallel understanding/status ledger here.

Controlled median server milliseconds (three alternated pairs/context): full
Market 10,133→5,994; full Share 13,791→7,854; five-driver Executive 6,388→3,493;
Review 2,817→1,588. Twelve paired complete result sets match. Initial boundary
test setup failed in the timing run; corrected independent boundary and exact
receiving checks pass separately (93 queries). See their distinct receipts.
75 mixed queries / 11,592 cells, 1,500 native formatted Share export cells,
five mock tests and 41 schema documents pass. These counts describe specific
tests, not broad company/Excel acceptance.

Expanded Share in actual Desktop remains about 9.7s DAX / 11.0s total. The
near-instant objective is open; no p95/company speed result is claimed. The
final report-local colour-reuse pilot matched values/colours but was slower and
is rejected. All task-owned Desktop windows and engines were closed.
