# TEST inherited-feed syntax repair R01

Open [OPEN FIRST.txt](OPEN%20FIRST.txt) on the work laptop. The operator's latest
TEST refresh completed with warnings, with nine inherited FM UI formulas ending
in `displayFolder: Forecast review\Visual feed`. That line belongs to measure
metadata, not DAX. The original getDefinition/copy path preserves incoming TMSL
tables; it does not parse or modify these old expressions. The supplied warnings
confirm invalid expressions in TEST, not when or how production acquired them.
There has been no current inspection or write of production's measures.

`REPAIR TEST FEED.py` is a readable single-cell repair for the exact existing
TEST ID. It moves only that terminal line on nine allowlisted measures in
`fm_review_measures`, preserving the preceding DAX. Unknown shapes or conflicting
metadata are refused. The full pre-repair definition and connection inventory
are backed up and verified in the private company lakehouse. No company
definition is written to this public repository. The REST update uses
`allowPurgeData: false`, compares the model definition on readback, and checks
the cloud mapping before and after. No connection, permission or SSO change is
requested. No explicit refresh, source query, recreation or publication occurs.

The notebook contains identical code with empty outputs. Build and check:

```bash
python3 handoff/report-native-onelake-r17.1/measure-repair-r01/build_notebook.py
python3 handoff/report-native-onelake-r17.1/measure-repair-r01/tests/check_repair.py
```

The tests use synthetic metadata, the existing public feed-formula templates,
and mocked APIs/filesystem. They verify body preservation, exact target scope,
backup refusal, concurrency, idempotency and readback. They do not establish
company execution, a clean refresh, numerical parity or native report acceptance.
R17.1 remains a qualification candidate and all R17 capability gaps still apply.

The old creation script, native model code, original source packages and both
thin-report ZIPs remain unchanged. Do not rerun the completed creation/setup or
modify production to clear a TEST warning.
