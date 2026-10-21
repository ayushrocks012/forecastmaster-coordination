"""Keep the numeric aggregate expressions; broaden only the transport scope."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'baseline'))
from measures import M, tmdl_measure
import visual_feed  # noqa: F401

READY = """VAR _country = CALCULATE(SELECTEDVALUE('fm_review_reference'[Country]), ALLSELECTED('fm_review_reference'))
VAR _cycles = CALCULATETABLE(VALUES('fm_review_reference'[DemandCycle]), ALLSELECTED('fm_review_reference'))
VAR _selectedIDs = SELECTCOLUMNS(ALLSELECTED('fm_review_reference'), "ID", 'fm_review_reference'[SourceRevisionID])
VAR _expectedIDs = SELECTCOLUMNS(FILTER(ALL('fm_review_reference'), 'fm_review_reference'[Country] = _country && 'fm_review_reference'[DemandCycle] IN _cycles), "ID", 'fm_review_reference'[SourceRevisionID])
VAR _allMetrics = CALCULATE(DISTINCTCOUNT('fm_review_measures'[MetricKey]), ALLSELECTED('fm_review_measures')) = COUNTROWS(ALL('fm_review_measures'))
VAR _cycleComplete = NOT ISBLANK(_country) && ISEMPTY(EXCEPT(_expectedIDs, _selectedIDs)) && _allMetrics
"""

def candidate():
    result = {}
    for name, measure in M.items():
        if not name.startswith('FM UI '):
            continue
        item = dict(measure)
        expression = item['expression']
        if name in ['FM UI Numerator', 'FM UI Denominator', 'FM UI Numerator Missing', 'FM UI Denominator Missing']:
            end = expression.index('\nRETURN IF(_scopeAllowed,')
            # All following component aggregation, missing-cell and file-membership logic is unchanged.
            expression = READY + 'VAR _scopeAllowed = _cycleComplete' + expression[end:]
        elif name == 'FM UI Context':
            expression = READY + expression.replace('"""schema"":" & "4"', '"""schema"":" & "5" & "," & """complete"":" & IF(_cycleComplete, "true", "false")')
            assert '"5"' in expression and '"""complete""' in expression
        elif name == 'FM UI Dimensions':
            # Availability is derived once from the numeric cycle rows, for the selected file cohort.
            expression = 'BLANK()'
        item['expression'] = expression
        result[name] = item
    return result

if __name__ == '__main__':
    result = candidate()
    (ROOT / 'FEED-MEASURES.json').write_text(json.dumps(result, indent=2) + '\n')
    text = 'createOrReplace\n\tref table fm_review_measures\n\n' + '\n\n'.join(tmdl_measure(name, value, indent='\t\t') for name, value in result.items()) + '\n'
    (ROOT / 'Upgrade_Cycle_Feed_R04.2.tmdl').write_text('\n'.join(line.rstrip() for line in text.splitlines()) + '\n')
    print('Prepared', len(result), 'feed measures; numeric aggregation expressions preserved.')
