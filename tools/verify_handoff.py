"""Check the exact initial handoff bytes; uses Python's standard library only."""

import hashlib
import json
from pathlib import Path
import sys

# Verification must not leave bytecode files in the receiving checkout.
sys.dont_write_bytecode = True
from receiving_contract import check_contract

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
try:
    receiving = check_contract(root, manifest)
except (ValueError, KeyError, TypeError, OSError) as exc:
    raise SystemExit('Receiving admission failed: ' + str(exc)) from None
print("Verified", len(manifest["Files"]), "handoff files against their recorded bytes.")
print(json.dumps(receiving, sort_keys=True))
