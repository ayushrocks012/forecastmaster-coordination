# ONE NEW TEST semantic model only. The original report/model is never replaced.
# OneLake calculated helpers referencing Direct Lake are a preview compatibility test.
# This file is readable Python. Import the .ipynb instead of copying JSON/base64 text.
import base64
import copy
from copy import deepcopy
import hashlib
import json
import re
import time
from types import SimpleNamespace
from urllib.parse import quote
from uuid import UUID
import sempy.fabric as fabric


PREFIX = "fm_native_"
ORDER = ['share', 'abbott', 'market', 'pi', 'net', 'community', 'wholesaler', 'ni', 'homecare', 'hospital', 'hcl', 'competitor', 'nursing', 'private', 'internal', 'retail', 'unassigned', 'ads']


def catalog_rows():
    return [{'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-abbott-units',
      'Denominator': 'gm-market-units',
      'Display': 'Units',
      'Growth': 0,
      'Measure': 'Share %',
      'MeasureRank': 0,
      'RowID': 'share',
      'RunRate': 0,
      'SourceOrder': 0,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-abbott-value',
      'Denominator': 'gm-market-value',
      'Display': 'Value',
      'Growth': 0,
      'Measure': 'Share %',
      'MeasureRank': 0,
      'RowID': 'share',
      'RunRate': 0,
      'SourceOrder': 0,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-abbott-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'Abbott IMS units',
      'MeasureRank': 1,
      'RowID': 'abbott',
      'RunRate': 1,
      'SourceOrder': 1,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-abbott-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'Abbott IMS value',
      'MeasureRank': 1,
      'RowID': 'abbott',
      'RunRate': 1,
      'SourceOrder': 1,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-market-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'Market units',
      'MeasureRank': 2,
      'RowID': 'market',
      'RunRate': 1,
      'SourceOrder': 2,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-market-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'Market value',
      'MeasureRank': 2,
      'RowID': 'market',
      'RunRate': 1,
      'SourceOrder': 2,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-pi-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 0,
      'Measure': 'PI units',
      'MeasureRank': 3,
      'RowID': 'pi',
      'RunRate': 1,
      'SourceOrder': 3,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-pi-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 0,
      'Measure': 'PI value',
      'MeasureRank': 3,
      'RowID': 'pi',
      'RunRate': 1,
      'SourceOrder': 3,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-net-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 0,
      'Measure': 'IMS minus PI units',
      'MeasureRank': 4,
      'RowID': 'net',
      'RunRate': 1,
      'SourceOrder': 4,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'IMS',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-net-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 0,
      'Measure': 'IMS minus PI value',
      'MeasureRank': 4,
      'RowID': 'net',
      'RunRate': 1,
      'SourceOrder': 4,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-community-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 5,
      'RowID': 'community',
      'RunRate': 1,
      'SourceOrder': 5,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'gm-community-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 5,
      'RowID': 'community',
      'RunRate': 1,
      'SourceOrder': 5,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'wholesaler',
      'RunRate': 1,
      'SourceOrder': 6,
      'SubChannel': 'Wholesaler',
      'SubRank': 1},
     {'Basis': 'EF',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'wholesaler',
      'RunRate': 1,
      'SourceOrder': 6,
      'SubChannel': 'Wholesaler',
      'SubRank': 1},
     {'Basis': 'EF',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'ni',
      'RunRate': 1,
      'SourceOrder': 7,
      'SubChannel': 'Northern Ireland',
      'SubRank': 2},
     {'Basis': 'EF',
      'Channel': 'Community',
      'ChannelRank': 0,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'ni',
      'RunRate': 1,
      'SourceOrder': 7,
      'SubChannel': 'Northern Ireland',
      'SubRank': 2},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'homecare',
      'RunRate': 1,
      'SourceOrder': 8,
      'SubChannel': 'Homecare',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'homecare',
      'RunRate': 1,
      'SourceOrder': 8,
      'SubChannel': 'Homecare',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'hospital',
      'RunRate': 1,
      'SourceOrder': 9,
      'SubChannel': 'Hospital',
      'SubRank': 1},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'hospital',
      'RunRate': 1,
      'SourceOrder': 9,
      'SubChannel': 'Hospital',
      'SubRank': 1},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'hcl',
      'RunRate': 1,
      'SourceOrder': 10,
      'SubChannel': 'Healthcare Logistics',
      'SubRank': 2},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'hcl',
      'RunRate': 1,
      'SourceOrder': 10,
      'SubChannel': 'Healthcare Logistics',
      'SubRank': 2},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'competitor',
      'RunRate': 1,
      'SourceOrder': 11,
      'SubChannel': 'Competitor',
      'SubRank': 3},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'competitor',
      'RunRate': 1,
      'SourceOrder': 11,
      'SubChannel': 'Competitor',
      'SubRank': 3},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'nursing',
      'RunRate': 1,
      'SourceOrder': 12,
      'SubChannel': 'Nursing Home',
      'SubRank': 4},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'nursing',
      'RunRate': 1,
      'SourceOrder': 12,
      'SubChannel': 'Nursing Home',
      'SubRank': 4},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'private',
      'RunRate': 1,
      'SourceOrder': 13,
      'SubChannel': 'Private Order',
      'SubRank': 5},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'private',
      'RunRate': 1,
      'SourceOrder': 13,
      'SubChannel': 'Private Order',
      'SubRank': 5},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'internal',
      'RunRate': 1,
      'SourceOrder': 14,
      'SubChannel': 'Internal Account',
      'SubRank': 6},
     {'Basis': 'EF',
      'Channel': 'Contracts',
      'ChannelRank': 1,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'internal',
      'RunRate': 1,
      'SourceOrder': 14,
      'SubChannel': 'Internal Account',
      'SubRank': 6},
     {'Basis': 'EF',
      'Channel': 'Out of Pocket',
      'ChannelRank': 2,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'retail',
      'RunRate': 1,
      'SourceOrder': 15,
      'SubChannel': 'Retail',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Out of Pocket',
      'ChannelRank': 2,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'retail',
      'RunRate': 1,
      'SourceOrder': 15,
      'SubChannel': 'Retail',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Unassigned',
      'ChannelRank': 3,
      'Component': 'ef-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'unassigned',
      'RunRate': 1,
      'SourceOrder': 16,
      'SubChannel': 'Unassigned',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Unassigned',
      'ChannelRank': 3,
      'Component': 'ef-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'unassigned',
      'RunRate': 1,
      'SourceOrder': 16,
      'SubChannel': 'Unassigned',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Sector total',
      'ChannelRank': 4,
      'Component': 'gm-ads-units',
      'Denominator': '',
      'Display': 'Units',
      'Growth': 1,
      'Measure': 'ADS units',
      'MeasureRank': 0,
      'RowID': 'ads',
      'RunRate': 1,
      'SourceOrder': 17,
      'SubChannel': '',
      'SubRank': 0},
     {'Basis': 'EF',
      'Channel': 'Sector total',
      'ChannelRank': 4,
      'Component': 'gm-ads-value',
      'Denominator': '',
      'Display': 'Value',
      'Growth': 1,
      'Measure': 'ADS value',
      'MeasureRank': 0,
      'RowID': 'ads',
      'RunRate': 1,
      'SourceOrder': 17,
      'SubChannel': '',
      'SubRank': 0}]

