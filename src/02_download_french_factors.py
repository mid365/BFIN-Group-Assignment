# ============================================================
# KAPPA FOUNDATION
# KENNETH FRENCH FACTOR DATA RETRIEVAL
# ============================================================

from pathlib import Path
from datetime import datetime
from importlib.metadata import version
from io import StringIO

import urllib.request
import zipfile
import re

import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. DATA SOURCE
# ============================================================

DATASET_NAME = "F-F Research Data Factors"

URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/"
    "ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"
)


# ============================================================
# 3. CASE WINDOWS
# ============================================================

CASE_START = "2015-01-31"

DECISION_CUTOFF = "2022-12-31"

EVALUATION_START = "2023-01-31"
EVALUATION_END = "2025-12-31"


# ============================================================
# 4. RAW FILE PATHS
# ============================================================

RAW_ZIP_FILE = (
    RAW_DIR
    / "F-F_Research_Data_Factors_CSV.zip"
)

RAW_TEXT_FILE = (
    RAW_DIR
    / "F-F_Research_Data_Factors_raw.txt"
)


# ============================================================
# 5. DOWNLOAD ORIGINAL KENNETH FRENCH FILE
# ============================================================

print("=" * 60)
print("Downloading Kenneth French factor data")
print("=" * 60)

urllib.request.urlretrieve(
    URL,
    RAW_ZIP_FILE
)

print(
    "Saved raw ZIP:",
    RAW_ZIP_FILE
)


# ============================================================
# 6. EXTRACT RAW TEXT
# ============================================================

with zipfile.ZipFile(
    RAW_ZIP_FILE,
    "r"
) as zip_file:

    zip_members = (
        zip_file.namelist()
    )

    if len(zip_members) == 0:
        raise ValueError(
            "Kenneth French ZIP file is empty."
        )

    source_filename = (
        zip_members[0]
    )

    raw_bytes = (
        zip_file.read(
            source_filename
        )
    )

    raw_text = (
        raw_bytes.decode(
            "latin1"
        )
    )


RAW_TEXT_FILE.write_text(
    raw_text,
    encoding="utf-8"
)

print(
    "Saved raw text:",
    RAW_TEXT_FILE
)


# ============================================================
# 7. LOCATE MONTHLY FACTOR TABLE
# ============================================================

lines = raw_text.splitlines()

header_index = None


for i, line in enumerate(lines):

    if (
        "Mkt-RF" in line
        and "SMB" in line
        and "HML" in line
        and "RF" in line
    ):

        header_index = i
        break


if header_index is None:

    raise ValueError(
        "Could not locate monthly factor-data header."
    )


# ============================================================
# 8. EXTRACT MONTHLY OBSERVATIONS
# ============================================================

monthly_lines = []


for line in lines[
    header_index + 1:
]:

    # Kenneth French monthly rows use YYYYMM
    if re.match(
        r"^\s*\d{6}\s*,",
        line
    ):

        monthly_lines.append(
            line
        )

    elif monthly_lines:

        # Once monthly data have started,
        # stop at the next non-monthly section.
        break


if len(monthly_lines) == 0:

    raise ValueError(
        "No monthly factor observations found."
    )


# ============================================================
# 9. PARSE MONTHLY DATA
# ============================================================

monthly_csv_text = (
    "Date,Mkt-RF,SMB,HML,RF\n"
    + "\n".join(
        monthly_lines
    )
)


factors_full = pd.read_csv(
    StringIO(
        monthly_csv_text
    )
)


# ============================================================
# 10. CLEAN AND CONVERT UNITS
# ============================================================

FACTOR_COLUMNS = [
    "Mkt-RF",
    "SMB",
    "HML",
    "RF"
]


for column in FACTOR_COLUMNS:

    factors_full[column] = (
        pd.to_numeric(
            factors_full[column],
            errors="coerce"
        )
        / 100
    )


# Kenneth French dates are YYYYMM.
# Convert them to calendar month-end timestamps.

factors_full["Date"] = (
    pd.to_datetime(
        factors_full["Date"]
        .astype(str)
        .str.strip(),
        format="%Y%m"
    )
    + pd.offsets.MonthEnd(0)
)


factors_full = (
    factors_full
    .set_index("Date")
    .sort_index()
)


# Remove rows where factor conversion failed.

factors_full = (
    factors_full
    .dropna(
        subset=FACTOR_COLUMNS
    )
)


# ============================================================
# 11. CREATE CASE-RELEVANT WINDOWS
# ============================================================

# Full current parsed history is retained only for audit/reference.

factors_case = (
    factors_full.loc[
        CASE_START:
        EVALUATION_END
    ]
    .copy()
)


