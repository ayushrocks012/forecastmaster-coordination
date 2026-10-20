"""Check the exact initial handoff bytes; uses Python's standard library only."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "HANDOFF-MANIFEST.json").read_text(encoding="utf-8"))
errors = []
for name, expected in manifest["Files"].items():
    path = root / name
    if not path.is_file():
        errors.append(name + ": missing")
        continue
    payload = path.read_bytes()
    if len(payload) != expected["Bytes"] or hashlib.sha256(payload).hexdigest() != expected["SHA256"]:
        errors.append(name + ": differs from the prepared handoff")
if errors:
    raise SystemExit("\n".join(errors))
print("Verified", len(manifest["Files"]), "handoff files against their recorded bytes.")
