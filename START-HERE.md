# Current report step - native-only R17.7 speed and file selection, 23 October 2026

Current receiving step: [R17.7 labels, checkboxes and DAX optimization](handoff/report-native-only-r17.7/OPEN%20FIRST%20-%20R17.7.txt).
R17.6 screenshots show loading summaries/variance columns. Reported DAX times
are 26.2s graph, 17.4s Review Summary and 4.7s Executive Summary. R17.7 adds
compact labelled controls, native series end labels, imported UTC timestamps,
searchable file checkboxes without Ctrl, and Apply filters batching. It reuses
regression coefficients and narrows monthly fact projection; the graph's value
filter moves into its value measure with the same admission check.

Pull Coordination and run ONE NEW R17.7 cell in ForecastMaster_GM_Setup. Before
any model write it compares 72 old/candidate aggregate results privately through
read-only virtual DAX measures. Failed/unavailable/incomplete/uninformative
checks refuse a write; send the result instead of changing tenant settings.
Require TEST_R177_UPDATED, then refresh ONLY existing R17.1 TEST ONCE for new
metadata columns. After Completed without warnings, extract/open the NEW R17.7
TEST ZIP. Company post-change timings/rendering/selection/export and broader
numerical acceptance remain pending. Local/schema/mock/algebra checks are not
company DAX execution. All visuals remain native. Keep older folders/backups
and production R16.6. SAMPLE is fabricated. Original setup instructions follow.

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
