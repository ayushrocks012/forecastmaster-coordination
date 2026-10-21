# ForecastMaster coordination

A separate repository for exchanging ForecastMaster setup scripts, office-laptop screenshots, and run output. Start with [START-HERE.md](START-HERE.md).

This repository is public. Files and screenshots committed here are publicly visible.

- **Design review:** pull this repo and open `design/index.html`. [Both pages — Plan-rate review R14](design/plan-rate-review-r14/README.md) adds header GBP/USD controls and annual Affiliate plan rates when **Value** is selected. One selected plan-year rate applies to the whole historical/forecast review. Monetary outputs convert once; units, Share, business growth and variance percentages stay independent of FX. Rates are not prefilled. Missing rates leave USD amounts unavailable; numeric zero is retained. The [named before-change checkpoint](design/checkpoints/before-plan-rate-review-r14.json) preserves all of [Connected GM Review R13](design/connected-gm-review-r13/README.md), and every earlier page remains available from the chooser. Shared filters, visible calendars, bridge order, explicit S&OP measure selection, source metadata, compact summaries and independent Hide/Show remain. All prototypes use illustrative data and local selections; official FX storage and actual cross-page source binding are pending. Power BI implementation remains paused.
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