SOURCES = r'''VAR _country = VALUES('fm_review_files'[Country])
VAR _cycles = VALUES('fm_review_files'[DemandCycle])
VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])
VAR _custom = SELECTEDVALUE('fm_native_file_mode'[Mode],"Automatic ADS") = "Selected files"
VAR _scenario = COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))
VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])
VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] IN _country
 && 'fm_native_files'[DemandCycle] IN _cycles
 && IF(_custom,'fm_native_files'[SourceRevisionID] IN _chosen,'fm_native_files'[ADSPriority]>0))
VAR _driver = INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",'fm_native_files'[GrowthDriver])))
VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)
VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN _chosen && (ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),
 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))
VAR _ids = SELECTCOLUMNS(_files,"ID",'fm_native_files'[SourceRevisionID])
VAR _scope = SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])
VAR _expected = CROSSJOIN(_country,_cycles,_driver)
VAR _cohorts = SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])
VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)
 && COUNTROWS(_cohorts)=COUNTROWS(_expected)
 && (NOT _custom || ISFILTERED('fm_review_files'[FileLabel]))
'''
FILES = r'''
VAR _base = SELECTCOLUMNS('fm_review_files',
 "SourceRevisionID", [SourceRevisionID], "SourceFileName", [SourceFileName],
 "SourceRelativePath", [SourceRelativePath], "Country", [Country],
 "DemandCycle", [DemandCycle], "GrowthDriver", [GrowthDriver],
 "IMSActualsThrough", [IMSActualsThrough], "ExFactoryActualsThrough", [ExFactoryActualsThrough],
 "PublicationStatus", [PublicationStatus], "FileLabel", [FileLabel])
VAR _stem = ADDCOLUMNS(_base, "_Stem",
 SUBSTITUTE(SUBSTITUTE(UPPER([SourceFileName]), ".XLSM", ""), ".XLSX", ""))
VAR _parsed = ADDCOLUMNS(_stem,
 "_Revision", VAR _s = [_Stem] VAR _p = SEARCH("_ADS_", _s, 1, 0)
  VAR _tail = TRIM(IF(_p > 0, MID(_s, _p + 5, LEN(_s))))
  VAR _digits = IF(LEFT(_tail, 1) IN {"+", "-"}, MID(_tail, 2, LEN(_tail)), _tail)
  VAR _valid = LEN(_digits) > 0 && COUNTROWS(FILTER(GENERATESERIES(1, MAX(1, LEN(_digits))),
   NOT (MID(_digits, [Value], 1) IN {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}))) = 0
  RETURN IF(_p > 0 && _valid, IFERROR(CONVERT(_tail, INTEGER), BLANK())),
 "_Imported", VAR _label = [FileLabel] VAR _p = SEARCH(" · Imported ", _label, 1, 0)
  VAR _tail = IF(_p > 0, MID(_label, _p + 12, LEN(_label)))
  VAR _end = SEARCH(" · ", _tail, 1, 0)
  VAR _iso = IF(_end > 0, LEFT(_tail, _end - 1), _tail)
  VAR _date = IFERROR(DATE(VALUE(LEFT(_iso, 4)), VALUE(MID(_iso, 6, 2)),
   VALUE(MID(_iso, 9, 2))), BLANK())
  VAR _time = IFERROR(TIME(VALUE(MID(_iso, 12, 2)), VALUE(MID(_iso, 15, 2)),
   VALUE(MID(_iso, 18, 2))), BLANK())
  VAR _zone = MAX(SEARCH("+", _iso, 20, 0), SEARCH("-", _iso, 20, 0))
  VAR _offset = IF(_zone > 0,
   IFERROR((VALUE(MID(_iso, _zone + 1, 2)) * 60 + VALUE(MID(_iso, _zone + 4, 2))) / 1440, 0), 0)
  VAR _fraction = IF(MID(_iso, 20, 1) = ".",
   IFERROR(VALUE("0" & MID(_iso, 20, IF(_zone > 0, _zone - 20,
    LEN(SUBSTITUTE(_iso, "Z", "")) - 19))) / 86400, 0), 0)
  RETURN IF(_p > 0 && NOT ISBLANK(_date) && NOT ISBLANK(_time),
   _date + _time + _fraction - IF(_zone > 0 && MID(_iso, MAX(1, _zone), 1) = "-", -_offset, _offset)))
VAR _versions = ADDCOLUMNS(_parsed,
 "ADSPriority", SWITCH(TRUE(),
  RIGHT([_Stem], 9) IN {"_PLAN_ADS", "_PLAN-ADS", "_PLAN ADS"}
   || RIGHT([_Stem], 8) = "_PLANADS", 3,
  RIGHT([_Stem], 4) = "_ADS", 2,
  NOT ISBLANK([_Revision]) && [_Revision] = INT([_Revision]), 1, 0),
 "ADSRevision", COALESCE([_Revision], 0),
 "Scenario", VAR _s = [_Stem] VAR _ims = SEARCH("_IMS", _s, 1, 0)
  VAR _start = IF(_ims > 0, SEARCH("_", _s, _ims + 4, 0), 0)
  RETURN IF(_start > 0, MID(_s, _start + 1, 200), _s))
VAR _ranked = ADDCOLUMNS(_versions,
 "PreferenceRank", VAR _c = [Country] VAR _cycle = [DemandCycle] VAR _driver = [GrowthDriver]
  VAR _p = [ADSPriority] VAR _r = [ADSRevision] VAR _i = [_Imported]
  RETURN 1 + COUNTROWS(DISTINCT(SELECTCOLUMNS(FILTER(_versions,
   [Country] = _c && [DemandCycle] = _cycle && [GrowthDriver] = _driver
   && ([ADSPriority] > _p || ([ADSPriority] = _p && [ADSRevision] > _r)
    || ([ADSPriority] = _p && [ADSRevision] = _r && [_Imported] > _i))),
   "P", [ADSPriority], "R", [ADSRevision], "I", [_Imported]))),
 "PreferenceTies", VAR _c = [Country] VAR _cycle = [DemandCycle] VAR _driver = [GrowthDriver]
  VAR _p = [ADSPriority] VAR _r = [ADSRevision] VAR _i = [_Imported]
  RETURN COUNTROWS(FILTER(_versions, [Country] = _c && [DemandCycle] = _cycle
   && [GrowthDriver] = _driver && [ADSPriority] = _p && [ADSRevision] = _r
   && [_Imported] == _i)))
RETURN SELECTCOLUMNS(_ranked,
 "SourceRevisionID", [SourceRevisionID], "SourceFileName", [SourceFileName],
 "SourceRelativePath", [SourceRelativePath], "Country", [Country],
 "DemandCycle", [DemandCycle], "GrowthDriver", [GrowthDriver],
 "IMSActualsThrough", [IMSActualsThrough], "ExFactoryActualsThrough", [ExFactoryActualsThrough],
 "PublicationStatus", [PublicationStatus], "FileLabel", [FileLabel],
 "ADSPriority", [ADSPriority], "ADSRevision", [ADSRevision],
 "PreferenceRank", [PreferenceRank], "PreferenceTies", [PreferenceTies], "Scenario", [Scenario])
'''

SCOPE = r'''
VAR _pairs = DISTINCT(SELECTCOLUMNS('fm_review_facts',
 "_Source", [SourceRevisionID], "_Sector", COALESCE([Sector], "")))
VAR _files = SELECTCOLUMNS('fm_native_files',
 "SourceRevisionID", [SourceRevisionID], "Country", [Country],
 "DemandCycle", [DemandCycle], "GrowthDriver", [GrowthDriver])
RETURN GENERATE(_files, VAR _id = [SourceRevisionID] VAR _driver = [GrowthDriver]
 RETURN SELECTCOLUMNS(FILTER(_pairs, [_Source] = _id),
 "Sector", [_Sector], "SectorLabel", IF(LEN([_Sector]) = 0, "No forecast tier", [_Sector]) & " – " & _driver))
'''

