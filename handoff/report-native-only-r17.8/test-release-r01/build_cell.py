"""Build a standalone receiving cell from pinned, reviewed public source."""
import ast
import importlib.util
import inspect
from pathlib import Path
import pprint

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def selected(source,names):
    result=[];found=set()
    for node in ast.parse(source).body:
        keys={node.name} if isinstance(node,(ast.FunctionDef,ast.ClassDef)) else {t.id for t in node.targets if isinstance(t,ast.Name)} if isinstance(node,ast.Assign) else set()
        if keys & names:result.append(ast.get_source_segment(source,node));found|=keys&names
    assert found==names,names-found
    return '\n\n'.join(result)


def build():
    model=load('r178_release_model',HERE/'model.py')
    previous=(HERE.parent/'cache-recovery-r02/RECOVER AND DIAGNOSE TEST R02.py').read_text()
    helper_names={'WORKSPACE','LAKEHOUSE','TEST','NAME','ROOT','FIELDS','ITEM','KINDS','DATE_QUERY',
      'CheckStopped','require','http','operation_path','read_definition','digest','identity','routing','connections',
      'as_date','physical_dates','semantic_dates','compare','all_match','verified_backup','safe_failure'}
    source='''"""ONE NEW ForecastMaster_GM_Setup cell; existing TEST only, run ONCE.
12 sequential paired scalar comparisons (values never printed/stored), verified
private backup, pinned inventory and concurrency guards, scoped update/readback.
No refresh, source/production write or publication. Return final JSON.
"""
import base64
from copy import deepcopy
from datetime import date,datetime,timezone
import hashlib
import json
import math
from numbers import Number
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote,urlsplit
from uuid import UUID,uuid4

'''+selected(previous,helper_names)+'\n\n'
    baseline=model.original_database()
    baseline['model']['tables']=[t for t in baseline['model']['tables'] if t['name'] in {'fm_native_measures','fm_native_files'}]
    source=source.replace('except Exception:\n        pass','except Exception:\n        signals=[]  # Error rendering must not expose private details.')
    source+='BASELINE = '+pprint.pformat(baseline,width=110,sort_dicts=False)+'\n\n'
    source+='def original_database():\n    return deepcopy(BASELINE)\n\n'
    source+='def expression_hash(value):\n    return hashlib.sha256(expression_text(value).strip().replace(\"\\r\\n\",\"\\n\").encode()).hexdigest()\n\n'
    for name in ('PICKED','MODE','OLD_MODE','DATE_OK','FILE_AVAILABLE'):
        source+=name+' = '+pprint.pformat(getattr(model,name),width=110)+'\n\n'
    for function in (model.replacements,model.file_expression,model.expression_text,model.normalized,model.patch_database):
        source+=inspect.getsource(function)+'\n\n'
    source+='EDITS = replacements()\n\n'
    check=load('r177_numeric',HERE.parents[1]/'report-native-only-r17.7/numeric_check.py')
    source+='METADATA_QUERY = '+repr(check.METADATA_QUERY)+'\n\n'
    source+=(HERE/'receiving.py').read_text()+'\n\n'
    source+='''if __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    # POST retry disabled, including transport retries. Intent is persisted before update.
    run(fabric.FabricRestClient(retry_config={"total":0}),notebookutils.fs,fabric.evaluate_dax,fabric.PowerBIRestClient(retry_config={"total":0}))
'''
    ast.parse(source,feature_version=(3,10))
    (HERE/'INSTALL COMPACT TEST R01.py').write_text(source)
    verify=source[:source.index('if __name__ == \"__main__\":')]+(HERE/'verify_receiving.py').read_text()+'''\nif __name__ == \"__main__\":\n    import sempy.fabric as fabric\n    import notebookutils\n    verify_installed(fabric.FabricRestClient(retry_config={\"total\":0}),fabric.PowerBIRestClient(retry_config={\"total\":0}),notebookutils.fs,fabric.evaluate_dax,globals().get(\"spark\"))\n'''
    ast.parse(verify,feature_version=(3,10))
    (HERE/'VERIFY INSTALLED TEST R01.py').write_text(verify)
    return len(source.encode())

if __name__=='__main__':print(build())
