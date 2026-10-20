# Hourly pipeline: use the existing user's execution context

This is the next company test after notebook-launch errors 2011 and 2461. The
metadata function succeeded. The explicit Notebook connection selected in the
True branch invoked Workspace Identity; that route depends on tenant settings
the operator cannot access. The operator requires a solution using existing
permissions, with no IT request, new app registration, or tenant-setting change.

Microsoft documents that a pipeline notebook runs as the pipeline's last
modified user. Its pipeline definition schema makes a TridentNotebook
activity's `externalReferences` connection optional. This setup cell updates
the existing pipeline with the signed-in user's token and omits that optional
reference. The company run must still prove that this works in the tenant.

## Receiving steps

1. In VS Code, open the coordination repository's terminal and run
   `git pull --ff-only`.
2. Save and close the `ForecastMaster_Hourly` editor tab. Let any active run
   finish; keep the hourly and old controller schedules paused during setup.
3. Open [SET HOURLY USER CONTEXT.txt](SET%20HOURLY%20USER%20CONTEXT.txt) in VS Code.
   Press Ctrl+A, then Ctrl+C.
4. In the Fabric workspace **UK-ANI-Demand**, select **New item > Notebook**.
   Name this separate notebook **ForecastMaster_Pipeline_Setup** and use the
   **PySpark (Python)** language. It is a setup notebook with no schedule.
5. Paste the complete text into its first code cell. Use that cell's triangle
   to run it. The cell uses the existing user's Fabric and OneLake tokens; it
   needs no manually entered credentials or Lakehouse attachment.
6. Retain the output. A successful update includes a verified backup path and:
   `UPDATED: ForecastMaster_Hourly - explicit notebook connection removed and read back.`
   An `ALREADY SET` result means the saved activity already omits the reference.
7. After success, reopen **ForecastMaster_Hourly** from the workspace. Run one
   manual test. Opening and using Run history lets you observe the saved
   pipeline; do not select the old Workspace Identity connection again. If
   the editor requires a connection or refuses the run, retain that exact
   message for the next diagnostic step.

Run the setup in its own notebook. Adding this cell to the maintained
`ForecastMaster_Refresh` notebook would insert setup and exit code ahead of
the refresh worker. The maintained worker remains R05.4.

## Exact scope and recovery

The cell discovers exactly one `ForecastMaster_Hourly` DataPipeline in the
known workspace. It requires exactly one `Run_ForecastMaster_Hourly` notebook
activity inside `Refresh_only_when_changed`'s True branch, the maintained
notebook/workspace IDs, `FM_RUN_MODE=HOURLY` (case insensitive), and the exact
metadata expression `@activity('Check_Demand_Metadata').output.output`.

Before updating, it saves the full original definition under the existing
ForecastMaster Lakehouse's `Files/ForecastMasterRefreshState/upgrades/` and
reads the backup back. It rereads the pipeline immediately before the update
to detect another editor's changes. The API provides no compare-and-swap
precondition here; keep other editors closed until setup completes.

Only the target notebook activity's `externalReferences` object is omitted.
The update preserves the metadata function's connection, all notebook
parameters, branches, policies, other content, and original definition parts.
The pipeline ID and worker notebook ID stay the same. The previous connection
ID remains in the retained backup. It does not edit or remove the connection
item, workspace identity, access grants, source files, model, notebook worker,
or schedules. It never launches a job.

The cell reads back the complete saved definition and rejects unexpected
changes. An error after the update was submitted does not prove that the
update failed: keep the backup and output and inspect the saved definition
before retrying. A readback failure is never printed as success. Do not paste
the full backup JSON into the notebook as executable code.

## Evidence and limits

Local synthetic tests execute the exact copy/paste cell, check the one-field
change, verified backup before update, unique item discovery, preserved
parameters and metadata connection, API failures, asynchronous operations,
concurrent edits, idempotence, and readback failure. They do not contact the
company tenant. See [VALIDATION.json](VALIDATION.json).

The repository's GitNexus quick graph returned `ACTIONABLE_PARTIAL` with no
complete reference coverage. Direct source inspection and focused tests
support this isolated new helper; complete graph impact remains unknown.

The first successful company notebook execution, baseline, unchanged-run skip,
semantic-model confirmation, and scheduled execution remain pending. A
successful definition update alone does not qualify the hourly refresh.

Official references, read on 20 October 2026:

- [Notebook execution context](https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook#security-context-of-running-notebook)
- [Optional TridentNotebook connection reference](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/datapipeline-definition#tridentnotebook-activity-properties)
- [Get Item Definition](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/get-item-definition)
- [Update Item Definition](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/update-item-definition)
- [Long-running operations](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation)
