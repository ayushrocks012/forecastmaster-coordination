"""Build a single receiving cell; preserve all earlier published cells."""
import ast
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESET = HERE.parent / 'cache-reset-r01/RESET TEST DATE CACHE R01.py'
DIAGNOSTIC = HERE.parent / 'read-only-check/CHECK BLANK VISUALS AND CUTOFFS.py'
FUNCTIONS = {'CheckStopped', 'require', 'http', 'operation_path', 'read_definition',
             'digest', 'identity', 'routing', 'connections', 'as_date', 'physical_dates',
             'semantic_dates', 'compare', 'all_match', 'verified_backup'}
CONSTANTS = {'WORKSPACE', 'LAKEHOUSE', 'TEST', 'NAME', 'ROOT', 'FIELDS', 'PBI_BASE',
             'ITEM', 'PRIVATE', 'KINDS', 'DATE_QUERY'}


def selected(source, functions, constants):
    parts = []
    found = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in functions:
            parts.append(ast.get_source_segment(source, node)); found.add(node.name)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in constants:
                parts.append(ast.get_source_segment(source, node)); found.add(name)
    assert found == functions | constants, found ^ (functions | constants)
    return '\n\n'.join(parts)


def build():
    source = RESET.read_text()
    assert hashlib.sha256(RESET.read_bytes()).hexdigest() == 'a5135045e61623126cd3cc0ddb4e07da9beb25e82e1386f97bf1e44cc9fb12ff'
    header = '''"""ONE NEW company-laptop cell ONCE: TEST recovery + consolidated diagnostics.
Never clears again. May submit ONE missing full refresh after verified history,
backups and concurrency checks. Amount observations stay in memory, never output.
No model-definition, Lakehouse-table, production, connection or report writes.
Return the entire final JSON, including PARTIAL/STOPPED. Do not rerun blindly.
"""
import base64
from datetime import date, datetime, timezone
import hashlib
import json
import math
from numbers import Number
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote, urlsplit
from uuid import UUID

'''
    text = header + selected(source, FUNCTIONS, CONSTANTS)
    text += '\n\n' + selected(DIAGNOSTIC.read_text(), set(), {'FILES_QUERY', 'GUARDS_QUERY'})
    text += '\n\n' + (HERE / 'recover.py').read_text()
    ast.parse(text, feature_version=(3, 10))
    path = HERE / 'RECOVER AND DIAGNOSE TEST R02.py'
    if path.exists() and path.read_text() != text:
        raise ValueError('Preserve a prepared receiving cell; remove only an unpublished local build')
    path.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


if __name__ == '__main__':
    print(build())
