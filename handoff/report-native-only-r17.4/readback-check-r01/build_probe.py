"""Freeze public definition fingerprints into the one-cell read-only probe."""
import importlib.util
from pathlib import Path
import pprint

HERE = Path(__file__).resolve().parent


def build():
    spec = importlib.util.spec_from_file_location("r174_frozen", HERE.parent / "UPDATE EXISTING TEST TO R17.4.py")
    updater = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(updater)
    rules = {}
    for name, old in updater.EXPECTED.items():
        fields = {}
        edits = updater.REPLACEMENTS.get(name, {})
        for key in ("expression", "formatStringDefinition"):
            if key not in old:
                continue
            first, second = old[key], edits.get(key, old[key])
            if key != "expression":
                first, second = first["expression"], second["expression"]
            hashes = [updater.expression_hash(first)]
            if updater.expression_hash(second) != hashes[0]:
                hashes.append(updater.expression_hash(second))
            fields[key] = hashes
        rules[name] = fields
    source = (HERE / "probe.py").read_text(encoding="utf-8")
    return source.replace("RULES = {}  # Replaced with frozen, public-code hashes by build_probe.py.",
                          "RULES = " + pprint.pformat(rules, width=110, sort_dicts=False))


if __name__ == "__main__":
    (HERE / "CHECK R17.4 READBACK.py").write_text(build(), encoding="utf-8")
