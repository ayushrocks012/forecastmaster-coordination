# ForecastMaster coordination

A separate repository for exchanging ForecastMaster setup scripts, office-laptop screenshots, and run output. Start with [START-HERE.md](START-HERE.md).

This repository is public. Files and screenshots committed here are publicly visible.

- **Project reference:** [UNDERSTANDING.md](handoff/report-native-only-r17.8/UNDERSTANDING.md) is the maintained project-wide reference: architecture, object IDs, data flow, fields/table grains, public native DAX/relationships/visual bindings, business/design decisions, history and open gaps. Read its resume section after chat compaction. [STATUS](feedback/STATUS.md) owns reviewed company results.

- **Current receiving step:** company verifier R02 returned **TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED**: nine exact date groups, 12 paired comparisons/zero mismatches, eight unique file choices with imports/no hashes, candidate metadata/cloud mapping preserved. [Reviewed success](feedback/logs/2026-10-24-r178-installed-bounded-verification-reviewed.json). **No more setup cell, verifier/probe/installer rerun, reset or manual Fabric refresh.** Open the [compact R17.8 TEST ZIP/PBIP](handoff/report-native-only-r17.8/test-release-r01/candidate/ForecastMaster%20Compact%20Native%20R17.8%20TEST.zip) in company Desktop and follow the [UI/performance steps](START-HERE.md). Native layout/interactions/export, independent business parity and comparable speed remain pending; production R16.6 stays unchanged.

- **Compact native R17.8 TEST R01 prepared:** [OPEN FIRST](handoff/report-native-only-r17.8/test-release-r01/OPEN%20FIRST.txt) and [qualification](handoff/report-native-only-r17.8/test-release-r01/VALIDATION.json). 207 native synthetic queries / 1,868 assertions, 14 receiving/layout tests and 67 schema documents pass. Built-in visuals only; compact controls, one checkbox file list and dynamic external chart heading. Company installation/processing and bounded verifier now pass; native UI/export/business/speed acceptance remains pending. Production R16.6 remains unchanged. Follow the current native Desktop steps above. Do not rerun the old recovery or inventory.

