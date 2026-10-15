# ============================================================
# KAPPA FOUNDATION
# YAHOO FINANCE MARKET DATA RETRIEVAL
# ============================================================

from pathlib import Path
from datetime import datetime
from importlib.metadata import version

import pandas as pd
import yfinance as yf


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. CASE UNIVERSE
# ============================================================

TICKERS = [
    "AAPL",
    "MSFT",
    "JPM",
    "JNJ",
    "PG",
    "HD",
    "CAT",
    "CVX",
    "KO",
    "WMT",
    "SPY",
    "IWM"
]


# ============================================================
# 3. REQUEST WINDOW
# ============================================================

# Need estimation data through Dec 2022
# and evaluation data through Dec 2025.
#
# yfinance end date is exclusive.

START_DATE = "2015-01-01"
END_DATE = "2026-01-01"


# ============================================================
# 4. DOWNLOAD SETTINGS
# ============================================================

DOWNLOAD_SETTINGS = {

    "start":
        START_DATE,

    "end":
        END_DATE,

    "auto_adjust":
        False,

    "actions":
        True,

    "group_by":
        "column",

    "progress":
        False,

    "threads":
        True
}


# ============================================================
# 5. DOWNLOAD DATA
# ============================================================

print("=" * 60)
print("Downloading Yahoo Finance market data")
print("=" * 60)

print(
    "Tickers:",
    TICKERS
)

print(
    "Requested range:",
    START_DATE,
    "to",
    END_DATE,
    "(end exclusive)"
)


market_raw = yf.download(
    TICKERS,
    **DOWNLOAD_SETTINGS
)


# ============================================================
# 6. BASIC VALIDATION
# ============================================================

if market_raw.empty:
    raise ValueError(
        "Yahoo Finance returned an empty dataset."
    )


if not isinstance(
    market_raw.columns,
    pd.MultiIndex
):
    raise ValueError(
        "Unexpected Yahoo data structure: "
        "expected MultiIndex columns."
    )


downloaded_tickers = (
    market_raw.columns
    .get_level_values(1)
    .unique()
    .tolist()
)


missing_tickers = [
    ticker
    for ticker in TICKERS
    if ticker not in downloaded_tickers
]


print()
print(
    "Downloaded tickers:",
    downloaded_tickers
)

print(
    "Missing tickers:",
    missing_tickers
)


if missing_tickers:
    raise ValueError(
        f"Yahoo download is missing tickers: "
        f"{missing_tickers}"
    )


# ============================================================
# 7. CHECK EXPECTED PRICE FIELD
# ============================================================

available_fields = (
    market_raw.columns
    .get_level_values(0)
    .unique()
    .tolist()
)


print(
    "Available fields:",
    available_fields
)


if "Adj Close" not in available_fields:
    raise ValueError(
        "Adjusted Close is not available in the "
        "Yahoo response. Return-construction code "
        "must not proceed until this is resolved."
    )


# ============================================================
# 8. CHECK DATE COVERAGE
# ============================================================

first_date = (
    market_raw.index.min()
)

last_date = (
    market_raw.index.max()
)


print()
print(
    "First observation:",
    first_date
)

print(
    "Last observation:",
    last_date
)


if first_date > pd.Timestamp(
    "2015-01-05"
):
    raise ValueError(
        "Downloaded history begins unexpectedly late."
    )


if last_date < pd.Timestamp(
    "2025-12-30"
):
    raise ValueError(
        "Downloaded history does not cover "
        "the full evaluation period through Dec 2025."
    )


# ============================================================
# 9. CHECK ADJUSTED-CLOSE COVERAGE
# ============================================================

adjusted_close = (
    market_raw["Adj Close"]
    .copy()
)


adj_close_summary = pd.DataFrame({

    "Ticker":
        TICKERS,

    "NonMissingAdjClose":
        [
            adjusted_close[ticker]
            .notna()
            .sum()

            for ticker
            in TICKERS
        ],

    "FirstValidDate":
        [
            adjusted_close[ticker]
            .first_valid_index()

            for ticker
            in TICKERS
        ],

    "LastValidDate":
        [
            adjusted_close[ticker]
            .last_valid_index()

            for ticker
            in TICKERS
        ]
})


print()
print(
    "Adjusted-close coverage:"
)

print(
    adj_close_summary
    .to_string(
        index=False
    )
)


# ============================================================
# 10. SAVE RAW RESPONSE
# ============================================================

RAW_PICKLE_FILE = (
    RAW_DIR
    / "yahoo_market_data_raw.pkl"
)

RAW_CSV_FILE = (
    RAW_DIR
    / "yahoo_market_data_raw.csv"
)


market_raw.to_pickle(
    RAW_PICKLE_FILE
)

market_raw.to_csv(
    RAW_CSV_FILE
)


# ============================================================
# 11. SAVE DOWNLOAD DIAGNOSTICS
# ============================================================

DIAGNOSTIC_FILE = (
    RAW_DIR
    / "yahoo_download_diagnostics.csv"
)


adj_close_summary.to_csv(
    DIAGNOSTIC_FILE,
    index=False
)


# ============================================================
# 12. SOURCE RECORD
# ============================================================

source_record = pd.DataFrame({

    "Source": [
        "Yahoo Finance via yfinance"
    ],

    "Dataset": [
        "Daily market price history"
    ],

    "RetrievalDate": [
        datetime.now().isoformat(
            timespec="seconds"
        )
    ],

    "Tickers": [
        ",".join(TICKERS)
    ],

    "RequestedStartDate": [
        START_DATE
    ],

    "RequestedEndDateExclusive": [
        END_DATE
    ],

    "AutoAdjust": [
        False
    ],

    "Actions": [
        True
    ],

    "GroupBy": [
        "column"
    ],

    "Threads": [
        True
    ],

    "ReturnPriceField": [
        "Adj Close"
    ],

    "CorporateActionTreatment": [
        (
            "Monthly returns are constructed from "
            "Yahoo Adjusted Close with auto_adjust=False."
        )
    ],

    "RawPickleFile": [
        RAW_PICKLE_FILE.name
    ],

    "RawCSVFile": [
        RAW_CSV_FILE.name
    ],

    "DiagnosticFile": [
        DIAGNOSTIC_FILE.name
    ],

    "YFinanceVersion": [
        version(
            "yfinance"
        )
    ],

    "PandasVersion": [
        version(
            "pandas"
        )
    ]
})


SOURCE_RECORD_FILE = (
    RAW_DIR
    / "yahoo_source_record.csv"
)


source_record.to_csv(
    SOURCE_RECORD_FILE,
    index=False
)


# ============================================================
# 13. FINAL OUTPUT
# ============================================================

print()
print("=" * 60)
print("YAHOO MARKET DATA DOWNLOAD COMPLETE")
print("=" * 60)

print(
    "Raw shape:",
    market_raw.shape
)

print(
    "First date:",
    first_date
)

print(
    "Last date:",
    last_date
)

print(
    "Saved raw pickle:",
    RAW_PICKLE_FILE
)

print(
    "Saved raw CSV:",
    RAW_CSV_FILE
)

print(
    "Saved diagnostics:",
    DIAGNOSTIC_FILE
)

print(
    "Saved source record:",
    SOURCE_RECORD_FILE
)

print("=" * 60)