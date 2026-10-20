# Company setup status

Last confirmed in chat before the office-laptop handoff on 20 October 2026:

- Power BI `ForecastMaster Review`: R04.1 published on the original shared report link.
- `ForecastMaster_Actions`: R05.2 source published; `checkNativeStateR05` returned `NATIVE_STATE_READY` with the test lease released.
- `ForecastMaster_Hourly`: `checkDemandChangesR05` ran successfully, found 8 bridges, and returned `BASELINE_REQUIRED` / `NeedsRefresh: true` without reading workbook contents.
- `Refresh_only_when_changed`: expression saved; True and False branches empty.
- New hourly schedule: off.
- R05.3 notebook: prepared and locally tested, company installation pending.
- Existing `ForecastMaster_Controller` schedule: confirm its current state before the notebook update.

Next: finish SSH/VS Code setup, obtain `handoff/notebook-r05.3/INSTALL NOTEBOOK R05.3.txt`, then resume the one-time notebook update described in its README.

After installation, update this file with the date, action, output filename, observed notebook heading, and any error. The first hourly refresh, unchanged-run skip, every-day 08:00–17:00 schedule, and native on-demand button pathway remain pending.

## Receiving observations on 20 October 2026

- The operator confirmed the coordination repository opened on the Abbott laptop.
- The R05.3 installer photo shows `UPDATED: ForecastMaster_Refresh R05.3 (existing notebook ID retained)` and a saved backup under `Files/ForecastMasterRefreshState/upgrades/`.
- A later photo of the reopened notebook confirms the R05.3 heading and the default `REQUESTS` parameter cell.
- The operator selected an existing connection named `ForecastMaster_Notebook Ayush.goyal` from the OneLake Catalog. Its authentication kind and runtime permissions have not been independently verified.
- The saved hourly pipeline photo shows `Check_Demand_Metadata` connected to `Refresh_only_when_changed`, a Notebook activity in the True branch, an empty False branch, workspace `UK-ANI-Demand`, notebook `ForecastMaster_Refresh`, and string `FM_RUN_MODE=HOURLY`.
- `FM_METADATA_JSON` appears as a dynamic expression beginning `@activity('Check_Demand_Metadata...`; the photo truncates the suffix. Confirm its full value is exactly `@activity('Check_Demand_Metadata').output.output` before the first run.
- No company hourly refresh or unchanged-run skip result has been observed. Schedules were instructed to stay paused; their live toggle state is not visible in these photos.

## R05.4 correction

R05.3's automatic source compaction deletes superseded imported revisions and its maintenance path can vacuum Delta recovery files. The new R05.4 handoff removes those operations. All original R05.3 handoff bytes remain available. Current report selection remains one scenario per saved file path.

Next: receive and install `handoff/notebook-r05.4/INSTALL NOTEBOOK R05.4.txt`, confirm its reopened heading, then verify the saved expression and run one company test with no competing writer. R05.4 company installation and runtime qualification are pending.

## Latest receiving result on 20 October 2026

- The operator reports the R05.4 installer printed the expected success message and the reopened notebook shows R05.4. The installer output was not retained; this milestone is operator-reported.
- The first hourly attempt reached the Notebook activity after `Check_Demand_Metadata` succeeded. Notebook launch failed with code `2011`: `Failed to get Workspace Identity access token ... PowerBIEntityNotFound`.
- The operator then created a workspace identity. The photo shows State `Active`, ID `ab5c0278-357c-4e54-b748-e5d9cdd3c57f`, App ID `d920cd74-bfbc-4438-b39f-0e5a591c48f4`.
- The next Manage access photo confirms the `UK-ANI-Demand` identity has `Contributor` access to the `UK-ANI-Demand` workspace.
- A subsequent manual attempt again passed the metadata check but failed the Notebook activity with code `2461`, failure type `User configuration issue`: `Failed to get workspace details with http error code - 'Unauthorized'`; nested message `The caller is not authenticated to access this resource`, `isRetriable: false`.
- The latest photographed pipeline run ID is `7c8e19de-6614-49f2-80d4-c15fb575a132`. No successful hourly notebook execution, baseline advancement, semantic-model confirmation or unchanged-run skip has been observed.

Previous diagnostic suggestion, superseded by the operator's constraint below: inspect the tenant setting `Service principals can call Fabric public APIs` and confirm that its allowed scope includes this newly created workspace identity. Workspace Admin and Fabric administrator are separate roles. The setting, its group scope, connection binding and permission propagation have not been independently verified. Current notebook code and pipeline parameter values do not need speculative edits for this launch-authentication error. Keep scheduling off until receiving tests pass.

## No IT dependency: current next step on 20 October 2026

The operator cannot access Tenant Settings and explicitly requires a route that needs no IT support. The Workspace Identity route is therefore no longer the selected implementation path. No tenant setting or identity permission change is being requested.

Microsoft's current documentation describes pipeline notebook execution under the pipeline's last modified user, and its definition schema makes the notebook activity's connection reference optional. The new `handoff/pipeline-user-context-r01/SET HOURLY USER CONTEXT.txt` uses the already signed-in user's tokens to save and verify the full existing pipeline definition, omit only `Run_ForecastMaster_Hourly.externalReferences`, and read back the change. It retains the same pipeline/notebook IDs, parameters, metadata function connection, branches and other definition parts. It does not start a refresh or edit schedules, source files, workspace identity or roles.

Local synthetic qualification: 29 tests passed, including execution of the exact pasteable cell. Both new code files passed Ruff's E4/E7/E9/F checks. No company API call was made by local qualification. The GitNexus quick graph returned `ACTIONABLE_PARTIAL`; full graph impact is unknown.

Receiving next step: pull the coordination repository, close the hourly pipeline editor, and run the cell in a separate unscheduled notebook named `ForecastMaster_Pipeline_Setup` in `UK-ANI-Demand`. After a verified update, reopen the saved hourly pipeline and test one manual run. Keep the output and backup path. If the current editor requires an explicit connection again, retain its exact message before choosing another route.

Company installation of this pipeline correction, user-context notebook launch, baseline advancement, semantic-model confirmation, unchanged-run skip, hourly schedule and on-demand button remain pending. Definition update success alone does not establish runtime success.
