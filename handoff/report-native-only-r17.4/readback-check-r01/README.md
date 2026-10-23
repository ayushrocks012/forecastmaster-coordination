# R17.4 post-update readback check R01

The operator's R17.4 update request ran and then stopped at `received != fixed`.
Its exact private backup was verified before the update. The subsequent cloud
mapping check was not reached. Installation/preservation are therefore
**unconfirmed**, with a write already attempted; another updater run is not the
next step. The cause of the returned-model difference is not established.

Follow [OPEN FIRST - READBACK.txt](OPEN%20FIRST%20-%20READBACK.txt) on the company
laptop. Paste the entire **CHECK R17.4 READBACK.py** into one NEW cell in the
unscheduled **ForecastMaster_GM_Setup** notebook and run that cell only.

This diagnostic reads the exact saved before/candidate/connection snapshots and
the existing TEST. Its API allowlist permits only metadata retrieval, TEST item
identity, TEST connections, and operation-status/result GETs. The `getDefinition`
POST retrieves metadata; it does not update the model. File copies go from the
private backup to temporary local files; there are no private-backup writes.

All 49 known native expression fingerprints and 20 format definitions validate
the backup's repair scope. A restore comparison also checks the rest of the
whole definition, including non-model parts. Full current-definition comparisons
cover all source/security/helper objects and expressions. Two reads of both the
current metadata and connection inventory detect intervening changes; they do
not lock the remote model against subsequent edits.

The probe decodes `model.bim` JSON, so JSON serialization whitespace/key order
alone does not cause a false mismatch. It separately reports the original raw
definition and parsed-model matches. Only measure DAX string-versus-line-array
representations with exactly identical joined text are accepted as equivalent.
It does not trim text or normalize CRLF in that full-definition comparison.
Named arrays align objects for diagnostics; ordering changes still require
review. Added/removed metadata is never silently ignored. A format-only or
repair-field-only match cannot override an unexplained difference elsewhere.

Output contains bounded, sanitized structural paths and difference kinds, plus
match/stability booleans. Public code identifiers are readable; unknown object
names/property keys are hashed. It never prints differing values, definitions,
connection values or API error bodies. Full traversal counts differences even
after the 40-detail output limit. Read/copy/JSON errors produce a safe stopped
result. Send only the printed result in the chat; keep model files private.

`TEST_R174_READBACK_VERIFIED` means the two metadata snapshots were stable,
the complete definition matched under that narrow representation rule and the
cloud mapping matched the backup. It does not prove calculation execution,
Desktop rendering/drill, refresh processing, performance or R16.6 parity.
Other outcomes require review before further action. No updater rerun, refresh,
rollback, connection edit, new model or publication is requested here.

Developer reproduction: `python3 build_probe.py`, then `python3 test_probe.py`.
The standalone cell freezes hashes from the unchanged R17.4 updater; no company
definition or data is embedded. `VALIDATION.json` records local evidence only.
