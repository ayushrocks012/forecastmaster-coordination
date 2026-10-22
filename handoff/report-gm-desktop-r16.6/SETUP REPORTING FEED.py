# Run in a separate, unscheduled Fabric Python notebook attached to ForecastMaster.
# This updates only reporting definitions. It does not start a worker or publish a report.
import csv, io, json, hashlib, requests, re
from typing import Any, Callable
from datetime import datetime, UTC
from email.utils import format_datetime
from urllib.parse import quote
from uuid import UUID, uuid4
WORKSPACE = "__WORKSPACE__"
LAKEHOUSE = "__LAKEHOUSE__"
class OneLakeQueueStore:
    def __init__(
        self,
        workspace: str,
        lakehouse: str,
        get_token: Callable[[str], str],
        *,
        http: Any = requests,
    ):
        workspace, lakehouse = str(UUID(workspace)), str(UUID(lakehouse))
        self.base = f"https://onelake.blob.fabric.microsoft.com/{workspace}/{lakehouse}/Files/ForecastMasterRefreshState/"
        self.get_token, self.http = get_token, http
        self.lease_id = ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + self.get_token("storage"),
            "x-ms-version": "2021-06-08",
            "x-ms-date": format_datetime(datetime.now(UTC), usegmt=True),
        }

    def _url(self, name: str) -> str:
        if (
            not re.fullmatch(r"[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*", name)
            or ".." in name
        ):
            raise ValueError("Invalid worker-state filename")
        return self.base + quote(name, safe="/")

    def read(self, name: str) -> dict[str, Any] | None:
        result = self.http.get(
            self._url(name), headers=self._headers(), timeout=45, allow_redirects=False
        )
        if result.status_code == 404:
            return None
        if result.status_code != 200:
            raise RuntimeError(
                f"Cannot read worker state {name} (HTTP {result.status_code})."
            )
        content = result.json()
        if not isinstance(content, dict):
            raise TypeError("Invalid worker state " + name)
        return content

    def write(self, name: str, content: dict[str, Any]) -> None:
        result = self.http.put(
            self._url(name),
            headers={
                **self._headers(),
                "x-ms-blob-type": "BlockBlob",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                content, ensure_ascii=False, allow_nan=False, indent=2
            ).encode("utf-8"),
            timeout=45,
            allow_redirects=False,
        )
        if result.status_code != 201:
            raise RuntimeError(
                f"Cannot retain worker receipt {name} (HTTP {result.status_code})."
            )

    def acquire(self) -> bool:
        result = self.http.put(
            self._url("worker.lock"),
            headers={
                **self._headers(),
                "x-ms-blob-type": "BlockBlob",
                "If-None-Match": "*",
            },
            data=b"",
            timeout=45,
            allow_redirects=False,
        )
        if result.status_code not in {201, 409, 412}:
            raise RuntimeError(
                f"Cannot initialize writer lock (HTTP {result.status_code})."
            )
        proposed = str(uuid4())
        leased = self.http.put(
            self._url("worker.lock"),
            params={"comp": "lease"},
            headers={
                **self._headers(),
                "x-ms-lease-action": "acquire",
                "x-ms-lease-duration": "-1",
                "x-ms-proposed-lease-id": proposed,
            },
            timeout=45,
            allow_redirects=False,
        )
        if (
            leased.status_code == 409
            and leased.headers.get("x-ms-error-code") == "LeaseAlreadyPresent"
        ):
            return False
        if leased.status_code != 201 or leased.headers.get("x-ms-lease-id") != proposed:
            raise RuntimeError(
                f"Exclusive writer lock could not be verified (HTTP {leased.status_code}). No refresh started."
            )
        self.lease_id = proposed
        return True

    def release(self) -> None:
        if not self.lease_id:
            return
        result = self.http.put(
            self._url("worker.lock"),
            params={"comp": "lease"},
            headers={
                **self._headers(),
                "x-ms-lease-action": "release",
                "x-ms-lease-id": self.lease_id,
            },
            timeout=45,
            allow_redirects=False,
        )
        if result.status_code != 200:
            raise RuntimeError(
                f"Writer lock release failed (HTTP {result.status_code}); check the worker job before recovery."
            )
        self.lease_id = ""

