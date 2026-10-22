"""Package a separate thin-report copy against the receiving TEST model only.

No Fabric calls, publishing, model changes or business-visual edits. All report
payloads except the connection and PBIP project reference retain their bytes.
"""
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "report-native-r17/candidate/ForecastMaster Native Review R17 - Candidate.zip"
SOURCE_SHA256 = "feca03b94b2cf3fd5abacb46acf870e6f3d201c860224a7b5036c4bf1e3ed5b1"
SOURCE_ID = "e7af2967-7725-4108-a170-9e490d4e35bb"
TEST_ID = "31d00232-ac03-48fe-af39-f2e4bae82443"
TEST_MODEL = "ForecastMaster Native OneLake R17.1 - TEST"
PROJECT = "ForecastMaster Native Review R17.1 TEST"
OLD_PROJECT = "ForecastMaster Native Review"
SOURCE_PREFIX = OLD_PROJECT + "/"


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def build_package(source_bytes, instructions):
    if sha256(source_bytes) != SOURCE_SHA256:
        raise ValueError("Original candidate bytes differ from the audited handoff; inspect before binding.")
    target = {}
    changed = []
    preserved = {}
    with zipfile.ZipFile(BytesIO(source_bytes)) as source:
        names = source.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entry.")
        for name in names:
            if not name.startswith(SOURCE_PREFIX):
                continue
            relative = name.removeprefix(SOURCE_PREFIX)
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or "\\" in relative:
                raise ValueError("Unexpected project path.")
            if any(p in {".pbi", ".git", ".platform"} for p in path.parts):
                raise ValueError("Unexpected local cache or item identity in thin report.")
            if path.suffix.lower() in {".pbix", ".pbit", ".abf", ".bim", ".tmdl"}:
                raise ValueError("Cached/full model content is outside this thin-report handoff.")
            payload = source.read(name)
            output_name = relative
            if relative.startswith(OLD_PROJECT + ".Report/"):
                output_name = PROJECT + ".Report/" + relative.removeprefix(OLD_PROJECT + ".Report/")
            if relative == OLD_PROJECT + ".pbip":
                definition = json.loads(payload)
                expected = [{"report": {"path": OLD_PROJECT + ".Report"}}]
                if definition.get("artifacts") != expected:
                    raise ValueError("Unexpected PBIP project reference.")
                definition["artifacts"][0]["report"]["path"] = PROJECT + ".Report"
                output_name = PROJECT + ".pbip"
                payload = (json.dumps(definition, indent=2) + "\n").encode()
                changed.append(output_name)
            elif relative == OLD_PROJECT + ".Report/definition.pbir":
                definition = json.loads(payload)
                connection = definition["datasetReference"]["byConnection"]
                original = connection["connectionString"]
                expected = ('Data Source=powerbi://api.powerbi.com/v1.0/myorg/UK-ANI-Demand;'
                            'Initial Catalog="ForecastMaster Demand Model";Access Mode=readonly;'
                            'Integrated Security=ClaimsToken;semanticModelId=' + SOURCE_ID)
                if original != expected or set(connection) != {"connectionString"}:
                    raise ValueError("Unexpected original binding; do not replace arbitrary connections.")
                connection["connectionString"] = original.replace(
                    'Initial Catalog="ForecastMaster Demand Model"', 'Initial Catalog="' + TEST_MODEL + '"'
                ).replace("semanticModelId=" + SOURCE_ID, "semanticModelId=" + TEST_ID)
                payload = (json.dumps(definition, indent=2) + "\n").encode()
                changed.append(output_name)
            else:
                preserved[output_name] = sha256(payload)
            target[output_name] = payload
    if set(changed) != {PROJECT + ".pbip", PROJECT + ".Report/definition.pbir"}:
        raise ValueError("Expected exactly one PBIP project and one connection change.")
    target["OPEN FIRST.txt"] = instructions.encode()
    result = BytesIO()
    with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(target.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    return result.getvalue(), changed, preserved


def main():
    instructions = (HERE / "NEXT - REFRESH AND OPEN TEST.txt").read_text()
    source_bytes = SOURCE.read_bytes()
    payload, changed, preserved = build_package(source_bytes, instructions)
    destination = HERE / "candidate"
    destination.mkdir(exist_ok=True)
    output = destination / (PROJECT + ".zip")
    if output.exists() and output.read_bytes() != payload:
        raise ValueError("A different TEST package already exists. Preserve it and use a new revision.")
    if not output.exists():
        output.write_bytes(payload)
    receipt = {
        "Artifact": output.name, "SHA256": sha256(payload), "Bytes": len(payload),
        "SourceSHA256": sha256(source_bytes), "SourceZIPUnchanged": SOURCE.read_bytes() == source_bytes,
        "TestModelName": TEST_MODEL, "TestModelID": TEST_ID,
        "ChangedProjectFiles": changed, "PreservedProjectFiles": len(preserved),
        "PreservedProjectSHA256": preserved, "AddedFiles": ["OPEN FIRST.txt"],
        "SQLInstallerOrProbePackaged": False, "CachedSalesOrFullModelPackaged": False,
        "CompanyConnectionIdentifiersIncluded": True, "Publication": False,
        "CompanyProcessingOrRenderingConfirmed": False,
        "NativeParity": "NOT COMPLETE; existing R17 gaps remain."}
    (destination / "PACKAGE-CHECK.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "PreservedProjectSHA256"}, indent=2))


if __name__ == "__main__":
    main()
