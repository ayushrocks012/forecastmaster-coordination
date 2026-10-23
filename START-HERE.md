# Project reference and current report state

Read [UNDERSTANDING.md](handoff/report-native-only-r17.8/UNDERSTANDING.md)
when resuming this work, including after chat compaction. It is the single
maintained project-wide reference for architecture, known objects, data flow,
fields/grains, public native DAX/relationships/visual mappings, business/design
rules, decisions/history, evidence and open questions. Start with its resume
section; load only the detailed appendix needed for the current work.

The latest company R02 result was reviewed:
**TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED**. The existing clear and one
missing full are completed; all nine date groups agree exactly with physical
storage, guards pass and all 90 bounded private scalar checks pass. Complete
model definition/cloud mapping and metadata dependencies were preserved.
See [STATUS](feedback/STATUS.md) and the linked receiving receipt.

**Do not rerun R02/reset, delete markers or manually refresh again for this
recovery.** Keep the private backup. You may reopen the unchanged R17.7 TEST
PBIP to inspect restored captions/numbers; it is a UI check, not installation.
The later R01 inventory is reviewed: 13 visible workspace items, 24 physical
tables/269 fields, original model 15 tables/209 fields/47 measures/5 relationships,
and TEST 39/333/98/12. Both attachments and complete hashes/byte length agree.
See the [verified inventory](handoff/report-native-only-r17.8/UNDERSTANDING.md#company-inventory-r01)
and [safe reviewed receipt](feedback/logs/2026-10-23-uk-ani-inventory-r01-reviewed.json).

**Model installation and bounded verification PASSED.** The operator returned
TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED / VerifierRevision R02:
nine exact date groups, 12 paired comparisons with zero mismatches, eight unique
file choices with import timestamps/no hash suffixes, candidate metadata and cloud
mapping preserved. [Reviewed result](feedback/logs/2026-10-24-r178-installed-bounded-verification-reviewed.json).
No new notebook cell, verifier/installer rerun, reset or Fabric refresh is needed.

**Current action: repair the rejected native UI first.** The subsequent seven
Desktop screenshots show failures described in the
[maintained resume](handoff/report-native-only-r17.8/UNDERSTANDING.md#resume-in-one-minute).
No new company cell, refresh or repeat of the steps below is requested. The
personal-laptop Desktop is open, but Computer Use fails before connecting from
this WSL chat. Try the app's Windows-native **agent** mode and restart; choosing
PowerShell only as the integrated terminal does not switch the agent. Native
rendering is not yet inspected here and this environment remedy is unverified.
ADS files visibly selected by default and empty selection = no business values
now supersedes the old clear-to-Automatic behavior; no corrected build is ready.

**Historical receiving instructions — already exercised and rejected:**

1. Close the old TEST report. Download/use
   [ForecastMaster Compact Native R17.8 TEST.zip](handoff/report-native-only-r17.8/test-release-r01/candidate/ForecastMaster%20Compact%20Native%20R17.8%20TEST.zip).
   Extract ALL its contents to a NEW folder. SAMPLE is fabricated, not company data.
2. Open ForecastMaster Compact Native R17.8 TEST.pbip from that extracted folder
   in Power BI Desktop. Keep its Report folder beside it.
3. First check an available UK/2026-10 Market/Units Total selection. Send screenshots
   of top filters/Review Summary, graph, Executive Summary and saved-file selector.
   If a visual fails, copy its exact error details and current selections.
4. If that slice works, check Sectors; change Section then Measure; Start/End month;
   single Review/graph trend independently of multiple Executive Table trends;
   driver→sector drill/expand; and several file checkboxes without Ctrl, then clear
   back to Automatic ADS (historical R01 behavior, now explicitly rejected).
   Two alternate versions must not sum into a false total.
5. In Desktop: Optimize → Performance Analyzer → Start recording → Refresh visuals.
   Record DAX query and total duration for monthly graph, Review Summary and
   Executive Summary. State Total/Sectors, filters and first/repeated-load conditions.
   This refreshes report visuals, not the Fabric semantic model. Do not use model
   Refresh or clear caches. [Microsoft guide](https://learn.microsoft.com/en-us/power-bi/create-reports/performance-analyzer).
   Send screenshots and timings; amounts/definitions remain outside the public repo.

This passes only the declared bounded model checks; native UI/export, independent
business parity and comparable speed remain separate. No publication/replacement
of production R16.6. Keep built-in visuals and private backups unchanged.

Original company-laptop connection setup follows for reference.

# Connect the Abbott laptop using VS Code and SSH

Use the GitHub account `ayushrocks012`. Open **VS Code → Terminal → New Terminal** and choose **PowerShell** from the terminal profile dropdown. These steps use a laptop-specific SSH key and repository-local Git settings; they do not need the Windows ssh-agent service or an elevated terminal.

## 1. Check the commands

Run:

```powershell
git --version
ssh -V
```

If either command is unavailable, send that exact message in the chat before continuing.

## 2. Create a key for this laptop

Open [setup/1-create-ssh-key.txt](setup/1-create-ssh-key.txt), click **Raw**, and copy its contents into the PowerShell terminal. It creates a new named key only if that file does not already exist, and copies its **public key** to the clipboard. Follow ssh-keygen's prompts.

The `.pub` file is the public key. The key without `.pub` is the SSH credential and stays on this laptop, outside this repository.

## 3. Add the public key to GitHub

In the browser, sign in as **ayushrocks012** and open [GitHub SSH keys](https://github.com/settings/keys).

Select **New SSH key**. Set Title to **Abbott laptop - ForecastMaster**, keep **Authentication Key**, paste the clipboard contents into **Key**, then select **Add SSH key**. See [GitHub's key setup instructions](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).

## 4. Test the SSH connection

In the same PowerShell terminal, run:

```powershell
ssh -T -i "$env:USERPROFILE\.ssh\id_ed25519_forecastmaster" -o IdentitiesOnly=yes git@github.com
```

On the first connection, SSH may ask whether to trust GitHub's host key. Compare the displayed fingerprint with [GitHub's official fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints), then answer the prompt. The Ed25519 fingerprint recorded on 20 October 2026 is:

```text
SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU
```

Expected response:

```text
Hi ayushrocks012! You've successfully authenticated, but GitHub does not provide shell access.
```

GitHub returns exit code 1 for this successful shell-access test; the greeting confirms authentication. A different error should be returned to the chat. See [GitHub's connection test](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection).

## 5. Clone and open the repository

Open [setup/2-clone-with-ssh.txt](setup/2-clone-with-ssh.txt), select **Raw**, and paste it into the PowerShell terminal. It clones into:

```text
C:\Users\YOUR-WINDOWS-USER\source\forecastmaster-coordination
```

It configures the selected SSH executable and key only for this repository and opens the folder in VS Code. If the `code` command is unavailable, use **File → Open Folder** and select the path printed by the script.

The installer is then available in VS Code at:

```text
handoff\notebook-r05.4\INSTALL NOTEBOOK R05.4.txt
```

Copy that entire file when we resume the Fabric installation. The current installer changes the existing `ForecastMaster_Refresh` item and saves a backup; it does not start ingestion or enable a schedule. R05.4 preserves imported revisions and disables automatic Delta purging. The original R05.3 package remains available; use R05.4 for the next installation.

## 6. Exchange updates and screenshots

Before receiving a new script handoff, run in this repository's terminal:

```powershell
git status --short
git pull --ff-only
```

Save screenshots in `feedback/screenshots/` and text output in `feedback/logs/`. Update `feedback/STATUS.md` with what you ran and the result. Filenames such as `2026-10-20-hourly-output.png` make it clear which run they belong to.

To send those feedback files, open [setup/3-send-feedback.txt](setup/3-send-feedback.txt), select **Raw**, and paste its contents into the terminal. It stages only the feedback folder, commits it, pushes `main`, and prints the commit ID. Tell me that ID in this chat so I can fetch the new output.

You can also use GitHub's **Add file → Upload files** inside the feedback folder. Afterwards, run `git pull --ff-only` in VS Code to receive that web upload.

Commit your feedback before receiving edits to those same files from the other side. If Git reports a conflict or refuses a command, return its message; these scripts do not reset or discard local work.

All files in this repository, including uploaded screenshots and logs, are public. This repository does not start Fabric jobs, schedule background synchronization, or change the original application repository.
