"""Build the offline review fragment from literal markup and pinned D3."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
marker = "/* BUNDLED_D3_V7_9_0 */"
template = (HERE / "page.fragment.html").read_text()
assert template.count(marker) == 1
vendor = (HERE.parent / "sop-build-up-r01/vendor/d3.v7.9.0.min.js").read_text()
fragment = template.replace(marker, vendor)
assert len(fragment.encode()) < 1_000_000
(HERE / "review.fragment.html").write_text(fragment)
print(f"Built review.fragment.html: {len(fragment.encode()):,} bytes")
