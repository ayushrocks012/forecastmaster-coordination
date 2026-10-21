"""Build the offline review fragment from literal markup and pinned D3."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
marker = "/* BUNDLED_D3_V7_9_0 */"
template = (HERE / "page.fragment.html").read_text()
assert template.count(marker) == 1
vendor = (HERE.parent / "sop-build-up-r01/vendor/d3.v7.9.0.min.js").read_text()
fragment = template.replace(marker, vendor)
catalog_marker = "/* BRIDGE_MEASURE_CATALOG */"
assert fragment.count(catalog_marker) == 1
catalog = json.loads((HERE / "bridge-catalog.json").read_text())
fragment = fragment.replace(catalog_marker, json.dumps(catalog, separators=(",", ":")))
rules_marker = "/* SOP_SUMMARY_RULES */"
assert fragment.count(rules_marker) == 1
rules = json.loads((HERE / "summary-rules.json").read_text())
fragment = fragment.replace(rules_marker, json.dumps(rules, separators=(",", ":")))
assert len(fragment.encode()) < 1_000_000
(HERE / "review.fragment.html").write_text(fragment)
print(f"Built review.fragment.html: {len(fragment.encode()):,} bytes")
