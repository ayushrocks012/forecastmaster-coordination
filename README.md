# ForecastMaster coordination

A separate repository for exchanging ForecastMaster setup scripts, office-laptop screenshots, and run output. Start with [START-HERE.md](START-HERE.md).

This repository is public. Files and screenshots committed here are publicly visible.

- **Design review:** pull this repo and open `design/index.html` in a browser. [Second page — source-only selections R07](design/sop-source-only-r07/README.md) starts with empty graph/table results and requires explicit Channel, source context and Measure choices. Affiliate, Demand cycle, Section and month calendars are available above the shared driver/sector scope. Derived Contracts totals and extra diagnostic measures are removed; Units/Value changes measure labels and Share uses the right axis. [R06](design/sop-cascade-r06/README.md), [R05](design/sop-spaced-groups-r05/README.md), [R04](design/sop-three-column-r04/README.md), [R03](design/sop-channel-table-r03/README.md), [R02](design/sop-side-panel-r02/README.md) and [R01](design/sop-build-up-r01/README.md) remain saved. All prototypes use synthetic data. [R11 — Month Range Review](design/executive-month-review-r11/README.md) is the approved first-page design and remains unchanged. First-page R07–R10 remain preserved; R07 also has the named tag `design-driver-sector-r07`. Live Power BI implementation remains paused.
- [R09 — Executive Period Review](design/executive-period-review-r09/README.md) adds FY/YTG overview comparison and explicit trend-history dates. Its variance table now uses numeric values without the small variance bars, as requested; every number is retained.
- Current notebook updater: [INSTALL NOTEBOOK R05.4.txt](handoff/notebook-r05.4/INSTALL%20NOTEBOOK%20R05.4.txt)
- Current authentication correction: [hourly user context setup](handoff/pipeline-user-context-r01/README.md)
- Original R05.3 handoff: [retained package](handoff/notebook-r05.3/README.txt)
- Current published Functions source: [ForecastMaster-Actions-R06-native.txt](handoff/native-adhoc-r01/ForecastMaster-Actions-R06-native.txt)
- Native ad hoc extension, installed and tested through the company report button:
  [native setup and receiving steps](handoff/native-adhoc-r01/README.md)
- Prepared hourly targeted refresh patch, **not yet installed**: [OPEN THIS FIRST](handoff/hourly-targeted-r01/OPEN%20THIS%20FIRST.txt)
- Prepared report performance update, paused for design review: [R04.2 cycle feed](handoff/report-cycle-cache-r04.2/README.md)
- Company setup state: [feedback/STATUS.md](feedback/STATUS.md)
- Screenshot exchange: [feedback/screenshots](feedback/screenshots)
- Text output exchange: [feedback/logs](feedback/logs)

This is an independent Git repository, with its own history and `main` branch. It is not a fork or checkout of Smart Demand Manager. The handoff folder contains the selected, previously prepared script package; no application working tree, master workbooks, or source bridge files were copied.

R05.4 retains older imported revisions and disables automatic Delta purging while keeping the report's existing current-file selection. Its [README](handoff/notebook-r05.4/README.txt) gives the installation steps; [validation receipt](handoff/notebook-r05.4/VALIDATION.json) records the exact local checks. Receiving evidence on 20 October 2026 confirms a successful hourly refresh with a completed model refresh, followed by an UNCHANGED run that skipped the notebook. The every-day 08:00–17:00 London schedule is saved and active; the first automatic scheduled run remains pending.

The operator cannot access tenant settings and requires no IT involvement. The [user-context correction](handoff/pipeline-user-context-r01/README.md) was installed and its company hourly launch succeeded. The existing SharePoint Refresh Demand button and manually run controller also completed a request successfully. On 21 October 2026, the new **Refresh Demand (native)** report button completed automatic native request processing and model refresh. Two requests were combined into one batch; overlapping duplicate runs recovered through the configured retry and returned the same successful receipt. See the [receiving record](feedback/logs/2026-10-21-native-adhoc-acceptance.json) and latest status section. The first scheduled hourly run remains unverified. Event listeners and duplicate notebook starts consume capacity; published rates are not measured company usage.

Normal ad hoc use: save the source bridge workbook, open the report's **Refresh Demand** page, click **Refresh Demand (native)** once, wait for the automatic pipeline to complete, then reload the report. The button acknowledges submission; it does not wait for the asynchronous model refresh. The operator removed the original Power Automate Run flow button and saved the Service report; the native button is the current report action. Handoff package READMEs and local validation receipts preserve their preparation-time state; `feedback/STATUS.md` owns the latest receiving results.

If Python is already available, `python tools/verify_handoff.py` verifies the copied handoff files against their recorded hashes. Python is not required to clone the repository, copy the installer into Fabric, or exchange screenshots.
