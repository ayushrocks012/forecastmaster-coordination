# Guarded R17.8 R02 TEST handoff

Follow [OPEN FIRST.txt](OPEN%20FIRST.txt). The runnable artifact is
[INSTALL AND PREPARE PRIVATE TEST R02.py](INSTALL%20AND%20PREPARE%20PRIVATE%20TEST%20R02.py).
Run only that whole file in one new company setup cell, once. The cell generates
the private report with real explicit ADS defaults; `REPORT TEMPLATE.zip` is a
maintainer input and must never be opened as the receiving report.

The TEST adapter changes 15 guarded selection/admission/cell-evaluation
expressions and two dynamic summary display definitions. Numeric amount kernels,
tables, dates, relationships and cloud mapping stay unchanged. It checks the
exact known private installed R01 before writing, performs 24 paired scalar
comparisons and three empty-file checks, verifies full private backups, writes a
sticky attempt before one update, then verifies metadata/cloud/date/default and
24 scalar plus three blank readbacks. No refresh or publication is submitted.
The report uses the SAMPLE05 layout and packaged single custom overlay, with
all controls/summaries/file selection native. Company custom-visual admission,
UI/business acceptance and speed remain open. No tenant-admin workaround is
part of this package.

[VALIDATION.json](VALIDATION.json) binds the exact generated cell and local
mock/schema proofs. [VALIDATION-NATIVE-QUERIES.json](VALIDATION-NATIVE-QUERIES.json)
binds all 51 exact receiving-query executions on the fabricated native engine.
Failed standalone attempt01 is preserved separately: a Desktop host metadata
hint requested MEngineHelper before any query. Attempt02 removes only that host
hint and records the adaptation. The cell itself is unchanged by that harness
fix. Engines and Desktop windows were closed after qualification.

Maintainers can reproduce the cell from the frozen pre-native SAMPLE05 archive:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 handoff/report-native-only-r17.8/ui-correction-r02/receiving-r01/build_cell.py PATH_TO_SAMPLE05_SCHEMA_CANDIDATE_ZIP
PYTHONDONTWRITEBYTECODE=1 python3 handoff/report-native-only-r17.8/ui-correction-r02/receiving-r01/test_receiving.py
```

Use a NEW directory for native_cases.py build; never overwrite a prior run.
Keep actual company default labels, backups, downloaded ZIPs and values private.
No company or production call was made during this local qualification.
