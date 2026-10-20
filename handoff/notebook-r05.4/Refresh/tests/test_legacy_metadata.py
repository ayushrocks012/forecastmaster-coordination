"""Compatibility is an ingestion view; original metadata, values and source bytes remain facts."""

from __future__ import annotations

import hashlib
import io
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from hypothesis import given, strategies as st
from xml.etree import ElementTree as ET

from test_refresh import NAME, reader, workbook


def metadata_variant(content: bytes, changes: dict[str, str | None]) -> bytes:
    output = io.BytesIO()
    with ZipFile(io.BytesIO(content)) as src, ZipFile(output, "w", ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "xl/workbook.xml":
                tree = ET.fromstring(data)
                names = tree.find("s:definedNames", reader.NS)
                for key, value in changes.items():
                    name = "Bridge_" + key
                    node = next((n for n in names if n.attrib["name"] == name), None)
                    if value is None:
                        if node is not None:
                            names.remove(node)
                    else:
                        if node is None:
                            node = ET.SubElement(names, "{" + reader.NS["s"] + "}definedName", {"name": name})
                        node.text = '"' + value + '"'
                data = ET.tostring(tree)
            dst.writestr(item, data)
    return output.getvalue()


@pytest.mark.parametrize("revision", ["V16_Ext", "V17_Ext"])
def test_reported_legacy_metadata_retains_revision_names_and_values(revision):
    original = workbook()
    content = metadata_variant(original, {
        "SourceProfile": "V15_Ext", "BridgeRevision": revision, "PublicationOrigin": None,
        "Cycle": "2026-10", "ExFactoryActualsThrough": "2026-09-01", "IMSActualsThrough": "2026-08-01",
    })
    before = hashlib.sha256(content).hexdigest()
    old = reader.BridgeReader(original, "Some/Folder/" + NAME)
    october_name = NAME.replace("Jul 26_EF-Jun 26_IMS-May 26", "Oct 26_EF-Sep 26_IMS-Aug 26")
    current = reader.BridgeReader(content, "Any/Other/Folder/" + october_name)
    old_rows, current_rows = list(old.rows()), list(current.rows())
    assert current.sha256 == before == hashlib.sha256(content).hexdigest()
    assert current.content == content
    assert current.metadata["SourceProfile"] == "Ext"
    assert current.metadata["Revision"] == revision
    assert current.metadata["PublicationOrigin"] == "NOT_RECORDED"
    assert current.metadata["PublicationStatus"] == "DEVELOPMENT"
    assert current.metadata["Version"] == "Dev"
    assert current.metadata["DemandCycle"] == "2026-10"
    assert current.metadata["IMSActualsThrough"] == "2026-08-01"
    assert current.metadata["ExFactoryActualsThrough"] == "2026-09-01"
    definitions = json.loads(current.metadata["DefinedNamesJson"])
    assert definitions["Bridge_SourceProfile"] == '"V15_Ext"'
    assert definitions["Bridge_BridgeRevision"] == '"' + revision + '"'
    assert "Bridge_PublicationOrigin" not in definitions
    assert current.observation_count == old.observation_count == 18
    for a, b in zip(old_rows, current_rows, strict=True):
        assert a["ids"] == b["ids"] and a["months"] == b["months"]
    receipt = reader.revision_record(current, "2026-10-19T10:00:00Z")
    assert receipt["DefinedNamesJson"] == current.metadata["DefinedNamesJson"]
    assert receipt["Revision"] == revision
    assert receipt["SourceRevisionID"] == before


@given(st.integers(min_value=1, max_value=999), st.booleans())
def test_versioned_profiles_use_their_explicit_ext_flag(number, ext):
    profile = "V" + str(number) + ("_Ext" if ext else "")
    content = metadata_variant(workbook(), {"SourceProfile": profile, "PublicationOrigin": None})
    parsed = reader.BridgeReader(content, NAME)
    list(parsed.rows())
    assert parsed.metadata["SourceProfile"] == ("Ext" if ext else "Local")


@pytest.mark.parametrize("key", ["Country", "GrowthDriver", "Cycle", "BridgeRevision", "SourceProfile", "IMSActualsThrough", "ExFactoryActualsThrough", "PublicationStatus"])
def test_legacy_metadata_does_not_supply_missing_business_fields(key):
    content = metadata_variant(workbook(), {"SourceProfile": "V15_Ext", "PublicationOrigin": None, key: None})
    with pytest.raises(ValueError, match="Missing explicit workbook metadata"):
        list(reader.BridgeReader(content, NAME).rows())


def test_native_missing_origin_remains_an_error():
    content = metadata_variant(workbook(), {"PublicationOrigin": None})
    with pytest.raises(ValueError, match="PublicationOrigin"):
        list(reader.BridgeReader(content, NAME).rows())


def test_legacy_metadata_does_not_bypass_sector_layout_validation():
    content = metadata_variant(workbook(), {"SourceProfile": "V15_Ext", "PublicationOrigin": None})
    output = io.BytesIO()
    with ZipFile(io.BytesIO(content)) as src, ZipFile(output, "w", ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename.startswith("xl/tables/"):
                data = data.replace(b'name="Channel"', b'name="Unknown column"')
            dst.writestr(item, data)
    with pytest.raises(ValueError, match="layout needs an adapter"):
        list(reader.BridgeReader(output.getvalue(), NAME).rows())


def test_recorded_origin_and_native_metadata_are_unchanged():
    for profile in ["Ext", "Local", "V15_Ext"]:
        content = metadata_variant(workbook(), {"SourceProfile": profile, "PublicationOrigin": "EXPLICIT_ORIGIN"})
        parsed = reader.BridgeReader(content, NAME)
        list(parsed.rows())
        assert parsed.metadata["PublicationOrigin"] == "EXPLICIT_ORIGIN"


@pytest.mark.parametrize("profile", ["ADS", "Unknown", "V15_bad", "Ext_Remote"])
def test_unrecognized_profile_is_not_guessed_from_filename(profile):
    content = metadata_variant(workbook(), {"SourceProfile": profile})
    with pytest.raises(ValueError, match="cycle/profile"):
        list(reader.BridgeReader(content, NAME).rows())


def test_installer_matches_the_tested_metadata_function():
    import ast
    import runpy
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    namespace = runpy.run_path(str(root / "source/reader.py"))
    exec((root / "Install_Legacy_Metadata_Compatibility.txt").read_text(), namespace)
    source = ast.parse((root / "source/reader.py").read_text())
    installer = ast.parse((root / "Install_Legacy_Metadata_Compatibility.txt").read_text())
    a = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "explicit_metadata")
    b = next(n for n in installer.body if isinstance(n, ast.FunctionDef) and n.name == "explicit_metadata")
    # The standalone cell uses Any because Element is a type-checking-only import in reader.
    a.args.args[0].annotation = ast.Name(id="Any", ctx=ast.Load())
    assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)
    assert namespace["REFRESH_MODE"] == "FILES"
    assert len(namespace["SELECTED_RELATIVE_PATHS"]) == 2
    # Reapplying the installation must not wrap recursively or duplicate the contract suffix.
    exec((root / "Install_Legacy_Metadata_Compatibility.txt").read_text(), namespace)
    assert namespace["CONTRACT"].count("legacy-metadata-compat-v1") == 1
