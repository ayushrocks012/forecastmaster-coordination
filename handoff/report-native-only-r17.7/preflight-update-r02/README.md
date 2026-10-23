# R17.7 updater R02 — sequential numerical preflight

[Company-laptop steps](OPEN%20FIRST%20-%20R02.txt).

On 23 October 2026 the operator's R01 diagnostic returned four NUMERIC baseline
reads: Plan 921ms, Benchmark 1989ms, VariancePercent 3716ms and FutureTrend 928ms.
Scope metadata took 10856ms; the earlier exception context was unavailable.
These are separate diagnostic reads, not report timings or candidate results.
They do not prove why the earlier 72-value baseline UNION failed. R17.7 was
not installed by either the failed updater or read-only diagnostic.

R02 keeps the exact frozen R17.7 metadata patch and numeric virtual overrides.
It changes the preflight execution shape to one scalar per read-only query.
Every original CALCULATE/filter expression is tested against the corresponding
member of the frozen batch: three metrics (Market/Ex-factory/Share), three
windows (6/12/24M), two years, and Plan/Benchmark/Variance %/December Trend
Monthly. There are 72 pairs, or 144 sequential scalar reads. Each original is
immediately followed by its candidate. There is no retry, parallel read or
reduction of comparison coverage. This can take several minutes.

None/NaN represent blank; numeric zero remains numeric. Finite numbers retain
the original rel_tol=1e-9/abs_tol=1e-6 comparison. Incomplete, nonnumeric,
infinite, mismatching and uninformative results block the write. The original
requirements for numeric benchmark and next-year trend observations remain.
Counts by metric expose matching blanks without printing amount values.

The same source metadata discovery chooses an available ADS scope. An additional
private read of that scope's revision/priority/rank/tie metadata is compared
before and after the serial checks; changed selection metadata refuses a write.
This is a selection-metadata guard, not a transaction across the source facts.
The existing final definition and connection concurrency checks still apply.

Virtual measure definitions last only for their read-only DAX query. Candidate
performance overrides intentionally require no new helper columns: they execute
against the existing R17.6 model. Native file-choice and presentation additions
remain part of the unchanged final patch, with receiving UI/selection gates.
See [Microsoft DEFINE behavior](https://learn.microsoft.com/en-us/dax/define-statement-dax)
and [SemPy evaluate_dax](https://learn.microsoft.com/en-us/python/api/semantic-link-sempy/sempy.fabric?view=semantic-link-python).

A preflight failure returns TEST_R177_PREFLIGHT_STOPPED with its comparison
checkpoint and allowlisted error details. It performs no model or backup write
and prints no raw exception, query, source identity or amount. No tenant/admin
change is requested. Other identity/backup/write/readback errors keep the prior
fail-closed behavior; never repeat an ambiguous write.

After preflight passes, the unchanged patch, private full-file verification,
cloud mapping, concurrency, no-purge update and full readback operate as before.
Backups use Native-R177-Performance-Files-R02. Success is TEST_R177_UPDATED with
UpdaterRevision R02. Then refresh ONLY existing TEST once, require warning-free
Completed, and open the unchanged R17.7 TEST PBIP ZIP. Every other result stops
for review. Production R16.6, original models, source retention, schedules,
connections and all older handoff bytes remain unchanged.

Local guards verify all 72 scalar expressions, frozen patch equivalence,
privacy, no writes on failure, full backups/readback and Python 3.10 syntax.
They do not execute DAX, prove numerical parity or establish speed. No local
or serial-preflight timing is report performance acceptance. Full R16.6 parity,
native rendering/interaction/export and company speed remain receiving gates.
GitNexus cannot resolve Coordination; direct tracing and guard/preservation
checks are bounded fallback, not a complete graph-impact conclusion.
