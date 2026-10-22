# Native R17.2 TEST revision

Open [OPEN FIRST - WORK LAPTOP.txt](OPEN%20FIRST%20-%20WORK%20LAPTOP.txt).
It gives the exact pull, one-cell TEST update, TEST refresh and new ZIP steps.
Production R16.6 remains in place.

The reported blank/inactive buttons came from malformed PBIR action/text
definitions. The resource error's detailed company message has not yet been
provided; its precise memory/timeout cause is unconfirmed. This revision removes
expensive repeated fact retrievals without changing available-member arithmetic,
and narrows the default calendar to a reviewable year. The native-engine and
report-structure checks are distinct from company UI/capacity acceptance.

Files:

- `UPDATE EXISTING TEST TO R17.2.py`: standalone readable Fabric cell.
- `ForecastMaster Native TEST R17.2.ipynb`: optional one-cell import, no outputs.
- `candidate/ForecastMaster Native Review R17.2 TEST.zip`: thin report bound to
  the already created TEST; no cached company data/model is included.
- `model.py`, `build_cell.py`, `prepare_project.py`: reproducible source.
- `tests/`: synthetic native engine fixtures, mocked update guards and report
  definition checks. `VALIDATION-*.json` records the completed local gates.
- [Capability comparison](CAPABILITIES-VS-R16.6.md): implemented and open gaps.

For developer verification (no company connection), run the two Python check
scripts. Generate `engine_fixture.py`, `additional_fixture.py signed/mixed` and
`scale_fixture.py` into private local scratch directories. On an explicitly
task-owned Power BI Desktop engine run `tests/run_engine.ps1 -Port PORT
-FixtureDirectory WINDOWS_LOCAL_DIRECTORY`, then each fixture's `--verify`
against the returned `queries-results.json`. The runner refuses non-synthetic
names and non-calculated source partitions. Do not point it at company models.

The thin report builder consumes the hash-pinned R17.1 TEST ZIP and requires a
new output directory. Advanced/Refresh/custom-control payloads and the TEST
binding retain their bytes. It rebuilds native pages/bookmarks only. Microsoft
schema validation used the frozen native checker; two preserved R16.6 schema
URLs remain unavailable (404), not a successful validation of those old schemas.

GitNexus did not provide a usable Coordination impact graph (repository authority
unavailable). Direct source/dependency tracing, synthetic engine execution and
explicit preservation comparisons supply the bounded evidence here.

Technical references: [Microsoft button authoring](https://raw.githubusercontent.com/microsoft/skills-for-fabric/main/skills/powerbi-report-cli/references/authoring/button.md),
[button actions and state formatting](https://raw.githubusercontent.com/microsoft/skills-for-fabric/main/skills/powerbi-report-cli/references/authoring/button-part-02.md),
[native buttons](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-buttons),
[dynamic numeric format strings](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-dynamic-format-strings).
