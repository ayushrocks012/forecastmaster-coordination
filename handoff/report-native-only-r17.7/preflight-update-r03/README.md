# R17.7 updater R03 — definition-checked variance evidence

[Company-laptop steps](OPEN%20FIRST%20-%20R03.txt).

R02 stopped before backups or any model write on comparison 27: Original,
Ex-factory/6M/current-year/Variance %. Twenty-six comparisons completed; no
mismatch was reported before the query failed. The only recognized error
signal was CANCELLED. The operator is unsure whether Stop was clicked. Neither
memory exhaustion, timeout nor a regression is established by that output.

## Evidence method

The verified R17.6 definitions are exactly:

```dax
N Variance =
VAR _p=[N Plan] VAR _t=[N Benchmark]
RETURN IF(NOT ISBLANK(_p)&&NOT ISBLANK(_t),_p-_t)

N Variance % = DIVIDE([N Variance],ABS([N Benchmark]))
```

R03 first hashes the live definitions against that exact contract, in addition
to the unchanged complete R17.6/R17.7 patch guards. A different or unavailable
contract refuses the preflight before querying. A partially installed new
variance formula also refuses this particular baseline method; no generic
algebra assumption substitutes for verified metadata.

For each metric/window/year, R03 reads baseline Plan and Benchmark and compares
both with actual candidate results. It then calculates the expected baseline
percentage privately as `(Plan - Benchmark) / abs(Benchmark)` and compares it
with a direct query of the actual candidate N Variance %. Either blank input
or zero benchmark yields blank; a real numeric zero result remains numeric.
The baseline December Trend Monthly is still directly queried and compared.

This is 54 direct original scalar reads and 18 derived expectations against
72 actual candidate reads: 72 comparisons across the same three metrics,
three windows and two years. It is **not** 72 successful direct original reads.
The cancelled original N Variance % query is neither rerun nor counted as
executed/passed. Output explicitly states OriginalVariancePercentMeasureExecuted
false, DirectOriginalScalarReads 54, DerivedOriginalVarianceComparisons 18,
ActualCandidateScalarReads 72 and OriginalVarianceFormulaVerified true.
All comparisons start afresh; the prior 26-count receipt is not resumed/reused.

This changes the numerical evidence method to a definition-backed expectation;
it does not prove why the old query was cancelled. Independent expected
arithmetic checks the candidate percentage rather than assuming it from its
own inputs. Python floating arithmetic is subject to the existing relative
1e-9/absolute 1e-6 comparison; mismatch/nonfinite output refuses a write.
Company DAX execution and acceptance remain unverified here.

Microsoft documents [VAR result reuse](https://learn.microsoft.com/en-us/dax/var-dax),
[DIVIDE's blank alternate](https://learn.microsoft.com/en-us/dax/divide-function-dax)
and [query-scoped measure definitions](https://learn.microsoft.com/en-us/dax/define-statement-dax).
The old variance chain references Benchmark in both the numerator chain and
denominator. That is a possible source of redundant work, not a demonstrated
root cause or execution profile. R03's independent expectation avoids that
combined baseline query; no performance improvement is promised.

## Preserved boundary and receiving gates

All candidate expressions, model patch constants, helper changes, formats,
roles, source contracts and native report ZIPs remain identical to R17.7/R02.
The source-selection snapshot, informative benchmark/future trend, blank/zero,
completeness, finite-value and tolerance guards remain. Cancellation or any
other query failure stops with safe checkpoint and elapsed time. There is no
retry, error-to-zero, relaxed tolerance, reduced scenario set or capacity change.

Only after success are private backups under Native-R177-Performance-Files-R03
verified, definition/cloud concurrency checked, the no-purge update made once,
and full readback/cloud mapping compared. Production and the refresh worker
remain untouched. R03 never requests refresh or publication. Return the final
JSON even for TEST_R177_UPDATED; do not refresh/open R17.7 until the explicit
direct/derived evidence and readback are reviewed. Older R02 refresh-on-success
instructions do not apply to this handoff step.

Local tests cover strict live-definition checks, blank/zero/sign arithmetic,
real candidate variance mismatches, read-only query counts/privacy, cancellation
and model/backup/readback guards. They do not execute DAX or qualify company
speed, full R16.6 parity, UI or exports. GitNexus cannot resolve Coordination;
direct source/AST tracing and guarded preservation tests are bounded fallback.