# ------------------------------------------------------------
# Decision / estimation sample
# ONLY information through December 2022
# ------------------------------------------------------------

factors_estimation = (
    factors_full.loc[
        CASE_START:
        DECISION_CUTOFF
    ]
    .copy()
)


# ------------------------------------------------------------
# Out-of-sample evaluation
# January 2023 through December 2025
# ------------------------------------------------------------

factors_evaluation = (
    factors_full.loc[
        EVALUATION_START:
        EVALUATION_END
    ]
    .copy()
)


# ============================================================
# 12. VALIDATION CHECKS
# ============================================================

if factors_estimation.empty:

    raise ValueError(
        "Estimation factor sample is empty."
    )


if factors_evaluation.empty:

    raise ValueError(
        "Evaluation factor sample is empty."
    )


if (
    factors_estimation.index.max()
    > pd.Timestamp(
        DECISION_CUTOFF
    )
):

    raise ValueError(
        "Post-2022 factor observations leaked "
        "into estimation sample."
    )


if (
    factors_evaluation.index.min()
    < pd.Timestamp(
        EVALUATION_START
    )
):

    raise ValueError(
        "Pre-2023 observations leaked "
        "into evaluation sample."
    )


# ============================================================
# 13. SAVE PROCESSED FILES
# ============================================================

FULL_PARSED_FILE = (
    PROCESSED_DIR
    / "french_factors_full_current.csv"
)

CASE_FILE = (
    PROCESSED_DIR
    / "french_factors_case_2015_2025.csv"
)

ESTIMATION_FILE = (
    PROCESSED_DIR
    / "french_factors_estimation_2015_2022.csv"
)

EVALUATION_FILE = (
    PROCESSED_DIR
    / "french_factors_evaluation_2023_2025.csv"
)


factors_full.to_csv(
    FULL_PARSED_FILE
)

factors_case.to_csv(
    CASE_FILE
)

factors_estimation.to_csv(
    ESTIMATION_FILE
)

factors_evaluation.to_csv(
    EVALUATION_FILE
)


# ============================================================
# 14. SOURCE RECORD
# ============================================================

source_record = pd.DataFrame({

    "Source": [
        "Kenneth French Data Library"
    ],

    "DatasetIdentifier": [
        DATASET_NAME
    ],

    "SourceURL": [
        URL
    ],

    "RetrievalDate": [
        datetime.now().isoformat(
            timespec="seconds"
        )
    ],

    "RawZipFile": [
        RAW_ZIP_FILE.name
    ],

    "RawTextFile": [
        RAW_TEXT_FILE.name
    ],

    "RawUnits": [
        "Percent per month"
    ],

    "ProcessedUnits": [
        "Decimal return per month"
    ],

    "DecisionInformationCutoff": [
        DECISION_CUTOFF
    ],

    "EstimationWindow": [
        "2015-01 to 2022-12"
    ],

    "EvaluationWindow": [
        "2023-01 to 2025-12"
    ],

    "Post2025Treatment": [
        (
            "Retained only in the full current parsed "
            "dataset; excluded from all case estimation "
            "and evaluation analysis."
        )
    ],

    "HistoricalRevisionCaveat": [
        (
            "The file was retrieved after the 2022 "
            "decision date and may contain revisions "
            "to historical observations."
        )
    ],

    "PythonPackage": [
        "pandas"
    ],

    "PandasVersion": [
        version(
            "pandas"
        )
    ]
})


SOURCE_RECORD_FILE = (
    RAW_DIR
    / "french_source_record.csv"
)


source_record.to_csv(
    SOURCE_RECORD_FILE,
    index=False
)


# ============================================================
# 15. DIAGNOSTIC OUTPUT
# ============================================================

print()
print("=" * 60)
print("KENNETH FRENCH DOWNLOAD COMPLETE")
print("=" * 60)

print(
    "Current full parsed range:",
    factors_full.index.min(),
    "to",
    factors_full.index.max()
)

print(
    "Case dataset:",
    factors_case.index.min(),
    "to",
    factors_case.index.max()
)

print(
    "Estimation dataset:",
    factors_estimation.index.min(),
    "to",
    factors_estimation.index.max()
)

print(
    "Evaluation dataset:",
    factors_evaluation.index.min(),
    "to",
    factors_evaluation.index.max()
)

print()

print(
    "Estimation observations:",
    len(
        factors_estimation
    )
)

print(
    "Evaluation observations:",
    len(
        factors_evaluation
    )
)

print()

print(
    "Saved estimation file:",
    ESTIMATION_FILE
)

print(
    "Saved evaluation file:",
    EVALUATION_FILE
)

print(
    "Saved source record:",
    SOURCE_RECORD_FILE
)

print("=" * 60)