FIELDS = ['MetricKey', 'Section', 'Measure', 'Unit', 'Aggregation', 'CutoffFamily', 'NumeratorKey', 'NumeratorSection', 'NumeratorMeasure', 'NumeratorManufacturer', 'NumeratorRequireProduct', 'DenominatorKey', 'DenominatorSection', 'DenominatorMeasure', 'DenominatorManufacturer', 'DenominatorRequireProduct', 'SortIndex']
BASE = [{'MetricKey': 'ims-market-units', 'Section': 'IMS / Market', 'Measure': 'IMS Market Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'product-units', 'NumeratorSection': 'Pricing', 'NumeratorMeasure': 'Product Selling units', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'true', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': 10}, {'MetricKey': 'ims-abbott-units', 'Section': 'IMS / Market', 'Measure': 'IMS Abbott Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'abbott-units', 'NumeratorSection': 'Pricing', 'NumeratorMeasure': 'Product Selling units', 'NumeratorManufacturer': 'Abbott', 'NumeratorRequireProduct': 'true', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': 20}, {'MetricKey': 'ims-volume-share', 'Section': 'IMS / Market', 'Measure': 'IMS Abbott Volume Share', 'Unit': '%', 'Aggregation': 'RATIO', 'CutoffFamily': 'IMS', 'NumeratorKey': 'abbott-units', 'NumeratorSection': 'Pricing', 'NumeratorMeasure': 'Product Selling units', 'NumeratorManufacturer': 'Abbott', 'NumeratorRequireProduct': 'true', 'DenominatorKey': 'product-units', 'DenominatorSection': 'Pricing', 'DenominatorMeasure': 'Product Selling units', 'DenominatorManufacturer': '*', 'DenominatorRequireProduct': 'true', 'SortIndex': 30}, {'MetricKey': 'ims-market-value', 'Section': 'IMS / Market', 'Measure': 'IMS Market Value', 'Unit': '£', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'product-value', 'NumeratorSection': 'Pricing', 'NumeratorMeasure': 'Product Value £', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'true', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': 40}, {'MetricKey': 'ims-value-share', 'Section': 'IMS / Market', 'Measure': 'IMS Abbott Value Share', 'Unit': '%', 'Aggregation': 'RATIO', 'CutoffFamily': 'IMS', 'NumeratorKey': 'abbott-value', 'NumeratorSection': 'Pricing', 'NumeratorMeasure': 'Product Value £', 'NumeratorManufacturer': 'Abbott', 'NumeratorRequireProduct': 'true', 'DenominatorKey': 'product-value', 'DenominatorSection': 'Pricing', 'DenominatorMeasure': 'Product Value £', 'DenominatorManufacturer': '*', 'DenominatorRequireProduct': 'true', 'SortIndex': 50}, {'MetricKey': 'ef-selling-units', 'Section': 'Ex-Factory', 'Measure': 'Ex-factory Selling Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'EF', 'NumeratorKey': 'ef-ads-units', 'NumeratorSection': 'Ex-Factory', 'NumeratorMeasure': 'ADS Selling units', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': 60}, {'MetricKey': 'ef-value', 'Section': 'Ex-Factory', 'Measure': 'Ex-factory Value', 'Unit': '£', 'Aggregation': 'SUM', 'CutoffFamily': 'EF', 'NumeratorKey': 'ef-ads-value', 'NumeratorSection': 'Ex-Factory', 'NumeratorMeasure': 'ADS Value £', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': 70}]
ADDITIONS = [{'MetricKey': 'gm-abbott-units', 'Section': 'GM S&OP', 'Measure': 'IMS Abbott Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'gm-abbott-units', 'NumeratorSection': 'Market and Share Working', 'NumeratorMeasure': 'IMS Abbott Selling units', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1000'}, {'MetricKey': 'gm-abbott-value', 'Section': 'GM S&OP', 'Measure': 'IMS Abbott Value', 'Unit': '£', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'gm-abbott-value', 'NumeratorSection': 'Market and Share Working', 'NumeratorMeasure': 'IMS Abbott Value £', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1010'}, {'MetricKey': 'gm-market-units', 'Section': 'GM S&OP', 'Measure': 'IMS Market Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'gm-market-units', 'NumeratorSection': 'Market and Share Working', 'NumeratorMeasure': 'IMS Market Selling units', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1020'}, {'MetricKey': 'gm-market-value', 'Section': 'GM S&OP', 'Measure': 'IMS Market Value', 'Unit': '£', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'gm-market-value', 'NumeratorSection': 'Market and Share Working', 'NumeratorMeasure': 'IMS Market Value £', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1030'}, {'MetricKey': 'gm-pi-units', 'Section': 'GM S&OP', 'Measure': 'PI Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'gm-pi-units', 'NumeratorSection': 'Market and Share Working', 'NumeratorMeasure': 'PI Selling units', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1040'}, {'MetricKey': 'gm-pi-value', 'Section': 'GM S&OP', 'Measure': 'PI Value', 'Unit': '£', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'gm-pi-value', 'NumeratorSection': 'Market and Share Working', 'NumeratorMeasure': 'PI Value £', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1050'}, {'MetricKey': 'gm-net-units', 'Section': 'GM S&OP', 'Measure': 'Total IMS minus PI Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'gm-net-units', 'NumeratorSection': 'Ex-Factory', 'NumeratorMeasure': 'Total IMS minus PI Selling units', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1060'}, {'MetricKey': 'gm-net-value', 'Section': 'GM S&OP', 'Measure': 'Total IMS minus PI Value', 'Unit': '£', 'Aggregation': 'SUM', 'CutoffFamily': 'IMS', 'NumeratorKey': 'gm-net-value', 'NumeratorSection': 'Ex-Factory', 'NumeratorMeasure': 'IMS minus PI Value £', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1070'}, {'MetricKey': 'gm-community-units', 'Section': 'GM S&OP', 'Measure': 'Community ADS Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'EF', 'NumeratorKey': 'gm-community-units', 'NumeratorSection': 'Ex-Factory', 'NumeratorMeasure': 'Community ADS Selling units', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1080'}, {'MetricKey': 'gm-community-value', 'Section': 'GM S&OP', 'Measure': 'Community ADS Value', 'Unit': '£', 'Aggregation': 'SUM', 'CutoffFamily': 'EF', 'NumeratorKey': 'gm-community-value', 'NumeratorSection': 'Ex-Factory', 'NumeratorMeasure': 'Community ADS Value £', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1090'}, {'MetricKey': 'gm-ads-units', 'Section': 'GM S&OP', 'Measure': 'Sector | ADS Units', 'Unit': 'Units', 'Aggregation': 'SUM', 'CutoffFamily': 'EF', 'NumeratorKey': 'gm-ads-units', 'NumeratorSection': 'Sector Total', 'NumeratorMeasure': 'Sector | ADS Selling units', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1100'}, {'MetricKey': 'gm-ads-value', 'Section': 'GM S&OP', 'Measure': 'Sector | ADS Value', 'Unit': '£', 'Aggregation': 'SUM', 'CutoffFamily': 'EF', 'NumeratorKey': 'gm-ads-value', 'NumeratorSection': 'Sector Total', 'NumeratorMeasure': 'Sector | ADS Value £', 'NumeratorManufacturer': '*', 'NumeratorRequireProduct': 'false', 'DenominatorKey': '', 'DenominatorSection': '', 'DenominatorMeasure': '', 'DenominatorManufacturer': '', 'DenominatorRequireProduct': 'false', 'SortIndex': '1110'}]