GROUPS = r'''
DISTINCT(UNION(
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Total",
  "ScopeDriver", "", "ScopeSector", "", "ScopeLabel", "Selected total", "IsSector", 0),
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Drivers",
  "ScopeDriver", [GrowthDriver], "ScopeSector", "", "ScopeLabel", [GrowthDriver], "IsSector", 0),
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Sectors",
  "ScopeDriver", [GrowthDriver], "ScopeSector", [Sector], "ScopeLabel", [SectorLabel], "IsSector", 1),
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Both",
  "ScopeDriver", [GrowthDriver], "ScopeSector", "", "ScopeLabel", [GrowthDriver], "IsSector", 0),
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Both",
  "ScopeDriver", [GrowthDriver], "ScopeSector", [Sector], "ScopeLabel", [SectorLabel], "IsSector", 1)))
'''

SCENARIO = r'''
UNION(ROW("Mode", "Automatic ADS", "Scenario", "Automatic ADS"),
 DISTINCT(SELECTCOLUMNS('fm_native_files', "Mode", "Selected files", "Scenario", [Scenario])))
'''

LINES = r'''
VAR _groups = CROSSJOIN('fm_native_groups', 'fm_native_scenario')
VAR _demand = CROSSJOIN(_groups, 'fm_native_display',
 DATATABLE("K", INTEGER, {{0}, {1}, {6}, {12}, {24}}))
VAR _sop = CROSSJOIN(_groups, 'fm_native_catalog', DATATABLE("K", INTEGER, {{0}, {1}}))
RETURN UNION(
 SELECTCOLUMNS(_demand,
 "DemandCycle", [DemandCycle], "ViewType", [ViewType], "ScopeDriver", [ScopeDriver],
 "ScopeSector", [ScopeSector], "ScopeLabel", [ScopeLabel], "IsSector", [IsSector],
 "Mode", [Mode], "Scenario", [Scenario], "Chart", "demand", "Token", "none", "RowID", "",
 "Display", [Display], "LineKind", [K],
 "LineLabel", [DemandCycle] & " · " & [Scenario] & " · " & [ScopeLabel] & " · " &
 SWITCH([K], 0, "Actuals", 1, "Forecast", [K] & "M trend"), "LineSort", [K]),
 SELECTCOLUMNS(_sop,
 "DemandCycle", [DemandCycle], "ViewType", [ViewType], "ScopeDriver", [ScopeDriver],
 "ScopeSector", [ScopeSector], "ScopeLabel", [ScopeLabel], "IsSector", [IsSector],
 "Mode", [Mode], "Scenario", [Scenario], "Chart", "sop", "Token", "", "RowID", [RowID],
 "Display", [Display], "LineKind", [K],
 "LineLabel", [DemandCycle] & " · " & [Scenario] & " · " & [ScopeLabel] & " · " &
 [Channel] & " · " & IF(LEN([SubChannel]) = 0, "—", [SubChannel]) & " · " &
 [Measure] & " · " & IF([K] = 0, "Actuals", "Forecast"), "LineSort", [SourceOrder] * 100 + [K]))
'''

EXPRESSIONS = {"files": FILES, "scope": SCOPE, "groups": GROUPS, "scenario": SCENARIO, "lines": LINES}


def static_tables(currencies=("GBP",)):
    """Enumerated filter tokens encode user preferences, never business amounts.

    Rank tokens allow independent sibling permutations. FX uses six three-digit
    chunks plus a decimal exponent instead of a sampled what-if parameter.
    The custom control filters Token; native DAX and visuals consume that state.
    """
    catalog = catalog_rows()
    state = []
    zw = "\u200b"
    for r in catalog:
        for c in range(5):
            for s in range(7):
                for m in range(6):
                    state.append(dict(Token=f"row:{r['RowID']}:{r['Display']}:{c}:{s}:{m}", Kind="row",
                                      RowID=r["RowID"], Display=r["Display"], Currency="", Position=-1, Digit=0,
                                      Channel=r["Channel"] + zw*c, SubChannel=(r["SubChannel"] or "—") + zw*s,
                                      Measure=r["Measure"] + zw*m, ChannelRank=c, SubRank=s, MeasureRank=m,
                                      RowRank=c*1000+s*10+m))
    for currency in currencies:
        if currency == "USD":
            continue
        for pos in range(7):
            digits = range(-341, 309) if pos == 6 else range(1000)
            for digit in digits:
                state.append(dict(Token=f"fx:{currency}:{pos}:{digit}", Kind="fx", RowID="", Display="",
                                  Currency=currency, Position=pos, Digit=digit, Channel="", SubChannel="", Measure="",
                                  ChannelRank=0, SubRank=0, MeasureRank=0, RowRank=0))
    state.append(dict(Token="none", Kind="empty", RowID="", Display="", Currency="", Position=-1, Digit=0,
                      Channel="", SubChannel="", Measure="", ChannelRank=0, SubRank=0, MeasureRank=0, RowRank=0))
    def preference(token):
        state.append(dict(Token=token,Kind='prefs',RowID='',Display='',Currency='',Position=-1,Digit=0,
                          Channel='',SubChannel='',Measure='',ChannelRank=0,SubRank=0,MeasureRank=0,RowRank=0))
    for channel in dict.fromkeys(r['Channel'] for r in catalog):preference('saved-channel:'+channel)
    for channel,sub in dict.fromkeys((r['Channel'],r['SubChannel']) for r in catalog):
        preference('saved-context:'+json.dumps([channel,sub],ensure_ascii=False,separators=(',',':')))
    for key in ORDER:
        preference('saved-row:'+key)
        for c in range(5):
            for s in range(7):
                for rank in range(6):preference(f'order:{key}:{c}:{s}:{rank}')
    cols = [dict(ColumnKey="plan", Comparison="Total Plan", ValueLabel=" ", Window=0, Sort=0)]
    for window in (6, 12, 24):
        for typ, label, i in (("abs", "Absolute", 0), ("pct", "%", 1)):
            cols.append(dict(ColumnKey=f"{window}:{typ}", Comparison=f"{window}M variance", ValueLabel=label,
                             Window=window, Sort=window*10+i))
    return {
        "catalog": catalog, "state": state, "rows": [r.copy() for r in state if r["Kind"]=="row"],
        "display": [{"Display": "Units"}, {"Display": "Value"}],
        "currency": [{"Currency": "USD"}, {"Currency": "Local"}],
        "currency_map": [{"Country": "UK", "Currency": "GBP"},{"Country":"United Kingdom","Currency":"GBP"}],
        "trend": [{"Window": i, "Label": f"{i}M"} for i in (6, 12, 24)],
        "chart_trend": [{"Window": i, "Label": f"{i}M"} for i in (6,12,24)],
        "view": [{"View": x} for x in ("Total", "Drivers", "Sectors", "Both")],
        "file_mode": [{"Mode": "Automatic ADS"}, {"Mode": "Selected files"}],
        "columns": cols,
        "run_rate": [{"Show": "Off"}, {"Show": "On"}],
        "growth": [{"Show": "Off"}, {"Show": "On"}],
        "measures": [{"ID": 1}],
        "metric": [dict(RowID=k,MetricLabel=v,Section='Ex-factory' if k=='ef' else 'IMS / Market') for k,v in
                   [('market','Market'),('abbott','Abbott IMS'),('share','Share %'),('pi','PI'),('net','IMS minus PI'),('ef','Ex-factory ADS')]],
    }

