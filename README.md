# Kappa Foundation — BFIN Group Assignment

This project evaluates an investment policy for the Kappa Foundation. The current source of truth is the Jupyter notebook [`notebooks/BFIN.ipynb`](notebooks/BFIN.ipynb); this README and `requirements.txt` describe that version of the analysis.

## Case and analysis scope

- **Historical decision date and information cutoff:** 31 December 2022.
- **Estimation period:** January 2015–December 2022. The effective sample is calculated after aligning market returns and factor observations.
- **Frozen out-of-sample evaluation:** January 2023–December 2025. These observations are used to evaluate the frozen strategy, not to set its original inputs.
- The analysis funds the two mandatory nominal payments first, then constructs a U.S. equity growth sleeve for a 2030 real-value objective.
- The notebook covers bond valuation and liability-funding risk; market and Fama–French data preparation; portfolio construction under sample-covariance and single-index risk models; factor-model analysis; sensitivity and decision-reversal tests; and the frozen out-of-sample evaluation.
- The revised-mandate section is intentionally pending until the official revised mandate is available.

The historical data were retrieved after the case decision date. The notebook documents the resulting retrospective-data and security-selection limitations; the analysis is not a live, point-in-time backtest or investment advice.

## Project layout

```text
.
├── README.md
├── requirements.txt
├── notebooks/
│   └── BFIN.ipynb
├── src/
│   ├── 01_download_market_data.py
│   └── 02_download_french_factors.py
├── data/
│   ├── raw/         # Downloaded source data and eligibility evidence
│   ├── processed/  # Aligned monthly prices, returns, and factor series
│   └── frozen/     # Optional approved initial-policy snapshot
└── outputs/
    ├── figures/
    └── tables/
```

## Setup

Use Python 3.10 or later. From the repository root, create and activate a virtual environment, then install the project dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Open `notebooks/BFIN.ipynb` in VS Code with the Jupyter extension, select the `.venv` Python interpreter as the notebook kernel, and run the cells from top to bottom.

## Data and reproducibility

The notebook can rebuild the analysis from the saved raw data in `data/raw/` without internet access. Its canonical Yahoo input is `yahoo_market_data_raw.csv`; the pickle copy is retained as an archive. Fama–French data are parsed from the saved raw text. The saved `security_eligibility_2022.csv` is also an input to the analysis.

The notebook includes a separate data-retrieval workflow for refreshing Yahoo Finance and Kenneth French source files when internet access is available. The scripts in `src/` are optional retrieval helpers; use the notebook for the complete analysis and output-generation workflow. Refreshing source data can change downstream results, so retain the source files used for a particular analysis.

Running the analysis writes processed data to `data/processed/` and CSV tables and figures to `outputs/`. Do not edit downloaded raw files manually.

### Initial-policy freeze

The notebook's initial-policy snapshot is an explicit, create-once action, not a routine part of rebuilding the analysis. Leave `CREATE_INITIAL_FREEZE = False` unless the team has approved creating the snapshot. When enabled, the cell writes the policy record and raw-input checksums under `data/frozen/`; preserve that original snapshot and its inputs rather than overwriting them during later mandate analysis.

## Outputs

Generated outputs include liability and bond analytics, data and return diagnostics, portfolio assumptions and allocations, covariance matrices, factor-model results, sensitivity and robustness tables, the frozen-strategy-versus-SPY evaluation, and the initial decision record. The revised-mandate status is recorded separately and remains pending in the current notebook.

## Dependencies

`requirements.txt` lists the notebook's direct third-party dependencies. Python standard-library modules are not listed. The dependencies are intentionally not pinned to a machine-specific environment freeze.
