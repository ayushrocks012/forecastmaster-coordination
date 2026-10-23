"""Build additive R03 from exact qualified R02; never overwrite the active cell."""
import ast
import hashlib
from pathlib import Path

BASE_SHA = 'a9384ff27e8ac6d7f3efb11f126be435218696b1e956418eea0547932019d635'


def build(here=None, baseline=None):
    here = Path(here) if here else Path(__file__).resolve().parent
    baseline = Path(baseline) if baseline else here.parent / 'test-release-r01/VERIFY INSTALLED TEST R01.py'
    raw = baseline.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError('Qualified R02 changed; do not silently inherit its evidence')
    source = raw.decode()
    tree = ast.parse(source)
    old = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'verify_installed')
    query = next(ast.literal_eval(node.value) for node in ast.walk(old) if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'query' for target in node.targets))
    lines = source.splitlines(keepends=True)
    # Preserve shared pure/read helpers exactly, replace misleading installer module docstring.
    text = '"""Read-only R03 candidate. Not selected for operator use; current R02 remains unchanged."""\n'
    text += ''.join(lines[tree.body[0].end_lineno:old.lineno - 1])
    text += '\nFILE_COUNT_QUERY = ' + repr(query) + '\n\n'
    text += (here / 'diagnostics.py').read_text() + '\n' + (here / 'verify_r03.py').read_text()
    text += '''\nif __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    verify_installed_r03(fabric.FabricRestClient(retry_config={"total":0}),
        fabric.PowerBIRestClient(retry_config={"total":0}),notebookutils.fs,
        fabric.evaluate_dax,globals().get("spark"))
'''
    ast.parse(text, feature_version=(3, 10))
    path = here / 'VERIFY INSTALLED TEST R03.py'
    path.write_text(text)
    return {'ArtifactSHA256': hashlib.sha256(path.read_bytes()).hexdigest(), 'Bytes': path.stat().st_size}


if __name__ == '__main__':
    print(build())
