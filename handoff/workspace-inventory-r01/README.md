# One read-only UK-ANI-Demand inventory cell — R01

This is the new metadata inventory requested after the successful R02 recovery.
It does **not** repeat recovery, refresh a model or install the R17.8 adapter.

1. On the company laptop, open the Coordination repository terminal and run
   `git pull --ff-only`.
2. Open [INVENTORY UK-ANI-DEMAND R01.py](INVENTORY%20UK-ANI-DEMAND%20R01.py).
   Copy the **entire file**. In PowerShell at the repository root you can use:

   ```powershell
   Get-Content -Raw 'handoff/workspace-inventory-r01/INVENTORY UK-ANI-DEMAND R01.py' | Set-Clipboard
   ```

3. In Fabric, open **ForecastMaster_GM_Setup**. Add **ONE NEW PySpark/Python
   cell**, paste the whole file, and run **only that cell once**. Do not choose
   Run all. Use the existing notebook session, identity and Lakehouse connection.
   There are no IDs or code settings to edit, packages to install, sign-in steps,
   administrator changes or capacity changes.
4. Wait for the final JSON and **Download complete inventory JSON** link.
   Download `UK-ANI-Demand-inventory-R01.json` and attach it **privately in this
   chat**. If the notebook blocks the link, copy the complete output between
   `BEGIN UK-ANI-DEMAND INVENTORY JSON` and `END ...` into a local `.txt` file,
   including the final byte length/hash line, and attach it here. Include all
   PARTIAL, STOPPED and failed sections; they identify remaining access gaps.

The output contains company metadata and full measure/calculated-column DAX,
which can contain company logic and literals. **Do not commit the returned file
or notebook output to this public repository.** Review it before sharing. No
business rows or amount results are requested. Safe reviewed facts will update
the existing [project understanding](../report-native-only-r17.8/UNDERSTANDING.md);
raw definitions and credentials will not be copied into public documentation.

## What it inventories

- Exact workspace identity, followed by **all pages of visible workspace
  items**, recursively through folders; item names/types/IDs/folder IDs.
- Each visible Lakehouse and supported OneLake-backed data item: all returned
  schemas, tables and fields, types, precision/scale, nullability and positions.
  The OneLake Delta metadata API supports both schema and non-schema Lakehouses.
  A classic Lakehouse API plus Spark **schema-only** fallback is available when
  that metadata endpoint cannot be read. It performs no DataFrame data action.
- **Every visible semantic model**, including original and TEST: all logical
  table/column/measure names, hidden flags, calculated-column DAX, full measure
  DAX, formats and dynamic format expressions, hierarchies, calculation groups,
  partition modes/source identifiers, and relationships with endpoints,
  direction/cardinality/active state. Full original definitions are held only
  transiently in memory; the output includes their fingerprints.
- Report-to-model bindings; role names and counts, table-permission names and
  whether a filter exists; named-expression identities/fingerprints.
- A second workspace item listing checks for item-list changes during the run.
  Each read has status/timing, and failed optional routes retain their evidence.
  A complete result is labelled **COMPLETED_WITHIN_DECLARED_SCOPE**, not a claim
  that this user can see every hidden/restricted tenant object.

## Deliberate boundaries

No refresh, clearValues, updateDefinition, model calculation, table write,
definition/connection/permission/schedule change, report publication or remote
file write. The only POST retrieves semantic-model metadata with `getDefinition`;
its asynchronous operation is polled separately. That API may require stronger
existing model permissions than listing items; refusal is recorded, without
requesting access changes or falling back to a model modification.

No DAX amount queries, row counts, samples, table scans, notebook/pipeline/
function code exports, source-file reads or runtime repair. No raw exception
messages, headers, connection strings, tokens, role member identities, role
filter expressions, arbitrary annotations, partition M/SQL/calculated-table
source expressions or stored source records are exported. Descriptive table/
measure metadata and DAX literals are not business query results, but still
need the private handling described above.

SQL views/procedures, effective permissions, KQL catalogs, engine-internal
generated measures, whole-workspace lineage and unsupported item-engine
catalogs remain explicit limits. KQL/Datamart/other recognized unsupported
table engines are listed as gaps. OneLake catalogs are not SQL endpoint catalog
exports. No workspace-wide atomic snapshot or absence of concurrent definition
edits is asserted. This inventory does not establish numerical parity, data
quality, capacity health, native rendering or performance.

The download is assembled in memory as a browser data link. It does not upload
or create a OneLake file. Full JSON is also printed for receiving UI limitations.
Its content hash and final UTF-8 file length/hash identify missing/truncated
copies. A forced session kill can still prevent final output; do not infer
completion from the last progress message.

## Validation and documented API basis

[VALIDATION.json](VALIDATION.json) separates local simulated checks from the
pending company run. Run the new local tests with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s handoff/workspace-inventory-r01 -p test_inventory.py -v
```

Official references checked on 23 October 2026:

- [Fabric workspace item listing and pagination](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/list-items)
- [Semantic-model getDefinition: TMSL, permission limits and asynchronous response](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/get-semantic-model-definition)
- [Semantic-model definition parts, including model.bim](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/semantic-model-definition)
- [OneLake Delta metadata API](https://learn.microsoft.com/en-us/fabric/onelake/table-apis/delta-table-apis-overview)
- [OneLake schema/table/column response examples](https://learn.microsoft.com/en-us/fabric/onelake/table-apis/delta-table-apis-get-started)
- [OneLake authentication audience](https://learn.microsoft.com/en-us/fabric/onelake/table-apis/table-apis-overview)
- [NotebookUtils token audiences](https://learn.microsoft.com/en-us/fabric/data-engineering/notebookutils/notebookutils-credentials)
- [Classic Lakehouse table listing](https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/tables/list-tables)
- [Schema-enabled Lakehouse restriction on the classic endpoint](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-api)
- [Report model bindings](https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-reports-in-group)

Built-in Power BI visuals and the existing production report remain unchanged.
