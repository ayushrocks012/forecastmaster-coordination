# Compact native R17.8 TEST — R01

This release implements the user's compact Demand page and matching TEST-only
selection adapter against the reviewed UK-ANI-Demand R01 dictionary. Start with
[OPEN FIRST](OPEN%20FIRST.txt). Company installation, rendering, business acceptance
and speed remain receiving gates; production R16.6 is preserved.

The report is 1440 × 1330, with 26 built-in visuals. Section and Measure remain
separate. Start/End dropdowns use the existing monthly dictionary. Review trend
(single), View and Table trends (multiple) have short visible labels beside
compact controls. The dynamic measure title occupies a heading band outside the
plot. Native scope-first legends/end labels and solid actual, dashed forecast,
dotted trend styles remain; both axis sliders and redundant titles are off.
Native Executive drill/expand retains Plan and absolute/percentage comparisons.
Its fixed-height container uses scrolling/Focus; expanding rows cannot resize
Power BI's page automatically.

One searchable checkbox list selects saved files without Ctrl, with filename and
UTC import timestamp. The model's existing ImportedAtUTC sort key provides newest
imports first; labels use a short v1/v2 suffix only when filename plus displayed
second collide. No raw source hash is displayed. Missing timestamps explicitly
say unavailable. Clearing actual file selection restores Automatic ADS. There
is no separate Source selection or Apply button and no duplicate file table.
Alternative versions remain separate source scenarios and cannot inflate totals.
A metadata-only file-availability filter keeps the list within affiliate/cycle/
driver context. Heavy visuals have no external measure-value filter.

`model.py` changes only the native selection/metadata expression sites and adds
one hidden metadata availability measure. Original source tables, roles,
relationships, connection metadata, arithmetic and numeric formats are preserved.
The live inventory's string/line-array DAX serialization is accepted only when
texts agree. The installer pins the exact reviewed TEST BIM digest and validates
all 51 prior native definitions/formats; unrelated metadata is never copied from
SAMPLE into the company model. The expected TEST becomes 99 measures after the
one added helper, retaining 39 tables and 12 relationships.

Installation performs 12 paired, one-scalar-per-query preflight checks against
virtual candidate formulas, source/date and quiet-processing checks, full UTF-8
SHA256/length private backup and immediate concurrency rechecks. A write-once
private intent precedes one updateDefinition POST. Transport/status retries are
disabled using the documented [SemPy retry configuration](https://learn.microsoft.com/en-us/python/api/semantic-link-sempy/sempy.fabric.fabricrestclient).
Unknown outcomes require receipt review, never another submission. Whole-document
readback normalizes identical expression line arrays only. Purging is disabled.

After the single manual TEST refresh, the read-only verifier requires a new
Completed refresh and compares the installed whole model/cloud mapping with the
private candidate, validates date sets and labels, and performs 12 paired scalar
comparisons against original formulas held privately. Values are neither printed
nor stored. Metadata backups stay in OneLake; this public repository receives
only code, fabricated fixtures/packages and sanitized qualification counts.

Run local checks from this folder with PYTHONDONTWRITEBYTECODE=1:

- `python3 test_release.py`: receiving failure/preservation and report contracts.
- `python3 native_cases.py <NEW-WINDOWS-LOCAL-FIXTURE-FOLDER>`: build fabricated
  baseline/candidate and independent Python expectations. No company inputs.
- `run_synthetic_engine.ps1 -FixtureDirectory <SAME-WINDOWS-PATH>`: owns its own
  loopback Tabular engine, calculated partitions only, unique synthetic databases,
  and stops only its own process in finally. Never attaches a company model or
  an existing Desktop engine. Generic Tabular host omits the Desktop Mashup-only
  defaultPowerBIDataSourceVersion property from these synthetic runtime fixtures.
- `python3 native_cases.py <FIXTURE-FOLDER> --verify`: inspect exact query
  population, independent arithmetic and context expectations.
- `../check_schema.py` checks Microsoft schemas for each ZIP.

The Power BI plugin's offline dependency review was used on public formulas;
heuristic edges are supporting evidence. GitNexus is unavailable for this
unregistered repository, so graph authority remains UNKNOWN. Windows Computer
Use fails before connection with `sandboxCwd is not a local file URI`; no rendered
Desktop acceptance is claimed. Actual company/model UI/export performance still
needs the checklist and measured receiving timings. Earlier R17.7 and draft
R17.8, inventory and recovery packages remain byte-preserved.

The single maintained [UNDERSTANDING](../UNDERSTANDING.md) records release state,
verified inventory, business semantics and remaining gaps. This is the Demand
TEST page; native S&OP, complete R16.6 feature parity and production release are
separate work, not silently delivered here.
