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
