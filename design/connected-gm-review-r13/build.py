"""Build the paired, offline HTML design from literal fragments and pinned D3."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
shell = (HERE / "shell.fragment.html").read_text()
demand = (HERE / "demand.fragment.html").read_text()
sop = (HERE / "sop.fragment.html").read_text()
replacements = {
    "/* BUNDLED_D3_V7_9_0 */": (HERE.parent / "sop-build-up-r01/vendor/d3.v7.9.0.min.js").read_text(),
    "/* BRIDGE_MEASURE_CATALOG */": json.dumps(json.loads((HERE / "bridge-catalog.json").read_text()), separators=(",", ":")),
    "/* SOP_SUMMARY_RULES */": json.dumps(json.loads((HERE / "summary-rules.json").read_text()), separators=(",", ":")),
}
for marker, value in replacements.items():
    assert sop.count(marker) == 1, marker
    sop = sop.replace(marker, value)
for marker, value in {"<!-- DEMAND_PAGE -->": demand, "<!-- SOP_PAGE -->": sop}.items():
    assert shell.count(marker) == 1, marker
    shell = shell.replace(marker, value)
assert len(shell.encode()) < 1_000_000
(HERE / "review.fragment.html").write_text(shell)
print(f"Built connected review: {len(shell.encode()):,} bytes")
