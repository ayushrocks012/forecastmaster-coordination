from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from build_feed import M, candidate

source = '# Run after importing the R04.2 visual into the existing report and saving it.\n'
source += (ROOT / 'install_feed.py').read_text()
source += '\nEXPECTED = json.loads(' + repr(json.dumps({k: v for k, v in M.items() if k.startswith('FM UI ')})) + ')\n'
source += 'UPDATES = json.loads(' + repr(json.dumps(candidate())) + ')\n'
source += 'result = main(EXPECTED, UPDATES)\n'
notebook = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {'kernelspec': {'display_name': 'PySpark (Python)', 'language': 'python', 'name': 'synapse_pyspark'}, 'language_info': {'name': 'python'}}, 'cells': [{'cell_type': 'markdown', 'metadata': {}, 'source': ['# ForecastMaster R04.2 cycle feed\n', 'First import the R04.2 visual into the existing report and save it. Then Run all here. This updates six transport expressions in the existing semantic model. Source tables, partitions, calculations, report pages, native button, Functions and pipelines retain their existing definitions. A readable model backup is verified in ForecastMaster before the update. Company speed must be checked after installation.\n']}, {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [], 'source': source.splitlines(keepends=True)}]}
(ROOT / 'Install_Cycle_Feed_R04.2.ipynb').write_text(json.dumps(notebook, indent=1) + '\n')
print('Prepared standalone Fabric installer notebook.')
