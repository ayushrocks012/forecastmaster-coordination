"""Read neutral identities only; never execute workbook code or copy source values."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads((HERE / "bridge-catalog.json").read_text())
    expected_contexts = {(b["channel"], b["subChannel"]) for b in catalog["bindings"]}
    context_order = list(dict.fromkeys(
        (b["channel"], b["subChannel"])
        for key in catalog["displayOrder"]
        for b in catalog["bindings"] if b["id"] == key
    ))
    reports = {}
    total_matches = total_order_checks = total_sectors = total_data_rows = 0
    for driver, source in catalog["sources"].items():
        raw = (args.source_root / f"{driver}.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["descriptorSHA256"], driver
        descriptor = json.loads(raw)
        assert descriptor["schema"] == "SDM_V18_MODEL_BINDINGS_V1"
        positions = defaultdict(list)
        coverage = Counter()
        data_count = 0
        for plan in descriptor["sectors"].values():
            # Only ordinal positions and the whitelisted identity fields below
            # are used. Product/Manufacturer/Sector identities are not copied.
            rows = [(i, r) for i, r in enumerate(plan["rows"], 66)
                    if r.get("kind") == "data"]
            data_count += len(rows)
            found_contexts = {(r["metadata"][0], r["metadata"][1]) for _, r in rows}
            assert found_contexts == expected_contexts, "Source context set differs"
            coverage.update(found_contexts)
            for dimension in ("units", "value"):
                ordered = []
                for binding in catalog["bindings"]:
                    expected = binding[dimension]
                    matches = [(i, r) for i, r in rows
                               if r.get("canonical_measure") == expected["role"]
                               and r["metadata"][0] == binding["channel"]
                               and r["metadata"][1] == binding["subChannel"]]
                    assert len(matches) == 1, (driver, binding["id"], dimension)
                    number, row = matches[0]
                    metadata = row["metadata"]
                    assert metadata[5] == expected["section"]
                    assert metadata[6] == expected["measure"]
                    positions[(binding["id"], dimension)].append(number)
                    ordered.append((number, binding["id"]))
                    total_matches += 1
                assert [key for _, key in sorted(ordered)] == catalog["displayOrder"]
                total_order_checks += 1
        sector_count = len(descriptor["sectors"])
        total_sectors += sector_count
        total_data_rows += data_count
        reports[driver] = {
            "descriptorSHA256": source["descriptorSHA256"],
            "sectorDefinitions": sector_count,
            "structuralDataRowsInspected": data_count,
            "bindingMatches": sector_count * len(catalog["bindings"]) * 2,
            "sourceOrderChecks": sector_count * 2,
            "contexts": [{"channel": c, "subChannel": s, "sectorOccurrences": coverage[(c, s)]}
                         for c, s in context_order],
        }
        for binding in catalog["bindings"]:
            for dimension in ("units", "value"):
                observed = positions[(binding["id"], dimension)]
                binding[dimension].pop("row", None)
                binding[dimension].setdefault("rowRangesByDriver", {})[driver] = {
                    "min": min(observed), "max": max(observed),
                    "distinctPositions": len(set(observed)), "occurrences": len(observed),
                }
    catalog["schema"] = "FM_SOP_EXECUTIVE_BRIDGE_CATALOG_R09"
    catalog["contextOrder"] = [{"channel": c, "subChannel": s} for c, s in context_order]
    catalog["presentationPolicy"] = (
        "All 13 source contexts audited across 29 retained sector definitions. "
        "Retail precedes Private Order/Internal Account; Contracts resumes afterwards. "
        "Homecare/Hospital retain ADS Units/Value only at the user's explicit request. "
        "Row positions vary by sector; bind by the full source identity, not one row number."
    )
    receipt = {
        "schema": "FM_SOP_R09_RETAINED_BRIDGE_AUDIT",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "status": "PASS", "sourceContextCount": len(expected_contexts),
        "sectorDefinitions": total_sectors, "structuralDataRowsInspected": total_data_rows,
        "bindingIdentityMatches": total_matches, "sourceOrderChecks": total_order_checks,
        "dimensions": ["units", "value"], "selectedExecutiveMeasures": len(catalog["bindings"]),
        "sourceReports": reports, "findings": [],
        "scope": "Retained neutral Core Oral and Paed SIP definitions, all sectors and all Channel/Sub-channel contexts. Executive measures only; not every bridge working/input.",
        "exclusions": "Cur/Pub remain excluded. Homecare/Hospital baseline/day, new-contract and shipment workings remain outside this GM page by user choice.",
        "limits": "No live workbook/Fabric audit, real forecast values, full model binding or Power BI speed qualification. GitNexus reported stale authority; direct retained identities supplied this evidence.",
    }
    (HERE / "bridge-catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    (HERE / "bridge-audit.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"PASS: {len(expected_contexts)} contexts, {total_sectors} sector definitions, "
          f"{total_data_rows} structural rows, {total_matches} binding matches, {total_order_checks} orders")


if __name__ == "__main__":
    main()
