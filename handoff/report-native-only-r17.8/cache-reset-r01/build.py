"""Compose one self-contained TEST processing cell from frozen read helpers."""
import ast
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'date-boundary-r03/CHECK DATE BOUNDARY R03.py'
NAMES={'CheckStopped','require','http','operation_path','read_definition'}


def build():
    old=SOURCE.read_text();tree=ast.parse(old)
    functions=[]
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in NAMES:
            text=ast.get_source_segment(old,node)
            if node.name=='read_definition':
                assert text.endswith('return result')
                text=text[:-len('return result')]+"return response.json()['definition'],db,result"
            functions.append(text)
    assert len(functions)==len(NAMES)
    constants=old[old.index('WORKSPACE='):old.index("QUERY='''")]
    header='''"""ONE NEW cell: isolated TEST cache reset + full refresh + private date parity.

Processing changes TEST state. No model-definition/source-table writes or
financial queries. clearValues can leave TEST unavailable until full succeeds.
Run ONCE; return final JSON even if stopped. Do not rerun an ambiguous attempt.
"""
import base64
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote, urlsplit
from uuid import UUID, uuid4

'''
    text=header+constants+'\n\n'+'\n\n'.join(functions)+'\n\n'+(HERE/'reset.py').read_text()
    ast.parse(text,feature_version=(3,10))
    out=HERE/'RESET TEST DATE CACHE R01.py'
    if out.exists() and out.read_text()!=text:raise ValueError('Preserve prepared cell; use a new revision')
    out.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


if __name__=='__main__':print(build())
