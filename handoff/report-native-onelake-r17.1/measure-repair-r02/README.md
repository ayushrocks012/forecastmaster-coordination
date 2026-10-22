# TEST feed repair R02: complete backup readback

Continue with [OPEN FIRST.txt](OPEN%20FIRST.txt). The operator's R01 run raised
`Private backup verification failed; no model write` before reaching its model
update. That establishes a failed comparison, not backup corruption or a
confirmed preview-size limit: the returned length/content was not captured.

The prior code used `notebookutils.fs.head`, a preview API with a requested
maximum byte count. R02 uses the [documented full-file copy API](https://learn.microsoft.com/en-us/fabric/data-engineering/notebookutils/notebookutils-file-system#copy-file)
to read each newly written company backup into a private temporary directory on
the Fabric driver. It verifies the byte count and SHA-256 of the complete UTF-8
file, then removes the temporary copy. The cloud backup stays in the company
lakehouse. It checks write/copy return values and permits three bounded readback
attempts for transient behavior, never reissuing a backup write or model update.
Persistent mismatch still refuses model writes and reports sizes/path only.

The nine-measure suffix repair and all model/connection preservation checks are
retained. Production is never an update target, no source amount is queried, no
explicit refresh/publication is requested, and purge remains disabled. R01's
files and all preceding model/report packages remain byte-preserved. R02 creates
a fresh `Native-R171-Feed-R02/<timestamp-uuid>` company backup folder and leaves
the partial earlier backup untouched.

Reproduce locally:

```bash
python3 -B handoff/report-native-onelake-r17.1/measure-repair-r02/build_notebook.py
python3 -B handoff/report-native-onelake-r17.1/measure-repair-r02/tests/check_repair.py
```

Twenty-three synthetic/mock tests pass. The added cases cover UTF-8 files larger
than 100 KiB, truncated and same-length corrupt copies, failed writes/copies,
bounded transient read recovery and temporary-file cleanup. The original nineteen
preservation/API tests are retained. No actual mismatch cause is inferred from
these simulations. Company full-file verification, repair and clean refresh
remain pending. R17.1's native feature and calculation gaps remain unchanged.
