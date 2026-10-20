# ForecastMaster coordination

A separate repository for exchanging ForecastMaster setup scripts, office-laptop screenshots, and run output. Start with [START-HERE.md](START-HERE.md).

This repository is public. Files and screenshots committed here are publicly visible.

- Current notebook updater: [INSTALL NOTEBOOK R05.3.txt](handoff/notebook-r05.3/INSTALL%20NOTEBOOK%20R05.3.txt)
- Published function source: [ForecastMaster-Actions-R05-2.txt](handoff/functions-r05.2/ForecastMaster-Actions-R05-2.txt)
- Company setup state: [feedback/STATUS.md](feedback/STATUS.md)
- Screenshot exchange: [feedback/screenshots](feedback/screenshots)
- Text output exchange: [feedback/logs](feedback/logs)

This is an independent Git repository, with its own history and `main` branch. It is not a fork or checkout of Smart Demand Manager. The handoff folder contains the selected, previously prepared script package; no application working tree, master workbooks, or source bridge files were copied.

R05.3 passed 126 local unit tests and one local Spark/Delta integration test. Company installation, the first automatic refresh, and the unchanged-run skip test are still pending. The native on-demand button pathway is also pending.

If Python is already available, `python tools/verify_handoff.py` verifies the copied handoff files against their recorded hashes. Python is not required to clone the repository, copy the installer into Fabric, or exchange screenshots.