- **Inventory reviewed:** both returned R01 copies match, including complete content/file hashes. All scoped reads completed: 13 visible items; 24 physical tables/269 fields; original model 15 tables/209 fields/47 measures/5 relationships; TEST 39/333/98/12. The [reviewed metadata receipt](feedback/logs/2026-10-23-uk-ani-inventory-r01-reviewed.json) and [understanding document](handoff/report-native-only-r17.8/UNDERSTANDING.md#company-inventory-r01) now contain the verified dictionary, formula mappings and remaining limits. No more inventory cell or refresh is requested. The new R01 receiving handoff above supersedes the earlier preparation-only next step; raw company exports remain private.

- **Earlier date-recovery evidence:** R02 returned `TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED`: all nine date groups match physical storage, guards and 90 internal scalar checks pass, and model/cloud/source metadata stayed preserved. No more reset, manual refresh or R02 rerun. That dated recovery predates the current R17.8 receiving candidate. The [reviewed receipt](feedback/logs/2026-10-23-native-r178-r02-recovery-verified.json) contains the recovery counts; the later R01 receipt supplies the scoped structural inventory. R17.8 R01 adapter/TEST report are now locally qualified and released for receiving qualification; company installation/processing and bounded verification now pass; native UI/business parity/export/speed remain open. Production R16.6 and all frozen packages remain preserved.

- **Design review:** pull this repo and open `design/index.html`. [Both pages — Currency plan review R15](design/currency-plan-review-r15/README.md) offers a simple rate per source currency, with no country or year in the rate editor. **Plan rates** stays visible in both headers, including Units view. Value offers GBP/USD; the conversion model defaults multiple Affiliates to USD and converts each currency before summing. Rates are not prefilled. The [saved checkpoint](design/checkpoints/before-currency-plan-review-r15.json) preserves all 31 [R14](design/plan-rate-review-r14/README.md) files; R13 and all earlier designs remain available in the chooser. The visible illustrative base remains UK/GBP; isolated multi-currency fixtures check future plumbing, not live source binding. Power BI remains unchanged.
- [R09 — Executive Period Review](design/executive-period-review-r09/README.md) adds FY/YTG overview comparison and explicit trend-history dates. Its variance table now uses numeric values without the small variance bars, as requested; every number is retained.
- Current notebook updater: [INSTALL NOTEBOOK R05.4.txt](handoff/notebook-r05.4/INSTALL%20NOTEBOOK%20R05.4.txt)
- Current authentication correction: [hourly user context setup](handoff/pipeline-user-context-r01/README.md)
- Original R05.3 handoff: [retained package](handoff/notebook-r05.3/README.txt)
- Current published Functions source: [ForecastMaster-Actions-R06-native.txt](handoff/native-adhoc-r01/ForecastMaster-Actions-R06-native.txt)
- Native ad hoc extension, installed and tested through the company report button:
  [native setup and receiving steps](handoff/native-adhoc-r01/README.md)
- Prepared hourly targeted refresh patch, **not yet installed**: [OPEN THIS FIRST](handoff/hourly-targeted-r01/OPEN%20THIS%20FIRST.txt); [quicker single-cell updater](handoff/hourly-targeted-r01/quick-install/START%20QUICK%20UPDATE.txt)
- Prepared report performance update, paused for design review: [R04.2 cycle feed](handoff/report-cycle-cache-r04.2/README.md)
- Company setup state: [feedback/STATUS.md](feedback/STATUS.md)
- Screenshot exchange: [feedback/screenshots](feedback/screenshots)
- Text output exchange: [feedback/logs](feedback/logs)

This is an independent Git repository, with its own history and `main` branch. It is not a fork or checkout of Smart Demand Manager. The handoff folder contains the selected, previously prepared script package; no application working tree, master workbooks, or source bridge files were copied.

R05.4 retains older imported revisions and disables automatic Delta purging while keeping the report's existing current-file selection. Its [README](handoff/notebook-r05.4/README.txt) gives the installation steps; [validation receipt](handoff/notebook-r05.4/VALIDATION.json) records the exact local checks. Receiving evidence on 20 October 2026 confirms a successful hourly refresh with a completed model refresh, followed by an UNCHANGED run that skipped the notebook. The every-day 08:00–17:00 London schedule is saved and active; the first automatic scheduled run remains pending.

The operator cannot access tenant settings and requires no IT involvement. The [user-context correction](handoff/pipeline-user-context-r01/README.md) was installed and its company hourly launch succeeded. The existing SharePoint Refresh Demand button and manually run controller also completed a request successfully. On 21 October 2026, the new **Refresh Demand (native)** report button completed automatic native request processing and model refresh. Two requests were combined into one batch; overlapping duplicate runs recovered through the configured retry and returned the same successful receipt. See the [receiving record](feedback/logs/2026-10-21-native-adhoc-acceptance.json) and latest status section. The first scheduled hourly run remains unverified. Event listeners and duplicate notebook starts consume capacity; published rates are not measured company usage.

Normal ad hoc use: save the source bridge workbook, open the report's **Refresh Demand** page, click **Refresh Demand (native)** once, wait for the automatic pipeline to complete, then reload the report. The button acknowledges submission; it does not wait for the asynchronous model refresh. The operator removed the original Power Automate Run flow button and saved the Service report; the native button is the current report action. Handoff package READMEs and local validation receipts preserve their preparation-time state; `feedback/STATUS.md` owns the latest receiving results.

If Python is already available, `python tools/verify_handoff.py` verifies the copied handoff files against their recorded hashes. Python is not required to clone the repository, copy the installer into Fabric, or exchange screenshots.

The same command now checks classified evidence and separate receiving gates in
the existing manifest. [Executable admission rules](handoff/report-native-only-r17.8/UNDERSTANDING.md#executable-admission-and-evidence-reuse)
and local CI prevent unsupported handoff/performance claims from passing those
checks. The new R03 diagnostic candidate is unselected; continue the current
Desktop step above. No new setup cell or refresh is needed for these additions.
