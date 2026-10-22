"""One NEW Fabric cell: upgrade ONLY the existing native TEST to R17.2.
Back up and verify the whole definition privately, preserve the cloud connection,
update native reporting measures/helpers. No company sales query, explicit refresh,
source change, production write, report publish or model recreation.
"""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote
from uuid import UUID, uuid4

WORKSPACE = 'f5cb5742-9a7c-4337-a4c0-952706dddf0b'
TEST_MODEL = '31d00232-ac03-48fe-af39-f2e4bae82443'
TEST_NAME = 'ForecastMaster Native OneLake R17.1 - TEST'
ORIGINAL_MODEL = 'e7af2967-7725-4108-a170-9e490d4e35bb'
LAKEHOUSE = 'd6e33ebd-67b1-420a-8d84-c3a0d04d8b21'
BASE = '/v1/workspaces/f5cb5742-9a7c-4337-a4c0-952706dddf0b/semanticModels/31d00232-ac03-48fe-af39-f2e4bae82443'
ITEM = '/v1/workspaces/f5cb5742-9a7c-4337-a4c0-952706dddf0b/items/31d00232-ac03-48fe-af39-f2e4bae82443'

BASELINE_HASHES = {'N Display': '83d093218662a8012c7d2c2c5c431506544c084e299eca356fc787c1fe262777',
 'N Catalog Visible': 'a1ed096682f12f94c65b23f7439585517369266b65c07ebe8118b02a6931be11',
 'N Catalog Available': '4b1adb265bb13a222276095e0871c938bc76657b7abd85719ced2332c23c6caa',
 'N Source Caption': 'a45fc9ada06582a0f1be59a66260c420c01cc9847be13ced786ae1d26c04cc96',
 'N Source OK': '91260c4f00240445f7cbf6d047a941dc63c4d8feea7256fe372f03d8e8c4b3aa',
 'N Scenario Visible': '224fb77731eacd9b6bf6eb53f8846dce25a4d3ae26952a9485a6d28073514a83',
 'N Scope Available': '2e65ea535c90f734ec0cf1890ae0bcc46b8f790b68501a53ebd9a35ab19eddba',
 'N Period Available': 'aeb693b79fd10b913e27617e8334d9ef7b06f492a9e81e9c272e7231765357f9',
 'N Cutoff': 'd3dd2b6875c0ef51b5c9c1a9db0a78637e7f6b975b5a59e5f7a3353fb96ce2ed',
 'N Monthly Numerator': '1efdc6836e4ee888d0a3c9e9fc20ee6864a345826c19a7b4b010528c48f65e8c',
 'N Monthly Denominator': '1ddf9d6f6d6c51f6bb8e8487ba3772424bdb0b2e3c9dd914a487cd069b9d898d',
 'N Monthly': '3274d7e88c1e1339794ede78bc182696d9fc833f3ae17a07a8edfc936713b656',
 'N Trend Monthly': 'a3dd82535e53f1dca0ae180157108d51e64450d961bc445d9c92a9cafc3d1591',
 'N Period Months': 'f69264dd7aff3034b87f341ab7bdc3e7c57d40a620a2eb67622ee239e7b32193',
 'N Plan': '0929908dabbf4139bdd9ea95f90fa84137e90c01af7060efabab1810025ce92d',
 'N Benchmark': '69154da8dbb16c2a76f0831eb93ccf3d9726c688f12ff3e3a5bf460e29a6c586',
 'N Variance': '64525ee09318aa2b386f7dc6c6bdb57d164d4f7ddef3b93415c7b7b23a7fbe74',
 'N Variance %': 'ff45f4339436d932955edef2e01eacbdd88d6c1f6236a5ac8bb07c461c5826af',
 'N Headline Variance': 'b80729a4d4db15fd721392ccffbc079356dfc5cb2f211321c9186ca0dc610228',
 'N Headline Variance %': '0fec548743ec12793c49f6ac867354edc7f40404fc5bdb465664dd46529c6110',
 'N Summary Cell': 'b5f87f81f6b98bcdf5b0f7e37a8ad743c8e07d9cbd766f28a7ef0b273972e6b3',
 'N Run Rate': '434e231e9f5e422a95019c31bbe897cdbb0259f6e12f7c5d30d00c65b519631c',
 'N Growth %': '530055c754ef14079d4ffa27784109ca04212d1f07c91358825e3c6b512f8793',
 'N SOP Row Selected': 'f90686cc5dbbd18e004cf469eeb4552fe40799f1f1915f3423fb5911e1f0fc52',
 'N SOP Plan': '56d1f4959a220d5c90740579f766b82f40fda518cb9642cf40e4282c6af1a077',
 'N SOP Run Rate': 'b5daef64e598b7c21141cf69b10dd1c18810b69acea3adaefb8c0cba807b73e3',
 'N SOP Growth %': 'e2f5581fec264566088e12d2c893558ffb686cc32704eb1b496d86a4e106dafb',
 'N SOP Monthly': '6c9de5289026a99311d8b191d895e97cd29ff886cb528bcc774935ee50cd45f3',
 'N SOP Monthly Growth %': 'b12f1ea184f793dfc37f8c931fdb7bdb2790d2606fbedcd40ff06db4d18a25e3',
 'N Export Selected': '488d7184e52844c19a0e3463dbcc165860f45b498cad362bb58ce01d344b5960',
 'N Export Plan': '04897f30186fcf00a11eb9fca8f92149ca07d3fa16a01e4f92ff6e25e5d1dd25',
 'N Export Run Rate': '772eec49fab63a3d29fe40aa7892da5745b3dbbb76805915162d71eebcc4b49f',
 'N Export Growth %': '2b04daf4beb36283edbebd50f2df3decc8a95924b704f889087edd410ae32584',
 'N Export Order': 'e730be8fa633332b34441ee8d65a764d2b26678ea7dc2af1199236d524929b66',
 'N Export Monthly': '4cf518b0e5d5cf5bfecee35e6f162c8759723d0433cc60b91321563231abaa4e',
 'N Export Month Stage': '98a443d675dbaac8ed174b7ff51b630063a4d1e54819f7b72efcb595ec67e697',
 'N Chart Monthly': 'ffccf80a170ec4ac92f29bacc763467878960f63d9ab1685587607a63f584903',
 'N Chart Amount': 'dec5ddc92c8c2fee36b340718e61be818a0f8ad33c5c985d651bdcfd85dbffa3',
 'N Chart Share': 'b59efc20e7accd4b466b347b5ce798fb3cad8c57993ade1ea3906d1682cf2da6',
 'N Status': '5c0bcca0d2c5f657c0be14a01bf7ea0cf9dcf7937270d66748ab4ebf7e3d3d0f',
 'N Variance Color': 'ab31ad7cee52b774325f64076c934bddb3ff6beb849c6e1095d712989787379c'}