def measures():
    """A table of reusable scalar DAX measures with native numeric formats."""
    d = {}
    def add(name, expression, fmt="#,0.00;−#,0.00;0"):
        d[name] = dict(name=name, expression=expression, formatString=fmt,
                       displayFolder="Native review", description="R17 candidate; receiving DAX qualification required.")
    add("N Display", 'SELECTEDVALUE(\'fm_native_display\'[Display],"Units")', "")
    add("N Catalog Visible", "IF(SELECTEDVALUE('fm_native_catalog'[Display])=[N Display],1)", "0")
    add("N Catalog Available", SOURCES+"""VAR _admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)
VAR _candidateIds=SELECTCOLUMNS(_admitted,"ID",'fm_native_files'[SourceRevisionID])
VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])
VAR _component=SELECTEDVALUE('fm_native_catalog'[Component])
VAR _channel=SELECTEDVALUE('fm_native_catalog'[Channel]) VAR _sub=SELECTEDVALUE('fm_native_catalog'[SubChannel])
RETURN IF(COUNTROWS(FILTER(ALL('fm_review_facts'),'fm_review_facts'[SourceRevisionID] IN _candidateIds
 && 'fm_review_facts'[ComponentKey]=_component && 'fm_review_facts'[Channel]=_channel
 && COALESCE('fm_review_facts'[SubChannel],"")=_sub))>0,1)""", "0")
    add("N Source Caption", SOURCES+"""VAR _ims=SUMMARIZE(_files,'fm_native_files'[IMSActualsThrough])
VAR _ef=SUMMARIZE(_files,'fm_native_files'[ExFactoryActualsThrough])
RETURN IF(NOT _sourceOK,"Choose an available source for every selected driver.",
 IF(_custom,"Selected versions","ADS automatic")&" · "&FORMAT(COUNTROWS(_files),"0")&" source(s) · IMS through "&
 IF(COUNTROWS(_ims)=1,FORMAT(MAXX(_ims,'fm_native_files'[IMSActualsThrough]),"mmm yy"),"mixed cutoffs")&
 " · Ex-factory through "&IF(COUNTROWS(_ef)=1,FORMAT(MAXX(_ef,'fm_native_files'[ExFactoryActualsThrough]),"mmm yy"),"mixed cutoffs"))""", "")
    add("N Source OK", SOURCES + "RETURN INT(_sourceOK)", "0")
    add("N Scenario Visible", "IF(SELECTEDVALUE('fm_native_scenario'[Mode])=SELECTEDVALUE('fm_native_file_mode'[Mode],\"Automatic ADS\")&&[N Source OK]=1,1)", "0")
    add("N Scope Available", SOURCES + """VAR _admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)
VAR _candidateIds=SELECTCOLUMNS(_admitted,"ID",'fm_native_files'[SourceRevisionID])
VAR _sectors=VALUES('fm_native_scope'[Sector])
RETURN IF(COUNTROWS(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN _candidateIds))>0
 && CALCULATE(COUNTROWS('fm_review_facts'),TREATAS(_candidateIds,'fm_review_facts'[SourceRevisionID]),TREATAS(_sectors,'fm_review_facts'[Sector]))>0,1)""", "0")
    add("N Period Available", """VAR _y=SELECTEDVALUE('fm_review_periods'[Year])
RETURN IF(_y>=YEAR(MIN('fm_review_months'[Month])) && _y<=YEAR(MAX('fm_review_months'[Month])),1)""", "0")
    add("N Cutoff", SOURCES + """VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID],"market")
VAR _ef=IF(_row IN {"share","abbott","market","pi","net"},FALSE(),TRUE())
VAR _dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,'fm_native_files'[ExFactoryActualsThrough],'fm_native_files'[IMSActualsThrough]))
RETURN IF(_sourceOK && COUNTROWS(DISTINCT(_dates))=1,MAXX(_dates,[Cutoff]))""", "mmm yyyy")
    # Numerator and denominator have independent available populations, including FX.
    # Month-level required source guards remain; never substitute a zero for a gap.
    for part in ("Numerator", "Denominator"):
        add("N Monthly " + part, SOURCES + f"""VAR _date=SELECTEDVALUE('fm_review_axis'[Month])
VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID],"market")
VAR _display=[N Display]
VAR _definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row && 'fm_native_catalog'[Display]=_display)
VAR _component=IF(_row="ef",{ '"ef-ads-" & LOWER(_display)' if part=='Numerator' else '""'},MAXX(_definition,'fm_native_catalog'[{ 'Component' if part=='Numerator' else 'Denominator'}]))
VAR _channel=IF(_row="ef","*",MAXX(_definition,'fm_native_catalog'[Channel]))
VAR _sub=IF(_row="ef","*",MAXX(_definition,'fm_native_catalog'[SubChannel]))
VAR _value=_display="Value"
VAR _usd=SELECTEDVALUE('fm_native_currency'[Currency],"USD")="USD"
VAR _currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],'fm_native_files'[Country]))
VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 && COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0
VAR _convert=_value && _usd && (_row<>"share" || NOT _singleCurrency)
VAR _selectedChannels=VALUES('fm_review_facts'[Channel])
VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])
VAR _fx=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),'fm_native_state'[Kind]="fx")
VAR _members=GENERATE(_files,
 VAR _id='fm_native_files'[SourceRevisionID]
 VAR _gd='fm_native_files'[GrowthDriver]
 VAR _cc='fm_native_files'[Country]
 VAR _currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)
 VAR _digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)
 VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 && COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,
  VAR _exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])
  VAR _half=INT(_exponent/2)
  RETURN SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*
  POWER(10,_half)*POWER(10,_exponent-_half)))
 VAR _sectors=SELECTCOLUMNS(FILTER(_scope,'fm_native_scope'[GrowthDriver]=_gd),"Sector",'fm_native_scope'[Sector])
 RETURN ADDCOLUMNS(ADDCOLUMNS(_sectors,"RawAmount",
  VAR _sec=[Sector]
  VAR _facts=FILTER(ALL('fm_review_facts'),'fm_review_facts'[SourceRevisionID]=_id && 'fm_review_facts'[Month]=_date
   && 'fm_review_facts'[Sector]=_sec && (_channel="*" || 'fm_review_facts'[Channel]=_channel)
   && (_sub="*" || COALESCE('fm_review_facts'[SubChannel],"")=_sub)
   && (_channel<>"*" || 'fm_review_facts'[Channel] IN _selectedChannels && 'fm_review_facts'[SubChannel] IN _selectedSubs)
   && 'fm_review_facts'[ComponentKey]=_component)
  VAR _amount=IF(COUNTROWS(_facts)>0 && COUNTROWS(FILTER(_facts,'fm_review_facts'[MissingCells]<>0 || ISBLANK('fm_review_facts'[Amount])))=0,SUMX(_facts,'fm_review_facts'[Amount]))
  RETURN _amount),"Amount",IF(_convert,IF(NOT ISBLANK([RawAmount])&&NOT ISBLANK(_rate),IFERROR([RawAmount]*_rate,BLANK())),[RawAmount]),
  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) && (ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))
VAR _available=FILTER(_members,NOT ISBLANK([Amount]))
VAR _localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))
RETURN IF(_sourceOK && NOT ISBLANK(_date) && LEN(_component)>0 && COUNTROWS(_available)>0
 && SUMX(_members,[FXMissing])=0 && (NOT _value || COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)
 && (NOT _value || _usd || COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))""")
    add("N Monthly", """VAR _n=[N Monthly Numerator] VAR _d=[N Monthly Denominator]
RETURN IF(SELECTEDVALUE('fm_native_catalog'[RowID],"market")="share",DIVIDE(_n,_d),_n)""")
    add("N Trend Monthly", """VAR _cut=[N Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _m=SELECTEDVALUE('fm_review_axis'[Month])
VAR _dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Date",EDATE(_cut,[Value]-_w),"X",[Value])
VAR _train=ADDCOLUMNS(_dates,"Y",VAR _d=[Date] RETURN CALCULATE([N Monthly],REMOVEFILTERS('fm_review_axis'),TREATAS({_d},'fm_review_axis'[Month])))
VAR _valid=FILTER(_train,NOT ISBLANK([Y]))
VAR _mx=AVERAGEX(_train,[X]) VAR _my=AVERAGEX(_train,[Y])
VAR _slope=DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_my)),SUMX(_train,POWER([X]-_mx,2)))
RETURN IF(NOT ISBLANK(_m)&&NOT ISBLANK(_cut),IF(_m<=_cut,[N Monthly],
 IF(COUNTROWS(_valid)=_w,_my+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-_mx))))""")
    add("N Period Months", """VAR _y=SELECTEDVALUE('fm_review_periods'[Year])
VAR _kind=SELECTEDVALUE('fm_review_periods'[PeriodType]) VAR _cut=[N Cutoff]
VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)
VAR _start=IF(_kind="YTG",MAX(_first,EDATE(_cut,1)),_first)
VAR _end=IF(_kind="YTD",MIN(_last,_cut),_last)
RETURN IF(NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_end>=_start,DATEDIFF(_start,_end,MONTH)+1)""", "0")
    for name, trend in (("N Plan", False), ("N Benchmark", True)):
        add(name, f"""VAR _y=SELECTEDVALUE('fm_review_periods'[Year])
VAR _kind=SELECTEDVALUE('fm_review_periods'[PeriodType]) VAR _cut=[N Cutoff]
VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)
VAR _start=IF(_kind="YTG",MAX(_first,EDATE(_cut,1)),_first)
VAR _end=IF(_kind="YTD",MIN(_last,_cut),_last)
VAR _count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)
VAR _months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]))
VAR _values=ADDCOLUMNS(_months,"N",VAR _m=[Date] RETURN
 CALCULATE({'IF(_m>_cut,IF(SELECTEDVALUE(\'fm_native_catalog\'[RowID],"market")="share",[N Trend Monthly]*[N Monthly Denominator],[N Trend Monthly]),[N Monthly Numerator])' if trend else '[N Monthly Numerator]'},REMOVEFILTERS('fm_review_axis'),TREATAS({{_m}},'fm_review_axis'[Month])),
 "D",VAR _m=[Date] RETURN CALCULATE([N Monthly Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({{_m}},'fm_review_axis'[Month])))
VAR _valid=COUNTROWS(FILTER(_values,NOT ISBLANK([N])))=_count
VAR _ratio=SELECTEDVALUE('fm_native_catalog'[RowID],"market")="share"
RETURN IF(NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_valid,
 IF(_ratio,IF(COUNTROWS(FILTER(_values,NOT ISBLANK([D])))=_count,DIVIDE(SUMX(_values,[N]),SUMX(_values,[D]))),SUMX(_values,[N])))""")
    add("N Variance", "VAR _p=[N Plan] VAR _t=[N Benchmark] RETURN IF(NOT ISBLANK(_p)&&NOT ISBLANK(_t),_p-_t)")
    add("N Variance %", "DIVIDE([N Variance],[N Benchmark])", "+0.0%;−0.0%;0.0%")
    for suffix,base in [('Variance','N Variance'),('Variance %','N Variance %')]:
        add('N Headline '+suffix,f"""VAR _w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)
VAR _year=SELECTEDVALUE('fm_review_periods'[Year])
VAR _actual=SELECTEDVALUE('fm_review_periods'[PeriodType])="YTD" || DATE(_year,12,1)<=[N Cutoff]
RETURN IF(NOT _actual,CALCULATE([{base}],REMOVEFILTERS('fm_native_trend'),TREATAS({{_w}},'fm_native_trend'[Window])))""",
           "+0.0%;−0.0%;0.0%" if suffix.endswith('%') else '#,0.00;−#,0.00;0')
    add("N Summary Cell", """VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _w=SELECTEDVALUE('fm_native_columns'[Window])
VAR _allowed=_w=0 || _w IN VALUES('fm_native_trend'[Window])
VAR _actualOnly=SELECTEDVALUE('fm_review_periods'[PeriodType])="YTD" ||
 DATE(SELECTEDVALUE('fm_review_periods'[Year]),12,1)<=[N Cutoff]
RETURN IF([N Period Available]=1&&_allowed,SWITCH(TRUE(),_key="plan",[N Plan],_actualOnly,BLANK(),
 RIGHT(_key,3)="abs",CALCULATE([N Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])),
 CALCULATE([N Variance %],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window]))))""")
    add("N Run Rate", """IF(SELECTEDVALUE('fm_native_run_rate'[Show],"Off")="On" && SELECTEDVALUE('fm_native_catalog'[RunRate],0)=1,
 DIVIDE([N Plan],[N Period Months]))""")
    # Same-month PY is explicit and independent of review-month slicer.
    add("N Growth %", """VAR _y=SELECTEDVALUE('fm_review_periods'[Year])
VAR _kind=SELECTEDVALUE('fm_review_periods'[PeriodType]) VAR _cut=[N Cutoff]
VAR _start=IF(_kind="YTG",MAX(DATE(_y,1,1),EDATE(_cut,1)),DATE(_y,1,1))
VAR _end=IF(_kind="YTD",MIN(DATE(_y,12,1),_cut),DATE(_y,12,1))
VAR _count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)
VAR _months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]-12))
VAR _values=ADDCOLUMNS(_months,"PY",VAR _m=[Date] RETURN CALCULATE([N Monthly Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])))
VAR _py=IF(_count>0 && COUNTROWS(FILTER(_values,NOT ISBLANK([PY])))=_count,SUMX(_values,[PY]))
RETURN IF(SELECTEDVALUE('fm_native_growth'[Show],"Off")="On"&&SELECTEDVALUE('fm_native_catalog'[Growth],0)=1,
 IF(NOT ISBLANK([N Plan])&&NOT ISBLANK(_py),DIVIDE([N Plan]-_py,_py)))""", "+0.0%;−0.0%;0.0%")
    add("N SOP Row Selected", """VAR _token=SELECTEDVALUE('fm_native_rows'[Token])
RETURN IF(ISFILTERED('fm_native_state'[Token]) && SELECTEDVALUE('fm_native_rows'[Kind])="row"
 && SELECTEDVALUE('fm_native_rows'[Display])=[N Display],1)""", "0")
    for suffix, calc in (("Plan", "N Plan"), ("Run Rate", "N Run Rate"), ("Growth %", "N Growth %"), ("Monthly", "N Monthly")):
        add("N SOP " + suffix, f"""VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])
RETURN IF([N SOP Row Selected]=1,CALCULATE([{calc}],TREATAS({{_row}},'fm_native_catalog'[RowID]),TREATAS({{[N Display]}},'fm_native_catalog'[Display])))""",
            "+0.0%;−0.0%;0.0%" if suffix == "Growth %" else "#,0.00;−#,0.00;0")
    add('N SOP Monthly Growth %', """VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])
VAR _month=SELECTEDVALUE('fm_review_axis'[Month])
VAR _allowed=MAXX(FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row),'fm_native_catalog'[Growth])=1
VAR _current=CALCULATE([N Monthly Numerator],TREATAS({_row},'fm_native_catalog'[RowID]))
VAR _prior=CALCULATE([N Monthly Numerator],TREATAS({_row},'fm_native_catalog'[RowID]),REMOVEFILTERS('fm_review_axis'),TREATAS({EDATE(_month,-12)},'fm_review_axis'[Month]))
RETURN IF([N SOP Row Selected]=1&&_allowed&&SELECTEDVALUE('fm_native_growth'[Show],"Off")="On"
 &&_month>=MIN('fm_review_months'[Month])&&_month<=MAX('fm_review_months'[Month])
 &&NOT ISBLANK(_current)&&NOT ISBLANK(_prior),DIVIDE(_current-_prior,_prior))""", "+0.0%;−0.0%;0.0%")
    add("N Export Selected", """VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])
VAR _display=[N Display]
VAR _chosen=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),
 'fm_native_state'[Kind]="row"&&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display)
RETURN IF(ISFILTERED('fm_native_state'[Token])&&COUNTROWS(_chosen)=1,1)""", "0")
    for suffix,calc in (("Plan","N Plan"),("Run Rate","N Run Rate"),("Growth %","N Growth %")):
        add('N Export '+suffix,f'IF([N Export Selected]=1,[{calc}])',
            "+0.0%;−0.0%;0.0%" if suffix=='Growth %' else '#,0.00;−#,0.00;0')
    add("N Export Order", """VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])
VAR _display=[N Display]
VAR _chosen=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),
 'fm_native_state'[Kind]="row"&&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display)
RETURN IF([N Export Selected]=1,MINX(_chosen,'fm_native_state'[RowRank]))""", "0")
    add('N Export Monthly', """VAR _m=SELECTEDVALUE('fm_review_axis'[Month]) RETURN IF([N Export Selected]=1
 &&_m>=MIN('fm_review_months'[Month])&&_m<=MAX('fm_review_months'[Month]),[N Monthly])""")
    add('N Export Month Stage', """VAR _m=SELECTEDVALUE('fm_review_axis'[Month]) VAR _cut=[N Cutoff]
RETURN IF([N Export Selected]=1&&NOT ISBLANK(_m)&&NOT ISBLANK(_cut),IF(_m<=_cut,"Actual","Forecast"))""", '')
    add("N Chart Monthly", """VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])
VAR _gd=SELECTEDVALUE('fm_native_lines'[ScopeDriver]) VAR _sec=SELECTEDVALUE('fm_native_lines'[ScopeSector])
VAR _sectorLevel=SELECTEDVALUE('fm_native_lines'[IsSector],0)=1
VAR _cyc=SELECTEDVALUE('fm_native_lines'[DemandCycle]) VAR _type=SELECTEDVALUE('fm_native_lines'[Chart])
VAR _row=IF(_type="sop",SELECTEDVALUE('fm_native_lines'[RowID]),SELECTEDVALUE('fm_native_catalog'[RowID],"market"))
VAR _token=SELECTEDVALUE('fm_native_lines'[Token])
VAR _selected=_type="demand" || _token IN SELECTCOLUMNS(ALLSELECTED('fm_native_state'),"T",'fm_native_state'[Token]) && ISFILTERED('fm_native_state'[Token])
VAR _scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)&&(NOT _sectorLevel||'fm_native_scope'[Sector]=_sec))
VAR _month=SELECTEDVALUE('fm_review_axis'[Month])
VAR _within=_month>=MIN('fm_review_months'[Month])&&_month<=MAX('fm_review_months'[Month])
VAR _mode=SELECTEDVALUE('fm_native_lines'[Mode])=SELECTEDVALUE('fm_native_file_mode'[Mode],"Automatic ADS")
VAR _base=CALCULATE([N Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))
VAR _cut=CALCULATE([N Cutoff],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))
RETURN IF(_mode&&_within&&_selected&&COUNTROWS(_scope)>0&&SELECTEDVALUE('fm_native_lines'[ViewType]) IN VALUES('fm_native_view'[View]),
 SWITCH(TRUE(),_kind=0&&_month<=_cut,_base,_kind=1&&_month>_cut,_base,
 _kind IN {6,12,24}&&_month>=_cut&&_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12),
 CALCULATE([N Trend Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]),REMOVEFILTERS('fm_native_trend'),TREATAS({_kind},'fm_native_trend'[Window]))))""")
    add("N Chart Amount", "IF(SELECTEDVALUE('fm_native_lines'[RowID])<>\"share\",[N Chart Monthly])")
    add("N Chart Share", "IF(SELECTEDVALUE('fm_native_lines'[RowID])=\"share\",[N Chart Monthly])", "0.0%")
    add("N Status", """SWITCH(TRUE(),[N Source OK]<>1,"Select a valid ADS source for each selected cohort. Check Matching files.",
 ISBLANK([N Cutoff]),"Selected sources have different cutoffs; compare them separately.",
 "Saved ADS · IMS / EF calendars retained · Native R17 candidate")""", "")
    add('N Variance Color', """VAR _value=[N Summary Cell] RETURN IF(SELECTEDVALUE('fm_native_columns'[ColumnKey])="plan"||ISBLANK(_value)||_value=0,"#17384D",IF(_value>0,"#087D88","#AC640C"))""", '')
    # Native dynamic formatting preserves numeric values for export.
    for key, value in d.items():
        if not key.endswith('Color') and key not in {"N Display", "N Source Caption", "N Catalog Visible", "N Catalog Available", "N Source OK", "N Scenario Visible", "N Scope Available", "N Period Available", "N Cutoff", "N Period Months", "N SOP Row Selected", "N Export Selected", "N Export Order", "N Export Month Stage", "N Export Growth %", "N Status", "N Variance %", "N Headline Variance %", "N Growth %", "N SOP Growth %", "N SOP Monthly Growth %", "N Chart Share"}:
            value["formatStringDefinition"] = {"expression": """VAR _row=COALESCE(SELECTEDVALUE('fm_native_rows'[RowID]),SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _pct=RIGHT(SELECTEDVALUE('fm_native_columns'[ColumnKey],""),3)="pct"
VAR _countries=VALUES('fm_review_files'[Country])
VAR _ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] IN _countries),'fm_native_currency_map'[Currency])
RETURN IF(_pct||_row="share","0.0%;−0.0%;0.0%",IF([N Display]="Units","#,0.00;−#,0.00;0",
 IF(SELECTEDVALUE('fm_native_currency'[Currency],"USD")="USD","$#,0.00;−$#,0.00;$0",
 SWITCH(_ccy,"GBP","£#,0.00;−£#,0.00;£0","EUR","€#,0.00;−€#,0.00;€0","USD","$#,0.00;−$#,0.00;$0","#,0.00;−#,0.00;0"))))"""}
            value.pop("formatString",None)
    for value in d.values():
        value['expression']=value['expression'].replace("SELECTEDVALUE('fm_native_catalog'[RowID],\"market\")", "COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),\"market\")")
        value['isHidden']=value['name'] not in {'N Plan','N Variance','N Variance %','N SOP Plan','N SOP Run Rate','N SOP Growth %','N SOP Monthly','N SOP Monthly Growth %'}
    monthly=next(v for k,v in d.items() if k=='N SOP Monthly')
    monthly['expression']=monthly['expression'].replace('IF([N SOP Row Selected]=1,', "IF([N SOP Row Selected]=1 && SELECTEDVALUE('fm_review_axis'[Month])>=MIN('fm_review_months'[Month]) && SELECTEDVALUE('fm_review_axis'[Month])<=MAX('fm_review_months'[Month]),")
    return list(d.values())

