"""Prepare only the shared detector helper edits; do not replace native endpoints."""
import ast
import difflib
from pathlib import Path

root = Path(__file__).resolve().parent
original = (root.parent / 'functions-r05.2/function_app.py').read_text(encoding="utf-8")
old = '''    if baseline is not None:
        if (
            not isinstance(baseline, dict)
            or baseline.get("SchemaVersion") != 1
            or baseline.get("SourceRoot") != "Files/Demand"
            or baseline.get("Status") != "SUCCESS"
            or not baseline.get("RefreshRunID")
        ):
            raise ValueError("The committed metadata baseline is invalid.")
        before = canonicalInventory(baseline.get("Files"))
        if baseline.get("Fingerprint") != inventoryFingerprint(baseline["Files"]):
            raise ValueError("The committed metadata baseline fingerprint is invalid.")
'''
new = '''    if baseline is not None:
        try:
            if (
                not isinstance(baseline, dict)
                or type(baseline.get("SchemaVersion")) is not int
                or baseline.get("SchemaVersion") != 1
                or baseline.get("SourceRoot") != "Files/Demand"
                or baseline.get("Status") != "SUCCESS"
                or not baseline.get("RefreshRunID")
            ):
                raise ValueError("The committed metadata baseline is invalid.")
            captured = datetime.fromisoformat(baseline["CapturedAtUtc"])
            if captured.utcoffset() is None:
                raise ValueError("Committed baseline timestamp needs a timezone.")
            before = canonicalInventory(baseline.get("Files"))
            if baseline.get("Fingerprint") != inventoryFingerprint(baseline["Files"]):
                raise ValueError("The committed metadata baseline fingerprint is invalid.")
        except (KeyError, TypeError, ValueError):
            baseline, before = None, {}
'''
assert original.count(old) == 1
text = original.replace(old, new)
old_read = '        baseline = readControlJson(files, "metadata-success.json")\n'
new_read = '''        try:
            baseline = readControlJson(files, "metadata-success.json")
        except (json.JSONDecodeError, UnicodeDecodeError):
            baseline = None
'''
assert text.count(old_read) == 1
text = text.replace(old_read, new_read)
ast.parse(text)
(root / 'detector.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='shared-functions/function_app.py',tofile='shared-functions/function_app.py')), encoding="utf-8")
# Keep a testable copy of only the existing shared helpers, not an older full app.
nodes = [n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name in {'canonicalInventory','inventoryFingerprint','prepareMetadataDecision'}]
(root / 'candidate/detector_helpers.py').write_text('from __future__ import annotations\nimport hashlib\nimport json\nfrom datetime import UTC, datetime\nfrom typing import Any\nimport re\n' + 'bridgePattern = re.compile(' + repr(r'[^_]+_.+?_Bridge_(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}_EF-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}_IMS-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}_.+\.(?:xlsx|xlsm)') + ', re.IGNORECASE)\n\n' + '\n\n'.join(ast.get_source_segment(text,n) for n in nodes) + '\n', encoding="utf-8")
