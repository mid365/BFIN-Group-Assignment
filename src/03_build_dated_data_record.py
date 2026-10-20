"""Build the 22-Oct dated data record from EXISTING records; no network access.
Place this script inside the repository's src/ directory, then run:
    python src/03_build_dated_data_record.py
"""
from pathlib import Path
import csv
import hashlib
import json
import platform
from importlib.metadata import version, PackageNotFoundError

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
DEST = ROOT / 'data' / 'Dated_Data_Record.csv'
FROZEN = ROOT / 'data' / 'frozen' / 'initial_policy_2026-10-22.json'

def first_row(filename):
    with (RAW / filename).open(encoding='utf-8-sig', newline='') as f:
        return next(csv.DictReader(f))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ver(name):
    try: return version(name)
    except PackageNotFoundError: return 'NOT INSTALLED'

y = first_row('yahoo_source_record.csv')
f = first_row('french_source_record.csv')
if not FROZEN.exists():
    raise FileNotFoundError(f'Missing frozen policy: {FROZEN}')
policy = json.loads(FROZEN.read_text(encoding='utf-8'))
checksums = policy.get('SourceSHA256', {})

common = {
    'HistoricalDecisionDate': policy['HistoricalDecisionDate'],
    'EstimationCutoff': policy['HistoricalInformationCutoff'],
    'EvaluationWindow': '2023-01 through 2025-12',
    'PythonVersionCurrentlyRunning': platform.python_version(),
    'PandasVersionAtRetrieval': y.get('PandasVersion', 'NOT DOCUMENTED'),
    'DownloadIssuesAndResolution': 'NOT DOCUMENTED - inspect download logs/Git history; do not assume no errors',
}

def check_frozen(key, file):
    path = RAW / file
    if not path.exists(): raise FileNotFoundError(path)
    actual = sha(path)
    expected = checksums.get(key)
    if expected and actual != expected:
        raise ValueError(f'{file}: SHA256 differs from frozen policy')
    return actual

rows = [
    dict(common, Source='Yahoo Finance via yfinance', DatasetIdentifier=y.get('Dataset','Daily market price history'),
         SourceURL='https://finance.yahoo.com/', RawFile='data/raw/yahoo_market_data_raw.csv',
         ActualRetrievalDateTime=y.get('RetrievalDate','NOT DOCUMENTED'),
         RequestedDateRange=f"{y.get('RequestedStartDate','?')} to {y.get('RequestedEndDateExclusive','?')} (end exclusive)",
         DownloadSettings=f"tickers={y.get('Tickers','?')}; auto_adjust={y.get('AutoAdjust','?')}; actions={y.get('Actions','?')}; group_by={y.get('GroupBy','?')}; threads={y.get('Threads','?')}",
         ReturnConstruction=y.get('CorporateActionTreatment','') + ' Daily adjusted prices aggregated to calendar month-end, then percent changes; verify notebook treatment.',
         Units='Decimal monthly total-return proxy',
         RetrievalPackageVersion=f"yfinance={y.get('YFinanceVersion','NOT DOCUMENTED')}",
         SHA256=check_frozen('YahooRawCSV','yahoo_market_data_raw.csv')),
    dict(common, Source='Kenneth French Data Library', DatasetIdentifier=f.get('DatasetIdentifier','NOT DOCUMENTED'),
         SourceURL=f.get('SourceURL','NOT DOCUMENTED'), RawFile='data/raw/F-F_Research_Data_Factors_raw.txt',
         ActualRetrievalDateTime=f.get('RetrievalDate','NOT DOCUMENTED'),
         RequestedDateRange='Full source ZIP downloaded; case filter 2015-01 through 2025-12',
         DownloadSettings='urllib.request.urlretrieve ZIP; monthly Mkt-RF, SMB, HML, RF rows selected',
         ReturnConstruction='Monthly factor percentage values divided by 100; YYYYMM aligned to calendar month-end; incomplete rows excluded',
         Units='Decimal returns per month',
         RetrievalPackageVersion=f"pandas={f.get('PandasVersion','NOT DOCUMENTED')}",
         SHA256=check_frozen('FrenchRawText','F-F_Research_Data_Factors_raw.txt')),
    dict(common, Source='Security eligibility evidence', DatasetIdentifier='Security eligibility as of 2022-12-31',
         SourceURL='NOT DOCUMENTED in supplied retrieval records', RawFile='data/raw/security_eligibility_2022.csv',
         ActualRetrievalDateTime='NOT DOCUMENTED - file modification time is not proof of retrieval',
         RequestedDateRange='Eligibility at historical decision date 2022-12-31',
         DownloadSettings='NOT DOCUMENTED', ReturnConstruction='N/A (eligibility evidence, not return series)',
         Units='N/A', RetrievalPackageVersion='NOT DOCUMENTED',
         SHA256=check_frozen('EligibilityEvidence','security_eligibility_2022.csv')),
]
DEST.parent.mkdir(parents=True, exist_ok=True)
with DEST.open('w',encoding='utf-8-sig',newline='') as out:
    writer=csv.DictWriter(out,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f'Created: {DEST}')
for row in rows:
    print(f" - {row['Source']}: {row['ActualRetrievalDateTime']} | SHA256 verified")
print('Review the NOT DOCUMENTED fields before submission.')
