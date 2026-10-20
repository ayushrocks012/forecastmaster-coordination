ForecastMaster notebook correction R05.4

WHAT CHANGED
R05.4 retains every imported content revision in the source history, measures,
calendar, controls, quality, assignments and source receipts. Editing or removing
a source path does not delete its earlier imported values. Automatic Delta
purging is disabled. The report still selects the current version of each saved
file path, so retained history does not add duplicate current scenarios.

The original R05.3 package remains unchanged under handoff/notebook-r05.3.
Retention of additional revisions can increase storage use. This correction
prevents further source-history deletion; it does not restore earlier deletions.

INSTALL ON THE COMPANY LAPTOP
1. Keep ForecastMaster_Hourly unscheduled and ForecastMaster_Controller paused.
   Let active runs finish.
2. In the coordination repository's VS Code terminal, check git status --short,
   then git pull --ff-only. Preserve any local edits if Git reports a conflict.
3. Open handoff/notebook-r05.4/INSTALL NOTEBOOK R05.4.txt and copy all its text.
4. In Fabric > UK-ANI-Demand, open the existing ForecastMaster_Refresh notebook.
   Keep ForecastMaster as the default lakehouse and PySpark (Python) selected.
5. Add a Code cell immediately below the heading, before existing code. Paste
   the installer, then run THIS CELL ONLY using Ctrl+Enter once.
6. Expected output:
   UPDATED: ForecastMaster_Refresh R05.4 (existing notebook ID retained).
   It also prints a backup under Files/ForecastMasterRefreshState/upgrades/.
7. Close the editor without saving old contents over the installed definition.
   Reopen the same notebook from the workspace and confirm R05.4 in its heading.
8. Return the installer output and heading confirmation before the first run.

The installer updates the same maintained notebook ID, preserves its attached
lakehouse metadata, saves the complete prior notebook definition, verifies the
saved code and parameter tags, and releases its writer lease. It does not run
ingestion, change schedules, create a new notebook or change source workbooks.

EXISTING HOURLY PIPELINE SETTINGS
Keep the selected existing connection. Notebook: ForecastMaster_Refresh.
Place the Notebook activity in the True branch of Refresh_only_when_changed.
Keep the False branch empty.
FM_RUN_MODE (String): HOURLY
FM_METADATA_JSON (String, dynamic): @activity('Check_Demand_Metadata').output.output
The metadata output is already a JSON string; pass that exact property without
converting the whole activity wrapper or serializing it a second time.

The default REQUESTS mode and existing button queue remain available. The hourly
function remains R05.2; the R05.4 notebook reports CodeVersion R05.4. Changed-file
hashing, same-content reuse, current report identities, model confirmation,
writer lease, successful baseline commit and unchanged-run skip are preserved.

QUALIFICATION
See VALIDATION.json for local unit, synthetic Spark/Delta, installer and static
checks. No company service is contacted by local testing. Company R05.4 install,
first hourly success, unchanged-run skip and connection permissions remain
receiving-workspace checks. Do not schedule until the company tests pass.

The original legacy-compatibility installer is included as a byte-preserved test
input because the legacy test references it. The R05.4 one-cell installer already
embeds the current decoder; the operator does not run that separate legacy file.