def columns_for(rows):
    sample = rows[0]
    return [dict(name=k, dataType="int64" if isinstance(v, int) else "string", sourceColumn=k,
                 summarizeBy="none") for k, v in sample.items()]

def native_table(name, columns, template_partition):
    p = deepcopy(template_partition)
    if p.get("mode") != "directLake" or p.get("source", {}).get("type") != "entity":
        raise ValueError("R17 installer supports the existing Direct Lake entity source only; no storage mode conversion is allowed.")
    p["name"] = name
    p["source"]["entityName"] = name
    p["source"]["schemaName"] = "dbo"
    p.pop("annotations", None)
    t = dict(name=name, columns=deepcopy(columns), partitions=[p], description="Native R17 additive reporting metadata.")
    return t

def extend_model(database, currencies=("GBP",)):
    """Pure additive definition transform; refuses conflicting objects.

    Existing tables, roles, expressions, relationships and model settings are
    retained byte-for-byte at their JSON value level. No purge or RLS removal.
    """
    after = deepcopy(database)
    model = after["model"]
    tables = model["tables"]
    by_name = {t["name"]: t for t in tables}
    if any(n.startswith(PREFIX) for n in by_name):
        raise ValueError("Native model objects already exist. Inspect retained receipt; do not overwrite them blindly.")
    source = by_name["fm_review_facts"]["partitions"]
    if len(source) != 1:
        raise ValueError("Expected one existing fact partition; source layout must be inspected.")
    added = []
    for short, rows in static_tables(currencies).items():
        t = native_table(PREFIX+short, columns_for(rows), source[0])
        if short == "measures":
            t['columns'][0]['isHidden']=True
            t["measures"] = measures()
        if short in {"state","rows"}:
            for c in t["columns"]:
                if c["name"] in {"Channel", "SubChannel", "Measure"}:
                    c["sortByColumn"] = {"Channel":"ChannelRank","SubChannel":"SubRank","Measure":"MeasureRank"}[c["name"]]
        if short == "columns":
            for c in t["columns"]:
                if c["name"] == "ColumnKey": c["sortByColumn"] = "Sort"
        added.append(t)
    view_columns = {
        "files": {k:c for k,c in {**{x:"string" for x in ("SourceRevisionID","SourceFileName","SourceRelativePath","Country","DemandCycle","GrowthDriver","PublicationStatus","FileLabel","Scenario")},
                  "IMSActualsThrough":"dateTime","ExFactoryActualsThrough":"dateTime",**{x:"int64" for x in ("ADSPriority","ADSRevision","PreferenceRank","PreferenceTies")}}.items()},
        "scope": {x:"string" for x in ("SourceRevisionID","Country","DemandCycle","GrowthDriver","Sector","SectorLabel")},
        "groups": {**{x:"string" for x in ("DemandCycle","ViewType","ScopeDriver","ScopeSector","ScopeLabel")},"IsSector":"int64"},
        "scenario": {"Mode":"string","Scenario":"string"},
        "lines": {**{x:"string" for x in ("DemandCycle","ViewType","ScopeDriver","ScopeSector","ScopeLabel","Mode","Scenario","Chart","Token","RowID","Display","LineLabel")},"IsSector":"int64","LineKind":"int64","LineSort":"int64"},
    }
    for short, cols in view_columns.items():
        table=native_table(PREFIX+short,[dict(name=k,dataType=v,sourceColumn=k,summarizeBy="none") for k,v in cols.items()],source[0])
        if short=='lines':
            next(c for c in table['columns'] if c['name']=='LineLabel')['sortByColumn']='LineSort'
        added.append(table)
    tables.extend(added)
    model.setdefault('relationships',[]).extend([
        {'name':'NativeR17-Rows-State','fromTable':'fm_native_rows','fromColumn':'Token','toTable':'fm_native_state','toColumn':'Token'},
        {'name':'NativeR17-Lines-Display','fromTable':'fm_native_lines','fromColumn':'Display','toTable':'fm_native_display','toColumn':'Display'},
        {'name':'NativeR17-Catalog-Display','fromTable':'fm_native_catalog','fromColumn':'Display','toTable':'fm_native_display','toColumn':'Display'},
        {'name':'NativeR17-Lines-State','fromTable':'fm_native_lines','fromColumn':'Token','toTable':'fm_native_state','toColumn':'Token'},
        {'name':'NativeR17-Lines-View','fromTable':'fm_native_lines','fromColumn':'ViewType','toTable':'fm_native_view','toColumn':'View'},
        {'name':'NativeR17-Lines-Mode','fromTable':'fm_native_lines','fromColumn':'Mode','toTable':'fm_native_file_mode','toColumn':'Mode'},
        {'name':'NativeR17-Scenario-Mode','fromTable':'fm_native_scenario','fromColumn':'Mode','toTable':'fm_native_file_mode','toColumn':'Mode'},
    ])
    return after