def prepare_rules(existing):
    rows=list(csv.DictReader(io.StringIO(existing))) if existing is not None else list(BASE)
    if not rows or any(set(r)!=set(FIELDS) for r in rows):
        raise ValueError('Existing report rules have an unknown schema; no file changed.')
    keys=[r['MetricKey'] for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate metric identities; no file changed.')
    for row in ADDITIONS:
        old=next((r for r in rows if r['MetricKey']==row['MetricKey']),None)
        if old is not None and old!=row:raise ValueError('Existing GM rule differs: '+row['MetricKey'])
        if old is None:rows.append(row)
    definitions={}
    for row in rows:
        for part in ['Numerator','Denominator']:
            key=row[part+'Key']
            if not key:continue
            spec=tuple(row[part+k] for k in ['Section','Measure','Manufacturer','RequireProduct'])
            if key in definitions and definitions[key]!=spec:raise ValueError('Conflicting component '+key)
            definitions[key]=spec
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=FIELDS,lineterminator='\n');w.writeheader();w.writerows(rows)
    return out.getvalue(),len(rows)

def main():
    if WORKSPACE.startswith('__') or LAKEHOUSE.startswith('__'):raise ValueError('Use the company-bound setup file in the private delivery ZIP.')
    root=f'abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}'
    path=root+'/Files/ForecastMasterControls/ReportMeasureRules.csv'
    store=OneLakeQueueStore(WORKSPACE,LAKEHOUSE,notebookutils.credentials.getToken)
    if not store.acquire():raise RuntimeError('Refresh worker is busy. Wait for it to finish and run this setup cell again.')
    try:
        existing=notebookutils.fs.head(path,1048576) if notebookutils.fs.exists(path) else None
        if existing is not None and len(existing.encode('utf-8'))>=1048576:raise ValueError('Rules exceed safe read limit; no file changed.')
        candidate,count=prepare_rules(existing)
        if candidate==existing:
            print('READY: GM reporting rules already present. No file changed.')
            return
        stamp=datetime.now(UTC).strftime('%Y%m%dT%H%M%S')+'-'+str(uuid4())
        backup=root+'/Files/ForecastMasterRefreshState/report-upgrades/GM-R16/'+stamp
        notebookutils.fs.mkdirs(backup)
        before=existing if existing is not None else ''
        notebookutils.fs.put(backup+'/rules-before.csv',before,False)
        notebookutils.fs.put(backup+'/receipt.json',json.dumps({'BeforeExisted':existing is not None,'BeforeSHA256':hashlib.sha256(before.encode()).hexdigest(),'AfterSHA256':hashlib.sha256(candidate.encode()).hexdigest(),'Rows':count}),False)
        if notebookutils.fs.head(backup+'/rules-before.csv',1048576)!=before:raise RuntimeError('Backup readback failed; live rules unchanged.')
        current=notebookutils.fs.head(path,1048576) if notebookutils.fs.exists(path) else None
        if current!=existing:raise RuntimeError('Rules changed concurrently; no overwrite performed.')
        notebookutils.fs.put(path,candidate,True)
        if notebookutils.fs.head(path,1048576)!=candidate:raise RuntimeError('Rule write outcome requires inspection; do not rerun blindly.')
        print('READY: added GM reporting measures; existing rules retained. Backup: '+backup)
        print('NEXT: click the existing native Refresh Demand button ONCE. Wait for SUCCESS and ModelRefresh COMPLETED before reviewing or publishing.')
    finally:store.release()

if __name__=='__main__':main()
