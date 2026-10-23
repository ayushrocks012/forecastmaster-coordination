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

**Immediate step from the latest screenshot:** the correct history dialog is
open with Scheduled selected. Click **Direct Lake**, the third tab beside
OneDrive, and send that tab's screenshot. If Failed at 23:27 is visible, open
its Show/error details. Its category is still unknown; no refresh is requested.

**Current diagnostic target: read the failed TEST refresh error details.**
The refresh-state R01 result confirms a post-install Completed refresh ending
22:24:33 UTC on 23 October, followed by a newer Failed refresh starting
22:27:57 UTC / 23:27:57 UK. The verifier correctly stops on the newer failure.
The cause is still unknown because the raw error was withheld.
[Reviewed result](feedback/logs/2026-10-23-r178-refresh-state-r01-reviewed.json).

On the company laptop, open [the exact failed refresh](https://app.powerbi.com/groups/f5cb5742-9a7c-4337-a4c0-952706dddf0b/datasets/31d00232-ac03-48fe-af39-f2e4bae82443/refreshdetails/7f24629a-4764-4dee-a712-a17854512b2e).
Expand error details and return its exact code/message, plus Data or Query Cache
phase if shown. If the link is unavailable: UK-ANI-Demand → ForecastMaster Native
OneLake R17.1 - TEST → Refresh → Refresh history → the Failed row at 23:27:57 UK
on 23 October → Show/error details.
[Microsoft instructions](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-data#semantic-model-refresh-history).

**No new notebook cell, installer/verifier/probe retry, refresh/reset, marker
deletion or publication.** Keep backups and completed recovery work unchanged.
Do not skip the newer failure by choosing an older Completed row. Earlier nine
date groups and 12 comparisons remain recorded, not rerun by this history probe.

Built-in visuals only; production R16.6 and older packages remain unchanged.
Local native runtime/context/oracle, schema and receiving safety tests pass.
Final verifier, Desktop rendering/export/business parity and speed remain
receiving gates. Installation and one TEST refresh are complete. SAMPLE is fabricated and cannot validate company figures.
Raw metadata/values/backups remain private; send only counts-only final JSON.

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