nm = SimpleNamespace(extend_model=extend_model, static_tables=static_tables)


def datatable(rows):
    """Constant-only DAX metadata. Never accepts a live data frame."""
    types = []
    for key, value in rows[0].items():
        types.extend([json.dumps(key), "INTEGER" if isinstance(value, int) else "STRING"])
    def cell(value):
        return str(value) if isinstance(value, int) else '"' + value.replace('"', '""') + '"'
    records = ["{" + ",".join(cell(row[key]) for key in rows[0]) + "}" for row in rows]
    return "DATATABLE(" + ",".join(types) + ",{\n" + ",\n".join(records) + "\n})"

def extend_onelake(database):
    """Pure additive transform. The caller creates a NEW model, never updates one."""
    original = database["model"]
    fact = next(t for t in original["tables"] if t["name"] == "fm_review_facts")
    if len(fact.get("partitions", [])) != 1:
        raise ValueError("Expected exactly one existing fact partition.")
    partition = fact["partitions"][0]
    source = partition.get("source", {})
    expression = next((e.get("expression", "") for e in original.get("expressions", [])
                       if e["name"] == source.get("expressionSource")), "")
    expression = "\n".join(expression) if isinstance(expression, list) else expression
    if (partition.get("mode") != "directLake" or source.get("type") != "entity"
            or "azurestorage.datalake" not in expression.lower()
            or any(x in expression.lower() for x in ("sql.database", "onelake.sqlanalytics"))):
        raise ValueError("This adapter requires the confirmed Direct Lake on OneLake route.")
    after = nm.extend_model(database)
    old_names = {t["name"] for t in original["tables"]}
    static = nm.static_tables()
    for table in after["model"]["tables"]:
        if table["name"] in old_names:
            continue
        short = table["name"].removeprefix("fm_native_")
        expression = EXPRESSIONS[short] if short in EXPRESSIONS else datatable(static[short])
        table["partitions"] = [{"name": table["name"], "mode": "import",
                                 "source": {"type": "calculated", "expression": expression}}]
        table["description"] = "OneLake R17.1 TEST metadata. Direct Lake calculated-table preview gate."
        for column in table.get("columns", []):
            column["type"] = "calculatedTableColumn"
            column["sourceColumn"] = "[" + column["name"] + "]"
    existing_relationships = deepcopy(original.get("relationships", []))
    added_relationships = after["model"]["relationships"][len(existing_relationships):]
    after["model"]["relationships"] = existing_relationships + [r for r in added_relationships
        if r.get("name") != "NativeR17-Lines-State"]
    measures = next(t for t in after["model"]["tables"] if t["name"] == "fm_native_measures")["measures"]
    chart = next(m for m in measures if m["name"] == "N Chart Monthly")
    old = '''VAR _token=SELECTEDVALUE('fm_native_lines'[Token])
VAR _selected=_type="demand" || _token IN SELECTCOLUMNS(ALLSELECTED('fm_native_state'),"T",'fm_native_state'[Token]) && ISFILTERED('fm_native_state'[Token])'''
    new = '''VAR _display=SELECTEDVALUE('fm_native_lines'[Display])
VAR _selected=_type="demand" || ISFILTERED('fm_native_state'[Token]) && COUNTROWS(
 FILTER(ALLSELECTED('fm_native_state'),'fm_native_state'[Kind]="row"
 &&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display))>0'''
    if chart["expression"].count(old) != 1:
        raise ValueError("R17 chart selection contract changed; inspect before adapting.")
    chart["expression"] = chart["expression"].replace(old, new)
    # Verify all old model JSON values, including roles and original relationships.
    restored = deepcopy(after)
    restored["model"]["tables"] = [t for t in restored["model"]["tables"] if t["name"] in old_names]
    if "relationships" in original:
        restored["model"]["relationships"] = deepcopy(original["relationships"])
    else:
        restored["model"].pop("relationships", None)
    if restored != database:
        raise AssertionError("An existing model value changed.")
    return after