REVISED = {'N Display': {'name': 'N Display',
               'expression': 'SELECTEDVALUE(\'fm_native_display\'[Display],"Units")',
               'formatString': '',
               'displayFolder': 'Native review',
               'description': 'R17 candidate; receiving DAX qualification required.',
               'isHidden': True},
 'N Catalog Visible': {'name': 'N Catalog Visible',
                       'expression': "IF(SELECTEDVALUE('fm_native_catalog'[Display])=[N "
                                     'Display],1)',
                       'formatString': '0',
                       'displayFolder': 'Native review',
                       'description': 'R17 candidate; receiving DAX qualification required.',
                       'isHidden': True},
 'N Catalog Available': {'name': 'N Catalog Available',
                         'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                       "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                       'VAR _selectedDrivers = '
                                       "VALUES('fm_native_scope'[GrowthDriver])\n"
                                       'VAR _custom = '
                                       'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                       'ADS") = "Selected files"\n'
                                       'VAR _scenario = '
                                       "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                       "VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])\n"
                                       "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                       "'fm_native_files'[Country] IN _country\n"
                                       " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                       " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                       "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                       'VAR _driver = '
                                       'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                       'VAR _pool = '
                                       "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                       '_driver)\n'
                                       'VAR _files = FILTER(_pool, IF(_custom, '
                                       "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                       "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                       " 'fm_native_files'[PreferenceRank]=1 && "
                                       "'fm_native_files'[PreferenceTies]=1))\n"
                                       'VAR _ids = '
                                       'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                       'VAR _scope = '
                                       "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                       'IN '
                                       "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                       'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                       'VAR _cohorts = '
                                       "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                       'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                       'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                       ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                       ' && (NOT _custom || '
                                       "ISFILTERED('fm_review_files'[FileLabel]))\n"
                                       'VAR '
                                       "_admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)\n"
                                       'VAR '
                                       '_candidateIds=SELECTCOLUMNS(_admitted,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                       'VAR '
                                       "_component=SELECTEDVALUE('fm_native_catalog'[Component])\n"
                                       "VAR _channel=SELECTEDVALUE('fm_native_catalog'[Channel])\n"
                                       "VAR _sub=SELECTEDVALUE('fm_native_catalog'[SubChannel])\n"
                                       'RETURN '
                                       "IF(CALCULATE(COUNTROWS('fm_review_facts'),REMOVEFILTERS('fm_review_facts'),\n"
                                       ' '
                                       "TREATAS(_candidateIds,'fm_review_facts'[SourceRevisionID]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                       " TREATAS({_channel},'fm_review_facts'[Channel]),\n"
                                       ' '
                                       'FILTER(ALL(\'fm_review_facts\'[SubChannel]),COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub))>0,1)',
                         'formatString': '0',
                         'displayFolder': 'Native review',
                         'description': 'R17 candidate; receiving DAX qualification required.',
                         'isHidden': True},
 'N Source Caption': {'name': 'N Source Caption',
                      'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                    "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                    'VAR _selectedDrivers = '
                                    "VALUES('fm_native_scope'[GrowthDriver])\n"
                                    'VAR _custom = '
                                    'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic ADS") '
                                    '= "Selected files"\n'
                                    'VAR _scenario = '
                                    "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                    "VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])\n"
                                    "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                    "'fm_native_files'[Country] IN _country\n"
                                    " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                    " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                    "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                    'VAR _driver = '
                                    'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                    'VAR _pool = '
                                    "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                    '_driver)\n'
                                    'VAR _files = FILTER(_pool, IF(_custom, '
                                    "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                    "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                    " 'fm_native_files'[PreferenceRank]=1 && "
                                    "'fm_native_files'[PreferenceTies]=1))\n"
                                    'VAR _ids = '
                                    'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                    'VAR _scope = '
                                    "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                    'IN '
                                    "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                    'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                    'VAR _cohorts = '
                                    "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                    'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                    'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                    ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                    ' && (NOT _custom || '
                                    "ISFILTERED('fm_review_files'[FileLabel]))\n"
                                    'VAR '
                                    "_ims=SUMMARIZE(_files,'fm_native_files'[IMSActualsThrough])\n"
                                    'VAR '
                                    "_ef=SUMMARIZE(_files,'fm_native_files'[ExFactoryActualsThrough])\n"
                                    'RETURN IF(NOT _sourceOK,"Choose an available source for every '
                                    'selected driver.",\n'
                                    ' IF(_custom,"Selected versions","ADS automatic")&" · '
                                    '"&FORMAT(COUNTROWS(_files),"0")&" source(s) · IMS through "&\n'
                                    ' '
                                    'IF(COUNTROWS(_ims)=1,FORMAT(MAXX(_ims,\'fm_native_files\'[IMSActualsThrough]),"mmm '
                                    'yy"),"mixed cutoffs")&\n'
                                    ' " · Ex-factory through '
                                    '"&IF(COUNTROWS(_ef)=1,FORMAT(MAXX(_ef,\'fm_native_files\'[ExFactoryActualsThrough]),"mmm '
                                    'yy"),"mixed cutoffs"))',
                      'formatString': '',
                      'displayFolder': 'Native review',
                      'description': 'R17 candidate; receiving DAX qualification required.',
                      'isHidden': True},
 'N Source OK': {'name': 'N Source OK',
                 'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                               "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                               "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                               'VAR _custom = '
                               'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic ADS") = '
                               '"Selected files"\n'
                               'VAR _scenario = '
                               "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                               "VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])\n"
                               "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                               "'fm_native_files'[Country] IN _country\n"
                               " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                               " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                               "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                               'VAR _driver = '
                               'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                               "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] "
                               'IN _driver)\n'
                               'VAR _files = FILTER(_pool, IF(_custom, '
                               "'fm_native_files'[SourceRevisionID] IN _chosen && "
                               "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                               " 'fm_native_files'[PreferenceRank]=1 && "
                               "'fm_native_files'[PreferenceTies]=1))\n"
                               'VAR _ids = '
                               'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                               'VAR _scope = '
                               "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                               'IN '
                               "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                               'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                               'VAR _cohorts = '
                               "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                               'VAR _sourceOK = COUNTROWS(_files)>0 && '
                               'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                               ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                               " && (NOT _custom || ISFILTERED('fm_review_files'[FileLabel]))\n"
                               'RETURN INT(_sourceOK)',
                 'formatString': '0',
                 'displayFolder': 'Native review',
                 'description': 'R17 candidate; receiving DAX qualification required.',
                 'isHidden': True},
 'N Scenario Visible': {'name': 'N Scenario Visible',
                        'expression': 'IF(SELECTEDVALUE(\'fm_native_scenario\'[Mode])=SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                      'ADS")&&[N Source OK]=1,1)',
                        'formatString': '0',
                        'displayFolder': 'Native review',
                        'description': 'R17 candidate; receiving DAX qualification required.',
                        'isHidden': True},
 'N Scope Available': {'name': 'N Scope Available',
                       'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                     "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                     'VAR _selectedDrivers = '
                                     "VALUES('fm_native_scope'[GrowthDriver])\n"
                                     'VAR _custom = '
                                     'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic ADS") '
                                     '= "Selected files"\n'
                                     'VAR _scenario = '
                                     "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                     "VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])\n"
                                     "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                     "'fm_native_files'[Country] IN _country\n"
                                     " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                     " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                     "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                     'VAR _driver = '
                                     'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                     'VAR _pool = '
                                     "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                     '_driver)\n'
                                     'VAR _files = FILTER(_pool, IF(_custom, '
                                     "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                     "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                     " 'fm_native_files'[PreferenceRank]=1 && "
                                     "'fm_native_files'[PreferenceTies]=1))\n"
                                     'VAR _ids = '
                                     'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                     'VAR _scope = '
                                     "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                     'IN '
                                     "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                     'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                     'VAR _cohorts = '
                                     "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                     'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                     'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                     ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                     ' && (NOT _custom || '
                                     "ISFILTERED('fm_review_files'[FileLabel]))\n"
                                     'VAR '
                                     "_admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)\n"
                                     'VAR '
                                     '_candidateIds=SELECTCOLUMNS(_admitted,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                     'RETURN '
                                     "IF(COUNTROWS(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                     'IN _candidateIds))>0,1)',
                       'formatString': '0',
                       'displayFolder': 'Native review',
                       'description': 'R17 candidate; receiving DAX qualification required.',
                       'isHidden': True},
 'N Period Available': {'name': 'N Period Available',
                        'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                      "RETURN IF(_y>=YEAR(MIN('fm_review_months'[Month])) && "
                                      "_y<=YEAR(MAX('fm_review_months'[Month])),1)",
                        'formatString': '0',
                        'displayFolder': 'Native review',
                        'description': 'R17 candidate; receiving DAX qualification required.',
                        'isHidden': True},
 'N Cutoff': {'name': 'N Cutoff',
              'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                            "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                            "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                            'VAR _custom = SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                            'ADS") = "Selected files"\n'
                            'VAR _scenario = '
                            "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                            "VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])\n"
                            "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                            "'fm_native_files'[Country] IN _country\n"
                            " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                            " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                            "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                            'VAR _driver = '
                            'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                            "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                            '_driver)\n'
                            'VAR _files = FILTER(_pool, IF(_custom, '
                            "'fm_native_files'[SourceRevisionID] IN _chosen && "
                            "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                            " 'fm_native_files'[PreferenceRank]=1 && "
                            "'fm_native_files'[PreferenceTies]=1))\n"
                            'VAR _ids = '
                            'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                            'VAR _scope = '
                            "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                            "IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                            'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                            'VAR _cohorts = '
                            "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                            'VAR _sourceOK = COUNTROWS(_files)>0 && '
                            'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                            ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                            " && (NOT _custom || ISFILTERED('fm_review_files'[FileLabel]))\n"
                            'VAR '
                            '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                            'VAR _ef=IF(_row IN '
                            '{"share","abbott","market","pi","net"},FALSE(),TRUE())\n'
                            'VAR '
                            '_dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,\'fm_native_files\'[ExFactoryActualsThrough],\'fm_native_files\'[IMSActualsThrough]))\n'
                            'RETURN IF(_sourceOK && '
                            'COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])))=0,MINX(_dates,[Cutoff]))',
              'formatString': 'mmm yyyy',
              'displayFolder': 'Native review',
              'description': 'R17 candidate; receiving DAX qualification required.',
              'isHidden': True},
 'N Monthly Numerator': {'name': 'N Monthly Numerator',
                         'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                       "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                       'VAR _selectedDrivers = '
                                       "VALUES('fm_native_scope'[GrowthDriver])\n"
                                       'VAR _custom = '
                                       'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                       'ADS") = "Selected files"\n'
                                       'VAR _scenario = '
                                       "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                       "VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])\n"
                                       "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                       "'fm_native_files'[Country] IN _country\n"
                                       " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                       " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                       "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                       'VAR _driver = '
                                       'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                       'VAR _pool = '
                                       "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                       '_driver)\n'
                                       'VAR _files = FILTER(_pool, IF(_custom, '
                                       "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                       "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                       " 'fm_native_files'[PreferenceRank]=1 && "
                                       "'fm_native_files'[PreferenceTies]=1))\n"
                                       'VAR _ids = '
                                       'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                       'VAR _scope = '
                                       "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                       'IN '
                                       "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                       'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                       'VAR _cohorts = '
                                       "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                       'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                       'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                       ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                       ' && (NOT _custom || '
                                       "ISFILTERED('fm_review_files'[FileLabel]))\n"
                                       "VAR _date=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                       'VAR '
                                       '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                       'VAR _display=[N Display]\n'
                                       'VAR '
                                       "_definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row "
                                       "&& 'fm_native_catalog'[Display]=_display)\n"
                                       'VAR _component=IF(_row="ef","ef-ads-" & '
                                       "LOWER(_display),MAXX(_definition,'fm_native_catalog'[Component]))\n"
                                       'VAR '
                                       '_channel=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[Channel]))\n'
                                       'VAR '
                                       '_sub=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[SubChannel]))\n'
                                       'VAR _value=_display="Value"\n'
                                       'VAR '
                                       '_usd=SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD"\n'
                                       'VAR '
                                       '_currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE(\'fm_native_currency_map\'[Currency],\'fm_native_currency_map\'[Country],\'fm_native_files\'[Country]))\n'
                                       'VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 && '
                                       'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0\n'
                                       'VAR _convert=_value && _usd && (_row<>"share" || NOT '
                                       '_singleCurrency)\n'
                                       "VAR _selectedChannels=VALUES('fm_review_facts'[Channel])\n"
                                       "VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])\n"
                                       'VAR '
                                       '_fx=FILTER(CALCULATETABLE(\'fm_native_state\',ALLEXCEPT(\'fm_native_state\',\'fm_native_state\'[Token])),\'fm_native_state\'[Kind]="fx")\n'
                                       'VAR _members=GENERATE(_files,\n'
                                       " VAR _id='fm_native_files'[SourceRevisionID]\n"
                                       " VAR _gd='fm_native_files'[GrowthDriver]\n"
                                       " VAR _cc='fm_native_files'[Country]\n"
                                       ' VAR '
                                       "_currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)\n"
                                       ' VAR '
                                       "_digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)\n"
                                       ' VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 && '
                                       "COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,\n"
                                       '  VAR '
                                       "_exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])\n"
                                       '  VAR _half=INT(_exponent/2)\n'
                                       '  RETURN '
                                       "SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*\n"
                                       '  POWER(10,_half)*POWER(10,_exponent-_half)))\n'
                                       ' VAR '
                                       '_sectors=SELECTCOLUMNS(FILTER(_scope,\'fm_native_scope\'[GrowthDriver]=_gd),"Sector",\'fm_native_scope\'[Sector])\n'
                                       ' VAR '
                                       "_memberFacts=CALCULATETABLE('fm_review_facts',REMOVEFILTERS('fm_review_facts'),\n"
                                       '  '
                                       "TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),\n"
                                       '  '
                                       "TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                       '  '
                                       'FILTER(ALL(\'fm_review_facts\'[Channel]),IF(_channel="*",\'fm_review_facts\'[Channel] '
                                       'IN '
                                       "_selectedChannels,'fm_review_facts'[Channel]=_channel)),\n"
                                       '  '
                                       'FILTER(ALL(\'fm_review_facts\'[SubChannel]),IF(_sub="*",\'fm_review_facts\'[SubChannel] '
                                       'IN '
                                       '_selectedSubs,COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub)))\n'
                                       ' VAR '
                                       "_bySector=GROUPBY(_memberFacts,'fm_review_facts'[Sector],\n"
                                       '  '
                                       '"RawAmount",SUMX(CURRENTGROUP(),\'fm_review_facts\'[Amount]),\n'
                                       '  '
                                       '"BadCells",SUMX(CURRENTGROUP(),INT(\'fm_review_facts\'[MissingCells]<>0||ISBLANK(\'fm_review_facts\'[Amount]))))\n'
                                       ' RETURN ADDCOLUMNS(FILTER(_bySector,[BadCells]=0),\n'
                                       '  "Amount",IF(_convert,IF(NOT ISBLANK([RawAmount])&&NOT '
                                       'ISBLANK(_rate),IFERROR([RawAmount]*_rate,BLANK())),[RawAmount]),\n'
                                       '  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) && '
                                       '(ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))\n'
                                       'VAR _available=FILTER(_members,NOT ISBLANK([Amount]))\n'
                                       'VAR '
                                       '_localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))\n'
                                       'RETURN IF(_sourceOK && NOT ISBLANK(_date) && '
                                       'LEN(_component)>0 && COUNTROWS(_available)>0\n'
                                       ' && SUMX(_members,[FXMissing])=0 && (NOT _value || '
                                       'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)\n'
                                       ' && (NOT _value || _usd || '
                                       'COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))',
                         'displayFolder': 'Native review',
                         'description': 'R17 candidate; receiving DAX qualification required.',
                         'formatStringDefinition': {'expression': 'VAR '
                                                                  '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                  'VAR '
                                                                  '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                  ' || '
                                                                  'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                  'VAR '
                                                                  "_countries=VALUES('fm_review_files'[Country])\n"
                                                                  'VAR '
                                                                  "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                  'IN '
                                                                  "_countries),'fm_native_currency_map'[Currency])\n"
                                                                  'VAR _symbol=IF([N '
                                                                  'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                  ' '
                                                                  'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                  'VAR '
                                                                  '_value=ABS(SELECTEDMEASURE())\n'
                                                                  'VAR '
                                                                  '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                                  '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                  ' _value>=1000,"#,0.0," & '
                                                                  'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                  'RETURN '
                                                                  'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                         'isHidden': True},
 'N Monthly Denominator': {'name': 'N Monthly Denominator',
                           'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                         "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                         'VAR _selectedDrivers = '
                                         "VALUES('fm_native_scope'[GrowthDriver])\n"
                                         'VAR _custom = '
                                         'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                         'ADS") = "Selected files"\n'
                                         'VAR _scenario = '
                                         "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                         'VAR _chosen = '
                                         "VALUES('fm_review_files'[SourceRevisionID])\n"
                                         "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                         "'fm_native_files'[Country] IN _country\n"
                                         " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                         " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                         "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                         'VAR _driver = '
                                         'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                         'VAR _pool = '
                                         "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                         '_driver)\n'
                                         'VAR _files = FILTER(_pool, IF(_custom, '
                                         "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                         "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                         " 'fm_native_files'[PreferenceRank]=1 && "
                                         "'fm_native_files'[PreferenceTies]=1))\n"
                                         'VAR _ids = '
                                         'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                         'VAR _scope = '
                                         "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                         'IN '
                                         "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                         'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                         'VAR _cohorts = '
                                         "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                         'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                         'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                         ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                         ' && (NOT _custom || '
                                         "ISFILTERED('fm_review_files'[FileLabel]))\n"
                                         "VAR _date=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                         'VAR '
                                         '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                         'VAR _display=[N Display]\n'
                                         'VAR '
                                         "_definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row "
                                         "&& 'fm_native_catalog'[Display]=_display)\n"
                                         'VAR '
                                         '_component=IF(_row="ef","",MAXX(_definition,\'fm_native_catalog\'[Denominator]))\n'
                                         'VAR '
                                         '_channel=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[Channel]))\n'
                                         'VAR '
                                         '_sub=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[SubChannel]))\n'
                                         'VAR _value=_display="Value"\n'
                                         'VAR '
                                         '_usd=SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD"\n'
                                         'VAR '
                                         '_currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE(\'fm_native_currency_map\'[Currency],\'fm_native_currency_map\'[Country],\'fm_native_files\'[Country]))\n'
                                         'VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 '
                                         '&& COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0\n'
                                         'VAR _convert=_value && _usd && (_row<>"share" || NOT '
                                         '_singleCurrency)\n'
                                         'VAR '
                                         "_selectedChannels=VALUES('fm_review_facts'[Channel])\n"
                                         "VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])\n"
                                         'VAR '
                                         '_fx=FILTER(CALCULATETABLE(\'fm_native_state\',ALLEXCEPT(\'fm_native_state\',\'fm_native_state\'[Token])),\'fm_native_state\'[Kind]="fx")\n'
                                         'VAR _members=GENERATE(_files,\n'
                                         " VAR _id='fm_native_files'[SourceRevisionID]\n"
                                         " VAR _gd='fm_native_files'[GrowthDriver]\n"
                                         " VAR _cc='fm_native_files'[Country]\n"
                                         ' VAR '
                                         "_currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)\n"
                                         ' VAR '
                                         "_digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)\n"
                                         ' VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 '
                                         '&& '
                                         "COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,\n"
                                         '  VAR '
                                         "_exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])\n"
                                         '  VAR _half=INT(_exponent/2)\n'
                                         '  RETURN '
                                         "SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*\n"
                                         '  POWER(10,_half)*POWER(10,_exponent-_half)))\n'
                                         ' VAR '
                                         '_sectors=SELECTCOLUMNS(FILTER(_scope,\'fm_native_scope\'[GrowthDriver]=_gd),"Sector",\'fm_native_scope\'[Sector])\n'
                                         ' VAR '
                                         "_memberFacts=CALCULATETABLE('fm_review_facts',REMOVEFILTERS('fm_review_facts'),\n"
                                         '  '
                                         "TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),\n"
                                         '  '
                                         "TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                         '  '
                                         'FILTER(ALL(\'fm_review_facts\'[Channel]),IF(_channel="*",\'fm_review_facts\'[Channel] '
                                         'IN '
                                         "_selectedChannels,'fm_review_facts'[Channel]=_channel)),\n"
                                         '  '
                                         'FILTER(ALL(\'fm_review_facts\'[SubChannel]),IF(_sub="*",\'fm_review_facts\'[SubChannel] '
                                         'IN '
                                         '_selectedSubs,COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub)))\n'
                                         ' VAR '
                                         "_bySector=GROUPBY(_memberFacts,'fm_review_facts'[Sector],\n"
                                         '  '
                                         '"RawAmount",SUMX(CURRENTGROUP(),\'fm_review_facts\'[Amount]),\n'
                                         '  '
                                         '"BadCells",SUMX(CURRENTGROUP(),INT(\'fm_review_facts\'[MissingCells]<>0||ISBLANK(\'fm_review_facts\'[Amount]))))\n'
                                         ' RETURN ADDCOLUMNS(FILTER(_bySector,[BadCells]=0),\n'
                                         '  "Amount",IF(_convert,IF(NOT ISBLANK([RawAmount])&&NOT '
                                         'ISBLANK(_rate),IFERROR([RawAmount]*_rate,BLANK())),[RawAmount]),\n'
                                         '  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) '
                                         '&& '
                                         '(ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))\n'
                                         'VAR _available=FILTER(_members,NOT ISBLANK([Amount]))\n'
                                         'VAR '
                                         '_localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))\n'
                                         'RETURN IF(_sourceOK && NOT ISBLANK(_date) && '
                                         'LEN(_component)>0 && COUNTROWS(_available)>0\n'
                                         ' && SUMX(_members,[FXMissing])=0 && (NOT _value || '
                                         'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)\n'
                                         ' && (NOT _value || _usd || '
                                         'COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))',
                           'displayFolder': 'Native review',
                           'description': 'R17 candidate; receiving DAX qualification required.',
                           'formatStringDefinition': {'expression': 'VAR '
                                                                    '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                    'VAR '
                                                                    '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                    ' || '
                                                                    'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                    'VAR '
                                                                    "_countries=VALUES('fm_review_files'[Country])\n"
                                                                    'VAR '
                                                                    "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                    'IN '
                                                                    "_countries),'fm_native_currency_map'[Currency])\n"
                                                                    'VAR _symbol=IF([N '
                                                                    'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                    ' '
                                                                    'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                    'VAR '
                                                                    '_value=ABS(SELECTEDMEASURE())\n'
                                                                    'VAR '
                                                                    '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                                    '& '
                                                                    'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                    ' _value>=1000,"#,0.0," & '
                                                                    'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                    'RETURN '
                                                                    'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                           'isHidden': True},
 'N Monthly': {'name': 'N Monthly',
               'expression': 'VAR _n=[N Monthly Numerator] VAR _d=[N Monthly Denominator]\n'
                             'RETURN '
                             'IF(COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share",DIVIDE(_n,_d),_n)',
               'displayFolder': 'Native review',
               'description': 'R17 candidate; receiving DAX qualification required.',
               'formatStringDefinition': {'expression': 'VAR '
                                                        '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                        'VAR '
                                                        '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                        ' || '
                                                        'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                        'VAR '
                                                        "_countries=VALUES('fm_review_files'[Country])\n"
                                                        'VAR '
                                                        "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                        'IN '
                                                        "_countries),'fm_native_currency_map'[Currency])\n"
                                                        'VAR _symbol=IF([N '
                                                        'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                        ' '
                                                        'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                        'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                        'VAR '
                                                        '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                        '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                        ' _value>=1000,"#,0.0," & '
                                                        'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                        'RETURN '
                                                        'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
               'isHidden': True},
 'N Trend Monthly': {'name': 'N Trend Monthly',
                     'expression': 'VAR _cut=[N Fit Cutoff] VAR '
                                   "_w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                                   "VAR _m=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                   'VAR '
                                   '_dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Date",EDATE(_cut,[Value]-_w),"X",[Value])\n'
                                   'VAR _train=ADDCOLUMNS(_dates,"Y",VAR _d=[Date] RETURN '
                                   'CALCULATE([N '
                                   "Monthly],REMOVEFILTERS('fm_review_axis'),TREATAS({_d},'fm_review_axis'[Month])))\n"
                                   'VAR _valid=FILTER(_train,NOT ISBLANK([Y]))\n'
                                   'VAR _mx=AVERAGEX(_train,[X]) VAR _my=AVERAGEX(_train,[Y])\n'
                                   'VAR '
                                   '_slope=DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_my)),SUMX(_train,POWER([X]-_mx,2)))\n'
                                   'RETURN IF(NOT ISBLANK(_m)&&NOT ISBLANK(_cut),IF(_m<=_cut,[N '
                                   'Monthly],\n'
                                   ' '
                                   'IF(COUNTROWS(_valid)=_w,_my+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-_mx))))',
                     'displayFolder': 'Native review',
                     'description': 'R17 candidate; receiving DAX qualification required.',
                     'formatStringDefinition': {'expression': 'VAR '
                                                              '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                              'VAR '
                                                              '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                              ' || '
                                                              'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                              'VAR '
                                                              "_countries=VALUES('fm_review_files'[Country])\n"
                                                              'VAR '
                                                              "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                              'IN '
                                                              "_countries),'fm_native_currency_map'[Currency])\n"
                                                              'VAR _symbol=IF([N '
                                                              'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                              ' '
                                                              'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                              'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                              'VAR '
                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                              '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                              ' _value>=1000,"#,0.0," & '
                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                              'RETURN '
                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                     'isHidden': True},
 'N Period Months': {'name': 'N Period Months',
                     'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                   "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR "
                                   '_cut=[N Cutoff]\n'
                                   'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                                   'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                                   'VAR '
                                   '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                                   'VAR '
                                   '_end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                                   'RETURN IF(NOT ISBLANK(_y)&&NOT '
                                   'ISBLANK(_cut)&&_end>=_start,DATEDIFF(_start,_end,MONTH)+1)',
                     'formatString': '0',
                     'displayFolder': 'Native review',
                     'description': 'R17 candidate; receiving DAX qualification required.',
                     'isHidden': True},
 'N Plan': {'name': 'N Plan',
            'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                          "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR _cut=[N "
                          'Cutoff]\n'
                          'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                          'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                          'VAR '
                          '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                          'VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                          'VAR _count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                          'VAR '
                          '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]))\n'
                          'VAR _values=ADDCOLUMNS(_months,"N",VAR _m=[Date] RETURN\n'
                          ' CALCULATE([N Monthly '
                          "Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])),\n"
                          ' "D",VAR _m=[Date] RETURN CALCULATE([N Monthly '
                          "Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])))\n"
                          'VAR _valid=COUNTROWS(FILTER(_values,NOT ISBLANK([N])))=_count\n'
                          'VAR '
                          '_ratio=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share"\n'
                          'RETURN IF(NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_valid,\n'
                          ' IF(_ratio,IF(COUNTROWS(FILTER(_values,NOT '
                          'ISBLANK([D])))=_count,DIVIDE(SUMX(_values,[N]),SUMX(_values,[D]))),SUMX(_values,[N])))',
            'displayFolder': 'Native review',
            'description': 'R17 candidate; receiving DAX qualification required.',
            'formatStringDefinition': {'expression': 'VAR '
                                                     '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                     'VAR '
                                                     '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                     ' || '
                                                     'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                     'VAR '
                                                     "_countries=VALUES('fm_review_files'[Country])\n"
                                                     'VAR '
                                                     "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                     'IN '
                                                     "_countries),'fm_native_currency_map'[Currency])\n"
                                                     'VAR _symbol=IF([N '
                                                     'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                     ' '
                                                     'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                     'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                     'VAR '
                                                     '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                     '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                     ' _value>=1000,"#,0.0," & '
                                                     'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                     'RETURN '
                                                     'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
            'isHidden': False},
 'N Benchmark': {'name': 'N Benchmark',
                 'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                               "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR "
                               '_cut=[N Cutoff]\n'
                               'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                               'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                               'VAR '
                               '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                               'VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                               'VAR _count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                               'VAR '
                               '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]))\n'
                               'VAR _values=ADDCOLUMNS(_months,"N",VAR _m=[Date] RETURN\n'
                               ' '
                               'CALCULATE(IF(_m>_cut,IF(COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share",[N '
                               'Trend Monthly]*[N Monthly Denominator],[N Trend Monthly]),[N '
                               'Monthly '
                               "Numerator]),REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])),\n"
                               ' "D",VAR _m=[Date] RETURN CALCULATE([N Monthly '
                               "Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])))\n"
                               'VAR _valid=COUNTROWS(FILTER(_values,NOT ISBLANK([N])))=_count\n'
                               'VAR '
                               '_ratio=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share"\n'
                               'RETURN IF(NOT ISBLANK([N Fit Cutoff])&&NOT ISBLANK(_y)&&NOT '
                               'ISBLANK(_cut)&&_count>0&&_valid,\n'
                               ' IF(_ratio,IF(COUNTROWS(FILTER(_values,NOT '
                               'ISBLANK([D])))=_count,DIVIDE(SUMX(_values,[N]),SUMX(_values,[D]))),SUMX(_values,[N])))',
                 'displayFolder': 'Native review',
                 'description': 'R17 candidate; receiving DAX qualification required.',
                 'formatStringDefinition': {'expression': 'VAR '
                                                          '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                          'VAR '
                                                          '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                          ' || '
                                                          'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                          'VAR '
                                                          "_countries=VALUES('fm_review_files'[Country])\n"
                                                          'VAR '
                                                          "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                          'IN '
                                                          "_countries),'fm_native_currency_map'[Currency])\n"
                                                          'VAR _symbol=IF([N '
                                                          'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                          ' '
                                                          'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                          'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                          'VAR '
                                                          '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                          '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                          ' _value>=1000,"#,0.0," & '
                                                          'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                          'RETURN '
                                                          'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                 'isHidden': True},
 'N Variance': {'name': 'N Variance',
                'expression': 'VAR _p=[N Plan] VAR _t=[N Benchmark] RETURN IF(NOT ISBLANK(_p)&&NOT '
                              'ISBLANK(_t),_p-_t)',
                'displayFolder': 'Native review',
                'description': 'R17 candidate; receiving DAX qualification required.',
                'formatStringDefinition': {'expression': 'VAR '
                                                         '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                         'VAR '
                                                         '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                         ' || '
                                                         'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                         'VAR '
                                                         "_countries=VALUES('fm_review_files'[Country])\n"
                                                         'VAR '
                                                         "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                         'IN '
                                                         "_countries),'fm_native_currency_map'[Currency])\n"
                                                         'VAR _symbol=IF([N '
                                                         'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                         ' '
                                                         'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                         'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                         'VAR '
                                                         '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                         '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                         ' _value>=1000,"#,0.0," & '
                                                         'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                         'RETURN '
                                                         'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                'isHidden': False},
 'N Variance %': {'name': 'N Variance %',
                  'expression': 'DIVIDE([N Variance],ABS([N Benchmark]))',
                  'formatString': '+0.0%;−0.0%;0.0%',
                  'displayFolder': 'Native review',
                  'description': 'R17 candidate; receiving DAX qualification required.',
                  'isHidden': False},
 'N Headline Variance': {'name': 'N Headline Variance',
                         'expression': "VAR _w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                                       'VAR _actual=[N Actual Only]=1\n'
                                       'RETURN IF(NOT _actual,CALCULATE([N '
                                       "Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))",
                         'displayFolder': 'Native review',
                         'description': 'R17 candidate; receiving DAX qualification required.',
                         'formatStringDefinition': {'expression': 'VAR '
                                                                  '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                  'VAR '
                                                                  '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                  ' || '
                                                                  'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                  'VAR '
                                                                  "_countries=VALUES('fm_review_files'[Country])\n"
                                                                  'VAR '
                                                                  "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                  'IN '
                                                                  "_countries),'fm_native_currency_map'[Currency])\n"
                                                                  'VAR _symbol=IF([N '
                                                                  'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                  ' '
                                                                  'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                  'VAR '
                                                                  '_value=ABS(SELECTEDMEASURE())\n'
                                                                  'VAR '
                                                                  '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                                  '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                  ' _value>=1000,"#,0.0," & '
                                                                  'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                  'RETURN '
                                                                  'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                         'isHidden': True},
 'N Headline Variance %': {'name': 'N Headline Variance %',
                           'expression': 'VAR '
                                         "_w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                                         'VAR _actual=[N Actual Only]=1\n'
                                         'RETURN IF(NOT _actual,CALCULATE([N Variance '
                                         "%],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))",
                           'formatString': '+0.0%;−0.0%;0.0%',
                           'displayFolder': 'Native review',
                           'description': 'R17 candidate; receiving DAX qualification required.',
                           'isHidden': True},
 'N Summary Cell': {'name': 'N Summary Cell',
                    'expression': "VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])\n"
                                  "VAR _w=SELECTEDVALUE('fm_native_columns'[Window])\n"
                                  "VAR _allowed=_w=0 || _w IN VALUES('fm_native_trend'[Window])\n"
                                  'VAR _actualOnly=[N Actual Only]=1\n'
                                  'RETURN IF([N Period '
                                  'Available]=1&&_allowed,SWITCH(TRUE(),_key="plan",[N '
                                  'Plan],_actualOnly,BLANK(),\n'
                                  ' RIGHT(_key,3)="abs",CALCULATE([N '
                                  "Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])),\n"
                                  ' CALCULATE([N Variance '
                                  "%],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window]))))",
                    'displayFolder': 'Native review',
                    'description': 'R17 candidate; receiving DAX qualification required.',
                    'formatStringDefinition': {'expression': 'VAR '
                                                             '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                             'VAR '
                                                             '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                             ' || '
                                                             'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                             'VAR '
                                                             "_countries=VALUES('fm_review_files'[Country])\n"
                                                             'VAR '
                                                             "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                             'IN '
                                                             "_countries),'fm_native_currency_map'[Currency])\n"
                                                             'VAR _symbol=IF([N '
                                                             'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                             ' '
                                                             'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                             'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                             'VAR '
                                                             '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                             '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                             ' _value>=1000,"#,0.0," & '
                                                             'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                             'RETURN '
                                                             'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                    'isHidden': True},
 'N Run Rate': {'name': 'N Run Rate',
                'expression': 'IF(SELECTEDVALUE(\'fm_native_run_rate\'[Show],"Off")="On" && '
                              "SELECTEDVALUE('fm_native_catalog'[RunRate],0)=1,\n"
                              ' DIVIDE([N Plan],[N Period Months]))',
                'displayFolder': 'Native review',
                'description': 'R17 candidate; receiving DAX qualification required.',
                'formatStringDefinition': {'expression': 'VAR '
                                                         '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                         'VAR '
                                                         '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                         ' || '
                                                         'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                         'VAR '
                                                         "_countries=VALUES('fm_review_files'[Country])\n"
                                                         'VAR '
                                                         "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                         'IN '
                                                         "_countries),'fm_native_currency_map'[Currency])\n"
                                                         'VAR _symbol=IF([N '
                                                         'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                         ' '
                                                         'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                         'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                         'VAR '
                                                         '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                         '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                         ' _value>=1000,"#,0.0," & '
                                                         'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                         'RETURN '
                                                         'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                'isHidden': True},
 'N Growth %': {'name': 'N Growth %',
                'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                              "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR "
                              '_cut=[N Cutoff]\n'
                              'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                              'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                              'VAR '
                              '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                              'VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                              'VAR _count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                              'VAR '
                              '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]-12))\n'
                              'VAR _values=ADDCOLUMNS(_months,"PY",VAR _m=[Date] RETURN '
                              'CALCULATE([N Monthly '
                              "Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])))\n"
                              'VAR _py=IF(_count>0 && COUNTROWS(FILTER(_values,NOT '
                              'ISBLANK([PY])))=_count,SUMX(_values,[PY]))\n'
                              'RETURN '
                              'IF(SELECTEDVALUE(\'fm_native_growth\'[Show],"Off")="On"&&SELECTEDVALUE(\'fm_native_catalog\'[Growth],0)=1,\n'
                              ' IF(NOT ISBLANK([N Plan])&&NOT ISBLANK(_py),DIVIDE([N '
                              'Plan]-_py,_py)))',
                'formatString': '+0.0%;−0.0%;0.0%',
                'displayFolder': 'Native review',
                'description': 'R17 candidate; receiving DAX qualification required.',
                'isHidden': True},
 'N SOP Row Selected': {'name': 'N SOP Row Selected',
                        'expression': "VAR _token=SELECTEDVALUE('fm_native_rows'[Token])\n"
                                      "RETURN IF(ISFILTERED('fm_native_state'[Token]) && "
                                      'SELECTEDVALUE(\'fm_native_rows\'[Kind])="row"\n'
                                      " && SELECTEDVALUE('fm_native_rows'[Display])=[N Display],1)",
                        'formatString': '0',
                        'displayFolder': 'Native review',
                        'description': 'R17 candidate; receiving DAX qualification required.',
                        'isHidden': True},
 'N SOP Plan': {'name': 'N SOP Plan',
                'expression': "VAR _groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                              "VAR _groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                              "VAR _groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                              "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                              "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                              ' '
                              "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                              " &&(NOT _groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                              "VAR _groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                              ' NOT '
                              "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                              "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                              'Visible]<>1,BLANK(),CALCULATE(\n'
                              "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                              'RETURN IF([N SOP Row Selected]=1,CALCULATE([N '
                              "Plan],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                              "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                'displayFolder': 'Native review',
                'description': 'R17 candidate; receiving DAX qualification required.',
                'formatStringDefinition': {'expression': 'VAR '
                                                         '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                         'VAR '
                                                         '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                         ' || '
                                                         'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                         'VAR '
                                                         "_countries=VALUES('fm_review_files'[Country])\n"
                                                         'VAR '
                                                         "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                         'IN '
                                                         "_countries),'fm_native_currency_map'[Currency])\n"
                                                         'VAR _symbol=IF([N '
                                                         'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                         ' '
                                                         'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                         'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                         'VAR '
                                                         '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                         '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                         ' _value>=1000,"#,0.0," & '
                                                         'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                         'RETURN '
                                                         'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                'isHidden': False},
 'N SOP Run Rate': {'name': 'N SOP Run Rate',
                    'expression': 'VAR '
                                  "_groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                  'VAR '
                                  "_groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                  'VAR '
                                  "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                  "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                  "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                  ' '
                                  "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                  ' &&(NOT '
                                  "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                  'VAR '
                                  "_groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                  ' NOT '
                                  "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                  "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                                  'Visible]<>1,BLANK(),CALCULATE(\n'
                                  "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                  'RETURN IF([N SOP Row Selected]=1,CALCULATE([N Run '
                                  "Rate],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                  "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                    'displayFolder': 'Native review',
                    'description': 'R17 candidate; receiving DAX qualification required.',
                    'formatStringDefinition': {'expression': 'VAR '
                                                             '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                             'VAR '
                                                             '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                             ' || '
                                                             'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                             'VAR '
                                                             "_countries=VALUES('fm_review_files'[Country])\n"
                                                             'VAR '
                                                             "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                             'IN '
                                                             "_countries),'fm_native_currency_map'[Currency])\n"
                                                             'VAR _symbol=IF([N '
                                                             'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                             ' '
                                                             'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                             'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                             'VAR '
                                                             '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                             '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                             ' _value>=1000,"#,0.0," & '
                                                             'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                             'RETURN '
                                                             'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                    'isHidden': False},
 'N SOP Growth %': {'name': 'N SOP Growth %',
                    'expression': 'VAR '
                                  "_groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                  'VAR '
                                  "_groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                  'VAR '
                                  "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                  "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                  "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                  ' '
                                  "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                  ' &&(NOT '
                                  "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                  'VAR '
                                  "_groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                  ' NOT '
                                  "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                  "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                                  'Visible]<>1,BLANK(),CALCULATE(\n'
                                  "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                  'RETURN IF([N SOP Row Selected]=1,CALCULATE([N Growth '
                                  "%],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                  "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                    'formatString': '+0.0%;−0.0%;0.0%',
                    'displayFolder': 'Native review',
                    'description': 'R17 candidate; receiving DAX qualification required.',
                    'isHidden': False},
 'N SOP Monthly': {'name': 'N SOP Monthly',
                   'expression': "VAR _groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                 "VAR _groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                 'VAR '
                                 "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                 "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                 "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                 ' '
                                 "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                 ' &&(NOT '
                                 "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                 "VAR _groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                 ' NOT '
                                 "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                 "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                                 'Visible]<>1,BLANK(),CALCULATE(\n'
                                 "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                 'RETURN IF([N SOP Row Selected]=1 && '
                                 "SELECTEDVALUE('fm_review_axis'[Month])>=MIN('fm_review_months'[Month]) "
                                 '&& '
                                 "SELECTEDVALUE('fm_review_axis'[Month])<=MAX('fm_review_months'[Month]),CALCULATE([N "
                                 "Monthly],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                 "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                   'displayFolder': 'Native review',
                   'description': 'R17 candidate; receiving DAX qualification required.',
                   'formatStringDefinition': {'expression': 'VAR '
                                                            '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                            'VAR '
                                                            '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                            ' || '
                                                            'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                            'VAR '
                                                            "_countries=VALUES('fm_review_files'[Country])\n"
                                                            'VAR '
                                                            "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                            'IN '
                                                            "_countries),'fm_native_currency_map'[Currency])\n"
                                                            'VAR _symbol=IF([N '
                                                            'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                            ' '
                                                            'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                            'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                            'VAR '
                                                            '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                            '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                            ' _value>=1000,"#,0.0," & '
                                                            'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                            'RETURN '
                                                            'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                   'isHidden': False},
 'N SOP Monthly Growth %': {'name': 'N SOP Monthly Growth %',
                            'expression': 'VAR '
                                          "_groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                          'VAR '
                                          "_groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                          'VAR '
                                          "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                          'VAR '
                                          "_groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                          "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                          ' '
                                          "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                          ' &&(NOT '
                                          "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                          'VAR '
                                          "_groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                          ' NOT '
                                          "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                          "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N "
                                          'Group Visible]<>1,BLANK(),CALCULATE(\n'
                                          "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                          "VAR _month=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                          'VAR '
                                          "_allowed=MAXX(FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row),'fm_native_catalog'[Growth])=1\n"
                                          'VAR _current=CALCULATE([N Monthly '
                                          "Numerator],TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                                          'VAR _prior=CALCULATE([N Monthly '
                                          "Numerator],TREATAS({_row},'fm_native_catalog'[RowID]),REMOVEFILTERS('fm_review_axis'),TREATAS({EDATE(_month,-12)},'fm_review_axis'[Month]))\n"
                                          'RETURN IF([N SOP Row '
                                          'Selected]=1&&_allowed&&SELECTEDVALUE(\'fm_native_growth\'[Show],"Off")="On"\n'
                                          ' '
                                          "&&_month>=MIN('fm_review_months'[Month])&&_month<=MAX('fm_review_months'[Month])\n"
                                          ' &&NOT ISBLANK(_current)&&NOT '
                                          'ISBLANK(_prior),DIVIDE(_current-_prior,_prior)),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))',
                            'formatString': '+0.0%;−0.0%;0.0%',
                            'displayFolder': 'Native review',
                            'description': 'R17 candidate; receiving DAX qualification required.',
                            'isHidden': False},
 'N Export Selected': {'name': 'N Export Selected',
                       'expression': "VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])\n"
                                     'VAR _display=[N Display]\n'
                                     'VAR '
                                     "_chosen=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),\n"
                                     ' '
                                     '\'fm_native_state\'[Kind]="row"&&\'fm_native_state\'[RowID]=_row&&\'fm_native_state\'[Display]=_display)\n'
                                     'RETURN '
                                     "IF(ISFILTERED('fm_native_state'[Token])&&COUNTROWS(_chosen)=1,1)",
                       'formatString': '0',
                       'displayFolder': 'Native review',
                       'description': 'R17 candidate; receiving DAX qualification required.',
                       'isHidden': True},
 'N Export Plan': {'name': 'N Export Plan',
                   'expression': 'IF([N Export Selected]=1,[N Plan])',
                   'displayFolder': 'Native review',
                   'description': 'R17 candidate; receiving DAX qualification required.',
                   'formatStringDefinition': {'expression': 'VAR '
                                                            '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                            'VAR '
                                                            '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                            ' || '
                                                            'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                            'VAR '
                                                            "_countries=VALUES('fm_review_files'[Country])\n"
                                                            'VAR '
                                                            "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                            'IN '
                                                            "_countries),'fm_native_currency_map'[Currency])\n"
                                                            'VAR _symbol=IF([N '
                                                            'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                            ' '
                                                            'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                            'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                            'VAR '
                                                            '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                            '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                            ' _value>=1000,"#,0.0," & '
                                                            'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                            'RETURN '
                                                            'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                   'isHidden': True},
 'N Export Run Rate': {'name': 'N Export Run Rate',
                       'expression': 'IF([N Export Selected]=1,[N Run Rate])',
                       'displayFolder': 'Native review',
                       'description': 'R17 candidate; receiving DAX qualification required.',
                       'formatStringDefinition': {'expression': 'VAR '
                                                                '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                'VAR '
                                                                '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                ' || '
                                                                'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                'VAR '
                                                                "_countries=VALUES('fm_review_files'[Country])\n"
                                                                'VAR '
                                                                "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                'IN '
                                                                "_countries),'fm_native_currency_map'[Currency])\n"
                                                                'VAR _symbol=IF([N '
                                                                'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                ' '
                                                                'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                'VAR '
                                                                '_value=ABS(SELECTEDMEASURE())\n'
                                                                'VAR '
                                                                '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                                '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                ' _value>=1000,"#,0.0," & '
                                                                'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                'RETURN '
                                                                'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                       'isHidden': True},
 'N Export Growth %': {'name': 'N Export Growth %',
                       'expression': 'IF([N Export Selected]=1,[N Growth %])',
                       'formatString': '+0.0%;−0.0%;0.0%',
                       'displayFolder': 'Native review',
                       'description': 'R17 candidate; receiving DAX qualification required.',
                       'isHidden': True},
 'N Export Order': {'name': 'N Export Order',
                    'expression': "VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])\n"
                                  'VAR _display=[N Display]\n'
                                  'VAR '
                                  "_chosen=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),\n"
                                  ' '
                                  '\'fm_native_state\'[Kind]="row"&&\'fm_native_state\'[RowID]=_row&&\'fm_native_state\'[Display]=_display)\n'
                                  'RETURN IF([N Export '
                                  "Selected]=1,MINX(_chosen,'fm_native_state'[RowRank]))",
                    'formatString': '0',
                    'displayFolder': 'Native review',
                    'description': 'R17 candidate; receiving DAX qualification required.',
                    'isHidden': True},
 'N Export Monthly': {'name': 'N Export Monthly',
                      'expression': "VAR _m=SELECTEDVALUE('fm_review_axis'[Month]) RETURN IF([N "
                                    'Export Selected]=1\n'
                                    ' '
                                    "&&_m>=MIN('fm_review_months'[Month])&&_m<=MAX('fm_review_months'[Month]),[N "
                                    'Monthly])',
                      'displayFolder': 'Native review',
                      'description': 'R17 candidate; receiving DAX qualification required.',
                      'formatStringDefinition': {'expression': 'VAR '
                                                               '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                               'VAR '
                                                               '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                               ' || '
                                                               'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                               'VAR '
                                                               "_countries=VALUES('fm_review_files'[Country])\n"
                                                               'VAR '
                                                               "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                               'IN '
                                                               "_countries),'fm_native_currency_map'[Currency])\n"
                                                               'VAR _symbol=IF([N '
                                                               'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                               ' '
                                                               'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                               'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                               'VAR '
                                                               '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                               '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                               ' _value>=1000,"#,0.0," & '
                                                               'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                               'RETURN '
                                                               'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                      'isHidden': True},
 'N Export Month Stage': {'name': 'N Export Month Stage',
                          'expression': "VAR _m=SELECTEDVALUE('fm_review_axis'[Month]) VAR _cut=[N "
                                        'Cutoff]\n'
                                        'RETURN IF([N Export Selected]=1&&NOT ISBLANK(_m)&&NOT '
                                        'ISBLANK(_cut),IF(_m<=_cut,"Actual","Forecast"))',
                          'formatString': '',
                          'displayFolder': 'Native review',
                          'description': 'R17 candidate; receiving DAX qualification required.',
                          'isHidden': True},
 'N Chart Monthly': {'name': 'N Chart Monthly',
                     'expression': "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                                   "VAR _gd=SELECTEDVALUE('fm_native_lines'[ScopeDriver]) VAR "
                                   "_sec=SELECTEDVALUE('fm_native_lines'[ScopeSector])\n"
                                   'VAR '
                                   "_sectorLevel=SELECTEDVALUE('fm_native_lines'[IsSector],0)=1\n"
                                   "VAR _cyc=SELECTEDVALUE('fm_native_lines'[DemandCycle]) VAR "
                                   "_type=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                                   'VAR '
                                   '_row=IF(_type="sop",SELECTEDVALUE(\'fm_native_lines\'[RowID]),COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market"))\n'
                                   "VAR _display=SELECTEDVALUE('fm_native_lines'[Display])\n"
                                   'VAR _selected=_type="demand" || '
                                   "ISFILTERED('fm_native_state'[Token]) && COUNTROWS(\n"
                                   ' '
                                   'FILTER(ALLSELECTED(\'fm_native_state\'),\'fm_native_state\'[Kind]="row"\n'
                                   ' '
                                   "&&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display))>0\n"
                                   'VAR '
                                   "_scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)&&(NOT "
                                   "_sectorLevel||'fm_native_scope'[Sector]=_sec))\n"
                                   "VAR _month=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                   'VAR '
                                   "_within=_month>=MIN('fm_review_months'[Month])&&_month<=MAX('fm_review_months'[Month])\n"
                                   'VAR '
                                   '_mode=SELECTEDVALUE(\'fm_native_lines\'[Mode])=SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                   'ADS")\n'
                                   'VAR _base=CALCULATE([N '
                                   "Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                                   'VAR _cut=CALCULATE([N '
                                   "Cutoff],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                                   'RETURN '
                                   "IF(_mode&&_within&&_selected&&COUNTROWS(_scope)>0&&SELECTEDVALUE('fm_native_lines'[ViewType]) "
                                   "IN VALUES('fm_native_view'[View]),\n"
                                   ' '
                                   'SWITCH(TRUE(),_kind=0&&_month<=_cut,_base,_kind=1&&_month>_cut,_base,\n'
                                   ' _kind IN {6,12,24}&&_month>=_cut&&_kind IN '
                                   "VALUES('fm_native_trend'[Window]),\n"
                                   ' CALCULATE([N Trend '
                                   "Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]),REMOVEFILTERS('fm_native_trend'),TREATAS({_kind},'fm_native_trend'[Window]))))",
                     'displayFolder': 'Native review',
                     'description': 'R17 candidate; receiving DAX qualification required.',
                     'formatStringDefinition': {'expression': 'VAR '
                                                              '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                              'VAR '
                                                              '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                              ' || '
                                                              'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                              'VAR '
                                                              "_countries=VALUES('fm_review_files'[Country])\n"
                                                              'VAR '
                                                              "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                              'IN '
                                                              "_countries),'fm_native_currency_map'[Currency])\n"
                                                              'VAR _symbol=IF([N '
                                                              'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                              ' '
                                                              'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                              'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                              'VAR '
                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                              '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                              ' _value>=1000,"#,0.0," & '
                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                              'RETURN '
                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                     'isHidden': True},
 'N Chart Amount': {'name': 'N Chart Amount',
                    'expression': 'IF(SELECTEDVALUE(\'fm_native_lines\'[RowID])<>"share",[N Chart '
                                  'Monthly])',
                    'displayFolder': 'Native review',
                    'description': 'R17 candidate; receiving DAX qualification required.',
                    'formatStringDefinition': {'expression': 'VAR '
                                                             '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                             'VAR '
                                                             '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                             ' || '
                                                             'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                             'VAR '
                                                             "_countries=VALUES('fm_review_files'[Country])\n"
                                                             'VAR '
                                                             "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                             'IN '
                                                             "_countries),'fm_native_currency_map'[Currency])\n"
                                                             'VAR _symbol=IF([N '
                                                             'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                             ' '
                                                             'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                             'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                             'VAR '
                                                             '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                             '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                             ' _value>=1000,"#,0.0," & '
                                                             'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                             'RETURN '
                                                             'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                    'isHidden': True},
 'N Chart Share': {'name': 'N Chart Share',
                   'expression': 'IF(SELECTEDVALUE(\'fm_native_lines\'[RowID])="share",[N Chart '
                                 'Monthly])',
                   'formatString': '0.0%',
                   'displayFolder': 'Native review',
                   'description': 'R17 candidate; receiving DAX qualification required.',
                   'isHidden': True},
 'N Status': {'name': 'N Status',
              'expression': 'SWITCH(TRUE(),[N Source OK]<>1,"Select a valid ADS source for each '
                            'selected cohort. Check Matching files.",\n'
                            ' ISBLANK([N Cutoff]),"Selected sources have different cutoffs; '
                            'compare them separately.",\n'
                            ' "Saved ADS · IMS / EF calendars retained · Native R17 candidate")',
              'formatString': '',
              'displayFolder': 'Native review',
              'description': 'R17 candidate; receiving DAX qualification required.',
              'isHidden': True},
 'N Variance Color': {'name': 'N Variance Color',
                      'expression': 'VAR _value=[N Summary Cell] RETURN '
                                    'IF(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey])="plan"||ISBLANK(_value)||_value=0,"#17384D",IF(_value>0,"#087D88","#AC640C"))',
                      'formatString': '',
                      'displayFolder': 'Native review',
                      'description': 'R17 candidate; receiving DAX qualification required.',
                      'isHidden': True},
 'N Fit Cutoff': {'name': 'N Fit Cutoff',
                  'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                                'VAR _custom = '
                                'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic ADS") = '
                                '"Selected files"\n'
                                'VAR _scenario = '
                                "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                "VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])\n"
                                "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                "'fm_native_files'[Country] IN _country\n"
                                " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                'VAR _driver = '
                                'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] "
                                'IN _driver)\n'
                                'VAR _files = FILTER(_pool, IF(_custom, '
                                "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                " 'fm_native_files'[PreferenceRank]=1 && "
                                "'fm_native_files'[PreferenceTies]=1))\n"
                                'VAR _ids = '
                                'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                'VAR _scope = '
                                "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                'IN '
                                "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                'VAR _cohorts = '
                                "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                " && (NOT _custom || ISFILTERED('fm_review_files'[FileLabel]))\n"
                                'VAR '
                                '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                'VAR _ef=IF(_row IN '
                                '{"share","abbott","market","pi","net"},FALSE(),TRUE())\n'
                                'VAR '
                                '_dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,\'fm_native_files\'[ExFactoryActualsThrough],\'fm_native_files\'[IMSActualsThrough]))\n'
                                'RETURN IF(_sourceOK && '
                                'COUNTROWS(DISTINCT(_dates))=1,MAXX(_dates,[Cutoff]))',
                  'formatString': 'mmm yyyy',
                  'displayFolder': 'Native review',
                  'description': 'R17 candidate; receiving DAX qualification required.',
                  'isHidden': True},
 'N Actual Only': {'name': 'N Actual Only',
                   'expression': "VAR _year=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                 "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR "
                                 '_cut=[N Cutoff]\n'
                                 'VAR '
                                 '_end=SWITCH(_kind,"YTD",DATE(_year,MONTH(_cut),1),"H1",DATE(_year,6,1),DATE(_year,12,1))\n'
                                 'VAR _actualOnly=NOT ISBLANK(_cut)&&NOT '
                                 'ISBLANK(_year)&&_end<=_cut\n'
                                 'RETURN INT(_actualOnly)',
                   'formatString': '0',
                   'displayFolder': 'Native review',
                   'isHidden': True},
 'N Line Visible': {'name': 'N Line Visible',
                    'expression': "VAR _view=SELECTEDVALUE('fm_native_lines'[ViewType])\n"
                                  "VAR _mode=SELECTEDVALUE('fm_native_lines'[Mode])\n"
                                  "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                                  "VAR _cycle=SELECTEDVALUE('fm_native_lines'[DemandCycle])\n"
                                  "VAR _chart=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                                  "RETURN IF(_view IN VALUES('fm_native_view'[View])\n"
                                  ' && '
                                  '_mode=SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                  'ADS")\n'
                                  " && _cycle IN VALUES('fm_review_files'[DemandCycle])\n"
                                  ' && (_chart="sop" || _kind IN {0,1} || _kind IN '
                                  "VALUES('fm_native_trend'[Window])),1)",
                    'formatString': '0',
                    'displayFolder': 'Native review',
                    'isHidden': True},
 'N Selected Month': {'name': 'N Selected Month',
                      'expression': "IF(HASONEVALUE('fm_review_axis'[Month]),\n"
                                    ' FORMAT(SELECTEDVALUE(\'fm_review_axis\'[Month]),"mmm yyyy"))',
                      'displayFolder': 'Native review',
                      'isHidden': True},
 'N Selected Monthly': {'name': 'N Selected Monthly',
                        'expression': "IF(HASONEVALUE('fm_review_axis'[Month]),[N Monthly])",
                        'displayFolder': 'Native review',
                        'description': 'R17 candidate; receiving DAX qualification required.',
                        'formatStringDefinition': {'expression': 'VAR '
                                                                 '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                 'VAR '
                                                                 '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                 ' || '
                                                                 'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                 'VAR '
                                                                 "_countries=VALUES('fm_review_files'[Country])\n"
                                                                 'VAR '
                                                                 "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                 'IN '
                                                                 "_countries),'fm_native_currency_map'[Currency])\n"
                                                                 'VAR _symbol=IF([N '
                                                                 'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                 ' '
                                                                 'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                 'VAR '
                                                                 '_value=ABS(SELECTEDMEASURE())\n'
                                                                 'VAR '
                                                                 '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                                 '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                 ' _value>=1000,"#,0.0," & '
                                                                 'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                 'RETURN '
                                                                 'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                        'isHidden': True},
 'N Headline Cell': {'name': 'N Headline Cell',
                     'expression': "SWITCH(SELECTEDVALUE('fm_native_headline'[Key]),\n"
                                   ' "plan",[N Plan],"variance",[N Headline Variance],"pct",[N '
                                   'Headline Variance %])',
                     'displayFolder': 'Native review',
                     'description': 'R17 candidate; receiving DAX qualification required.',
                     'formatStringDefinition': {'expression': 'VAR '
                                                              '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                              'VAR '
                                                              '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                              ' || '
                                                              'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                              'VAR '
                                                              "_countries=VALUES('fm_review_files'[Country])\n"
                                                              'VAR '
                                                              "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                              'IN '
                                                              "_countries),'fm_native_currency_map'[Currency])\n"
                                                              'VAR _symbol=IF([N '
                                                              'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                              ' '
                                                              'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                              'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                              'VAR '
                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," '
                                                              '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                              ' _value>=1000,"#,0.0," & '
                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                              'RETURN '
                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                     'isHidden': False},
 'N Measure Caption': {'name': 'N Measure Caption',
                       'expression': 'VAR '
                                     '_name=SELECTEDVALUE(\'fm_native_metric\'[MetricLabel],"Selected '
                                     'measures")\n'
                                     'RETURN IF(CONTAINSSTRING(_name,"%"),_name,_name & IF([N '
                                     'Display]="Value"," value"," units"))',
                       'displayFolder': 'Native review',
                       'isHidden': True},
 'N Group Visible': {'name': 'N Group Visible',
                     'expression': "VAR _cycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                   "VAR _gd=SELECTEDVALUE('fm_native_groups'[ScopeDriver]) VAR "
                                   "_sec=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                   "VAR _sector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                   'VAR '
                                   "_scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)\n"
                                   " &&(NOT _sector||'fm_native_scope'[Sector]=_sec))\n"
                                   'RETURN IF(_cycle IN '
                                   "VALUES('fm_review_files'[DemandCycle])&&COUNTROWS(_scope)>0,1)",
                     'displayFolder': 'Native review',
                     'formatString': '0',
                     'isHidden': True}}

HELPERS = [{'name': 'fm_native_periods',
  'description': 'R17.2 native FY/YTD/YTG/H1/H2 metadata; amounts remain in original facts.',
  'columns': [{'name': 'Y',
               'dataType': 'int64',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[Y]',
               'summarizeBy': 'none'},
              {'name': 'Year',
               'dataType': 'int64',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[Year]',
               'summarizeBy': 'none'},
              {'name': 'PeriodType',
               'dataType': 'string',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[PeriodType]',
               'summarizeBy': 'none'},
              {'name': 'PeriodKey',
               'dataType': 'string',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[PeriodKey]',
               'summarizeBy': 'none'},
              {'name': 'Label',
               'dataType': 'string',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[Label]',
               'summarizeBy': 'none',
               'sortByColumn': 'SortIndex'},
              {'name': 'SortIndex',
               'dataType': 'int64',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[SortIndex]',
               'summarizeBy': 'none'}],
  'partitions': [{'name': 'fm_native_periods',
                  'mode': 'import',
                  'source': {'type': 'calculated',
                             'expression': '\n'
                                           "VAR _years = DISTINCT(SELECTCOLUMNS('fm_review_axis', "
                                           '"Y", YEAR([Month])))\n'
                                           'RETURN GENERATE(_years, VAR _year = [Y]\n'
                                           ' RETURN SELECTCOLUMNS(DATATABLE("K", STRING, "S", '
                                           'INTEGER,\n'
                                           ' {{"FY",0},{"YTD",1},{"YTG",2},{"H1",3},{"H2",4}}),\n'
                                           ' "Year", _year, "PeriodType", [K], "PeriodKey", '
                                           'FORMAT(_year,"0") & ":" & [K],\n'
                                           ' "Label", FORMAT(_year,"0") & " " & [K], "SortIndex", '
                                           '_year * 10 + [S]))\n'}}]},
 {'name': 'fm_native_headline',
  'columns': [{'name': 'Key',
               'dataType': 'string',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[Key]',
               'summarizeBy': 'none'},
              {'name': 'Label',
               'dataType': 'string',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[Label]',
               'summarizeBy': 'none',
               'sortByColumn': 'Sort'},
              {'name': 'Sort',
               'dataType': 'int64',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[Sort]',
               'summarizeBy': 'none'}],
  'partitions': [{'name': 'fm_native_headline',
                  'mode': 'import',
                  'source': {'type': 'calculated',
                             'expression': 'DATATABLE("Key",STRING,"Label",STRING,"Sort",INTEGER,{{"plan","Plan",0},{"variance","Overcall '
                                           '/ Undercall",1},{"pct","Variance %",2}})'}}]}]
def expression_hash(expression):
    text = "\n".join(expression) if isinstance(expression, list) else expression
    return hashlib.sha256(text.strip().replace("\r\n","\n").encode()).hexdigest()


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def complete(client, response, result=False):
    if response.status_code not in {200, 202}:
        raise RuntimeError("Fabric HTTP " + str(response.status_code)
                           + "; inspect Fabric. No automatic retry.")
    if response.status_code == 200:
        if not result:
            return {}
        return response.json()
    operation_id = str(UUID(response.headers["x-ms-operation-id"]))
    print("Operation: " + operation_id, flush=True)
    operation = "/v1/operations/" + operation_id
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        time.sleep(min(30, max(1, int(response.headers.get("Retry-After", "5")))))
        response = client.get(operation)
        if response.status_code != 200:
            raise RuntimeError("Operation status unavailable; inspect it before any retry.")
        state = response.json().get("status")
        if state == "Succeeded":
            if not result:
                return {}
            received = client.get(operation + "/result")
            if received.status_code != 200:
                raise RuntimeError("Operation result unavailable; inspect Fabric before retrying.")
            return received.json()
        if state in {"Failed", "Cancelled", "Canceled"}:
            raise RuntimeError("Operation " + state + "; inspect the private backup. No retry.")
    raise TimeoutError("Outcome unconfirmed; inspect this operation before any retry.")


def read_definition(client):
    return complete(client, client.post(BASE + "/getDefinition?format=TMSL"), True)["definition"]


def database_part(definition):
    parts = [p for p in definition["parts"] if p["path"] == "model.bim"]
    if len(parts) != 1:
        raise ValueError("Expected one TMSL model.bim; no write.")
    return json.loads(base64.b64decode(parts[0]["payload"], validate=True))


def connection_state(client):
    values, token = [], None
    for _ in range(100):
        path = ITEM + "/connections"
        if token:
            path += "?continuationToken=" + quote(token, safe="")
        response = client.get(path)
        if response.status_code != 200:
            raise RuntimeError("Cannot verify TEST cloud mapping; no further write attempted.")
        page = response.json()
        values.extend(page.get("value", []))
        token = page.get("continuationToken")
        if not token:
            return sorted(values, key=lambda value: json.dumps(value, sort_keys=True))
    raise RuntimeError("Connection inventory incomplete; no further write attempted.")


def verified_backup(fs, path, value):
    """Full UTF-8 byte verification; never use a preview read as backup evidence."""
    raw = json.dumps(value, ensure_ascii=False)
    expected = raw.encode("utf-8")
    expected_hash = hashlib.sha256(expected).digest()
    if not fs.put(path, raw, False):
        raise RuntimeError("Private backup write failed; no model write. Retained path: " + path)
    observed_size, reason = None, "copy not completed"
    with TemporaryDirectory(prefix="forecastmaster-test-backup-") as directory:
        for attempt in range(3):
            if attempt:
                time.sleep(0.5)
            local = Path(directory) / (str(attempt) + ".json")
            try:
                if not fs.cp(path, local.as_uri(), False):
                    reason = "copy returned false"
                    continue
                observed_hash, observed_size = hashlib.sha256(), 0
                with local.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(65536), b""):
                        observed_size += len(chunk)
                        observed_hash.update(chunk)
                if observed_size == len(expected) and observed_hash.digest() == expected_hash:
                    return
                reason = "full-file hash/length mismatch"
            except Exception as error:
                reason = type(error).__name__
    raise RuntimeError(
        "Private backup verification failed: " + reason
        + "; expected bytes=" + str(len(expected)) + ", observed bytes=" + str(observed_size)
        + ". No model write. Retained backup: " + path)


def patch_database(database):
    after = deepcopy(database)
    tables = {t["name"]:t for t in after["model"]["tables"]}
    if "fm_native_measures" not in tables or "fm_native_lines" not in tables:
        raise ValueError("Expected the installed R17.1 TEST; no update.")
    old = BASELINE_HASHES
    revised = REVISED
    current = {m["name"]:m for m in tables["fm_native_measures"]["measures"]}
    changes = []
    for name, replacement in revised.items():
        if name in current:
            value = current[name]
            new = deepcopy(value)
            new["expression"] = replacement["expression"]
            if "formatStringDefinition" in replacement:
                new["formatStringDefinition"] = deepcopy(replacement["formatStringDefinition"])
            if value == new:
                continue
            if name not in old or expression_hash(value["expression"]) != old[name]:
                raise ValueError("Unknown native measure expression; inspect before applying: " + name)
            value.update(new)
        else:
            tables["fm_native_measures"]["measures"].append(deepcopy(replacement))
        changes.append(name)
    for expected in HELPERS:
        if expected["name"] in tables:
            existing = tables[expected["name"]]
            if expression_hash(existing["partitions"][0]["source"]["expression"]) != expression_hash(expected["partitions"][0]["source"]["expression"]):
                raise ValueError("Unexpected existing native helper; no update.")
        else:
            after["model"]["tables"].append(expected)
            changes.append(expected["name"])
    relationship = {"name":"NativeR172-Groups-View","fromTable":"fm_native_groups","fromColumn":"ViewType",
                    "toTable":"fm_native_view","toColumn":"View"}
    matches = [r for r in after["model"].get("relationships",[]) if r["name"]==relationship["name"]]
    if matches and any(matches[0].get(k)!=v for k,v in relationship.items()):
        raise ValueError("Unexpected native grouping relationship; no update.")
    if not matches:
        after["model"].setdefault("relationships",[]).append(relationship)
        changes.append(relationship["name"])
    # Restrict changes to this measure table and the single new native helper.
    restored = deepcopy(after)
    original = {t["name"]:t for t in database["model"]["tables"]}
    restored["model"]["tables"] = [deepcopy(original[t["name"]]) if t["name"]=="fm_native_measures" else t
        for t in restored["model"]["tables"] if t["name"] not in {"fm_native_periods","fm_native_headline"} or t["name"] in original]
    if not any(r["name"]==relationship["name"] for r in database["model"].get("relationships",[])):
        restored["model"]["relationships"] = [r for r in restored["model"].get("relationships",[]) if r["name"]!=relationship["name"]]
        if "relationships" not in database["model"]:
            restored["model"].pop("relationships",None)
    if restored != database:
        raise AssertionError("Unrelated model change; no update.")
    return after, changes


def run(client, fs):
    if TEST_MODEL == ORIGINAL_MODEL or not BASE.endswith("/" + TEST_MODEL):
        raise ValueError("Invalid TEST target; no write.")
    item = client.get(ITEM)
    if item.status_code != 200:
        raise RuntimeError("Cannot verify existing TEST item; no write.")
    identity = item.json()
    if (identity.get("id") != TEST_MODEL or identity.get("displayName") != TEST_NAME
            or identity.get("type") != "SemanticModel"):
        raise ValueError("TEST item identity does not match; no write.")
    before = read_definition(client)
    database = database_part(before)
    tables = database["model"]["tables"]
    if sum(t["name"].startswith("fm_native_") for t in tables) not in {20,22}:
        raise ValueError("Expected existing R17.1 TEST helper tables; no write.")
    fixed, changed = patch_database(database)
    if not changed:
        result = {"Stage": "TEST_R172_ALREADY_INSTALLED", "MeasuresChanged": 0,
                  "TestModelID": TEST_MODEL, "ModelWriteRequested": False,
                  "SourceAmountsQueried": False, "RefreshRequested": False}
        print(json.dumps(result, indent=2), flush=True)
        return result
    connections = connection_state(client)
    if not any(c.get("connectivityType") == "ShareableCloud" for c in connections):
        raise ValueError("Explicit shareable TEST cloud mapping not confirmed; no write.")
    after = deepcopy(before)
    part = next(p for p in after["parts"] if p["path"] == "model.bim")
    part["payload"] = base64.b64encode(json.dumps(fixed, ensure_ascii=False).encode()).decode()
    part["payloadType"] = "InlineBase64"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + str(uuid4())
    root = f"abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}"
    backup = root + "/Files/ForecastMasterRefreshState/report-upgrades/Native-R172/" + stamp
    fs.mkdirs(backup)
    for name, value in (("definition-before.json", before),
                        ("definition-candidate.json", after), ("connections-before.json", connections)):
        verified_backup(fs, backup + "/" + name, value)
    print("Verified private TEST backup: " + backup, flush=True)
    if digest(read_definition(client)) != digest(before):
        raise RuntimeError("TEST metadata changed concurrently; no overwrite.")
    if connection_state(client) != connections:
        raise RuntimeError("TEST connection changed concurrently; no overwrite.")
    complete(client, client.post(BASE + "/updateDefinition", json={
        "definition": after, "options": {"allowPurgeData": False}}))
    received = database_part(read_definition(client))
    if received != fixed:
        raise RuntimeError("TEST definition readback differs; keep backup and send the result.")
    if connection_state(client) != connections:
        raise RuntimeError("TEST cloud mapping differs; inspect Maps to before refreshing.")
    result = {"Stage": "TEST_R172_UPDATED", "TestModelID": TEST_MODEL,
              "Revision": "R17.2", "BackupVerification": "FULL_FILE_UTF8_SHA256_AND_LENGTH",
              "NativeObjectsChanged": len(changed), "OtherModelDefinitionPreserved": True,
              "CloudConnectionPreserved": True, "OriginalModelWriteRequested": False,
              "SourceAmountsQueried": False, "RefreshRequested": False,
              "ReportPublished": False, "Backup": backup}
    fs.put(backup + "/receipt.json", json.dumps(result, indent=2), False)
    print(json.dumps(result, indent=2), flush=True)
    print("NEXT: Refresh this TEST semantic model ONCE. If Completed without warnings, open the NEW R17.2 TEST report. Keep production R16.6 unchanged.")
    return result


if __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(), notebookutils.fs)
