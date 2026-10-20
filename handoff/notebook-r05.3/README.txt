ForecastMaster hourly notebook update R05.3

NEXT ON COMPANY LAPTOP
1. Keep ForecastMaster_Hourly unscheduled; pause ForecastMaster_Controller while installing. Let active runs finish.
2. Open the existing ForecastMaster_Refresh, keep its pinned ForecastMaster lakehouse, and connect using PySpark (Python).
3. Add one Code cell immediately below the heading. Paste INSTALL NOTEBOOK R05.3.txt and run THIS cell only.
4. Wait for UPDATED. The installer stops the current execution. Close the notebook editor without saving its old contents; reopen the same workspace item and check R05.3 in the heading.
5. Stop here and confirm the heading. The pipeline Notebook activity and its parameters still need to be connected and company-tested.

PIPELINE SETTINGS FOR THE NEXT GUIDED STEP
Notebook: ForecastMaster_Refresh, existing item e2e0952d-4317-4936-bf0f-2c34698371dc
True branch of Refresh_only_when_changed; False remains empty.
FM_RUN_MODE (String): HOURLY
FM_METADATA_JSON (String, dynamic): @activity('Check_Demand_Metadata').output.output
The output above is already a JSON string; do not use the whole activity wrapper or convert it twice.

BEHAVIOR
Default REQUESTS mode preserves ForecastMaster_Controller and the existing SharePoint button queue.
HOURLY mode accepts the complete published function result, rechecks it under the existing exclusive worker.lock, and processes all matching paths while forcing a content hash only for files changed by size, modification time or SharePoint ETag.
The first successful baseline checks all admitted file contents once; same SHA256 content is reused without creating another report scenario. Later unchanged gates skip the notebook. A full metadata inventory is retained so deletions and renames are detected.
A source path remains one scenario. The reader, catalog, reporting, confirmed model refresh, ordered run and request worker modules are preserved byte for byte (PRESERVATION.json). Existing file identity and retention functions are unchanged; fast_refresh.py adds per-path content checks and retains its discovery metadata.
Only successful ingestion, reporting, model confirmation/UNCHANGED, retention and matching source inventory can advance Files/ForecastMasterRefreshState/metadata-success.json. Each baseline is retained separately under metadata-baselines/.
If a file changes between gate and ingestion, the run fails without advancing that baseline. If another worker owns the lease, the hourly job fails for retry; it does not run a competing writer. The existing intentional operator recovery rules for an interrupted infinite lease remain in force.

CAPACITY AND QUALIFICATION
No Fabric calls run during local packaging. This installer updates the existing notebook definition and retains its complete prior definition under Files/ForecastMasterRefreshState/upgrades/r053-<timestamp>.json. It does not run ingestion, change schedules, create another notebook, change the report or alter source workbooks.
The published metadata function still scans the full Demand folder tree. Its measured company scan was about 51 seconds; function and pipeline executions consume capacity. Only the idle Spark/model work is avoided.
A successful company hourly run and a second unchanged metadata check are required before scheduling daily, including weekends, 08:00-17:00 Europe/London.
The native prompt on-demand button/event pipeline remains a separate pending step.

RECOVERY
Use the printed full backup path to recover the prior notebook definition. All prior working sources and notebook backups remain available. If reopening does not show R05.3, leave the hourly pipeline unscheduled and return the installer output.