# Creates ONE NEW test semantic model. Never updates/replaces the original model.
# Run only this new code cell in ForecastMaster_GM_Setup, not Run all.
WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
SOURCE_MODEL = "e7af2967-7725-4108-a170-9e490d4e35bb"
TEST_NAME = "ForecastMaster Native OneLake R17.1 - TEST"


def digest(value):
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


def complete(client, response):
    if response.status_code not in {200, 201, 202}:
        try:
            code = response.json().get("errorCode", "UNKNOWN")
        except (ValueError, AttributeError):
            code = "UNKNOWN"
        code = code if isinstance(code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]{0,95}", code) else "UNKNOWN"
        raise RuntimeError("Fabric HTTP " + str(response.status_code)
                           + " (" + code + "). Inspect this run; do not retry a creation blindly.")
    if response.status_code != 202:
        return response.json()
    operation_id = str(UUID(response.headers["x-ms-operation-id"]))
    print("Operation: " + operation_id, flush=True)
    operation = "/v1/operations/" + operation_id
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        delay = max(1, min(30, int(response.headers.get("Retry-After", "5"))))
        time.sleep(min(delay, max(0, deadline - time.monotonic())))
        response = client.get(operation)
        if response.status_code != 200:
            raise RuntimeError("Operation status unavailable. Inspect the operation before retrying.")
        state = response.json().get("status")
        if state == "Succeeded":
            result = client.get(operation + "/result")
            if result.status_code not in {200, 201}:
                raise RuntimeError("Operation succeeded but result is unavailable. Do not recreate it.")
            return result.json()
        if state in {"Failed", "Cancelled", "Canceled"}:
            raise RuntimeError("Operation " + state + ". Inspect its details in Fabric; keep the original model.")
    raise TimeoutError("Operation unconfirmed. Check the TEST model and this operation before any retry.")


def read_definition(client, model_id):
    path = f"/v1/workspaces/{WORKSPACE}/semanticModels/{str(UUID(model_id))}/getDefinition?format=TMSL"
    return complete(client, client.post(path))["definition"]


def model_part(definition):
    parts = [p for p in definition["parts"] if p["path"] == "model.bim"]
    if len(parts) != 1:
        raise ValueError("Expected exactly one TMSL model.bim. No creation attempted.")
    return json.loads(base64.b64decode(parts[0]["payload"]))


def ensure_absent(client):
    token = None
    for _ in range(100):
        path = f"/v1/workspaces/{WORKSPACE}/semanticModels"
        if token:
            path += "?continuationToken=" + quote(token, safe="")
        response = client.get(path)
        if response.status_code != 200:
            raise RuntimeError("Cannot check existing test models. No creation attempted.")
        page = response.json()
        if any(item.get("displayName", "").casefold() == TEST_NAME.casefold()
               for item in page.get("value", [])):
            raise ValueError("The TEST model already exists. Keep it and send its result; do not overwrite it.")
        token = page.get("continuationToken")
        if not token:
            return
    raise RuntimeError("Item listing did not complete. No creation attempted.")


def create_test_model(client):
    ensure_absent(client)
    before = read_definition(client, SOURCE_MODEL)
    source = model_part(before)
    candidate = extend_onelake(source)
    candidate["name"] = TEST_NAME
    candidate.pop("id", None)
    # Item identity and platform metadata belong to the original. Never clone them.
    parts = [copy.deepcopy(p) for p in before["parts"] if p["path"] != ".platform"]
    part = next(p for p in parts if p["path"] == "model.bim")
    part["payload"] = base64.b64encode(json.dumps(candidate, ensure_ascii=False).encode()).decode()
    part["payloadType"] = "InlineBase64"
    if not any(p["path"] == "definition.pbism" for p in parts):
        raise ValueError("Required definition.pbism was not returned. No creation attempted.")
    if digest(read_definition(client, SOURCE_MODEL)) != digest(before):
        raise RuntimeError("Original metadata changed concurrently. No creation attempted.")
    print("Creating one separate TEST model; the original model is not an update target.", flush=True)
    created = complete(client, client.post(f"/v1/workspaces/{WORKSPACE}/semanticModels", json={
        "displayName": TEST_NAME,
        "description": "OneLake native metadata compatibility TEST only. R16.6 production stays in place.",
        "definition": {"parts": parts}}))
    test_id = str(UUID(created["id"]))
    print("Created TEST model ID: " + test_id, flush=True)
    if test_id == SOURCE_MODEL:
        raise RuntimeError("Unexpected item identity. Stop and inspect Fabric.")
    received = model_part(read_definition(client, test_id))
    old = {t["name"]: t for t in source["model"]["tables"]}
    new = {t["name"]: t for t in received["model"]["tables"]}
    native = [t for name, t in new.items() if name.startswith("fm_native_")]
    preserved = all(new.get(name) == value for name, value in old.items())
    roles = received["model"].get("roles", []) == source["model"].get("roles", [])
    helpers = len(native) == 20 and all(
        len(t.get("partitions", [])) == 1
        and t["partitions"][0].get("source", {}).get("type") == "calculated" for t in native)
    production_unchanged = digest(read_definition(client, SOURCE_MODEL)) == digest(before)
    result = {"Stage": "ONELAKE_TEST_CREATED", "TestModelName": TEST_NAME, "TestModelID": test_id,
              "OriginalModelUnchanged": production_unchanged, "OriginalTablesCopiedExactly": preserved,
              "OriginalRolesCopiedExactly": roles, "NativeCalculatedHelpers": len(native),
              "HelperDefinitionsConfirmed": helpers, "SourceAmountsQueried": False,
              "OriginalModelUpdated": False, "RefreshRequested": False, "ReportPublished": False,
              "DirectLakeCalculatedTablePreview": "Company processing still unverified",
              "R166Parity": "NOT COMPLETE; qualification candidate only"}
    print(json.dumps(result, indent=2), flush=True)
    if not all((preserved, roles, helpers, production_unchanged)):
        raise RuntimeError("Readback needs inspection. Keep this TEST model; do not publish or recreate it.")
    print("NEXT: send this output. Do not change the published report or run the old SQL installer.")
    return result


if __name__ == "__main__":
    create_test_model(fabric.FabricRestClient())

