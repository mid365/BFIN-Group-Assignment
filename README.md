# Kappa Foundation Investment Policy

**BFIN Group Assignment — quantitative investment research**

## Executive summary

This repository develops an investment policy for a fictional Kappa Foundation mandate. The analysis prioritizes two fixed nominal payments, then invests the remaining capital in a constrained U.S. equity growth portfolio intended to support a 2030 real-value objective. The primary analysis is in [`notebooks/BFIN.ipynb`](notebooks/BFIN.ipynb).

The notebook's selected initial growth strategy is `Utility_SingleIndex`, using a CAPM-style expected-return framework, a single-index covariance model, and base risk aversion \(A=4\). The saved decision tables show 12 eligible candidates (10 common stocks and two ETFs), a 15% common-stock weight limit, and a 35% ETF weight limit. The policy is long-only and fully invested within the growth sleeve; borrowing, short selling, and derivatives are prohibited.

The stored results report that the 2024 and 2027 liabilities are fully funded under their contractual funding plans. In the 36-month frozen evaluation from January 2023 through December 2025, the saved evaluation table reports that the recommended strategy underperformed SPY on cumulative and annualized return, Sharpe ratio, and maximum drawdown. These are historical results under the documented data and assumptions, not forecasts or investment advice.

> **Target reconciliation:** The baseline inflation assumption is 2.5% annually, so the USD 8 million real 2030 objective is USD 9,747,223.18 nominal. The notebook derives this from the baseline parameter and regenerates the mandate, feasibility, sensitivity, and initial-decision tables. `Section_02_Summary.csv` is a checked-in legacy summary; no repository script or notebook cell generates it, so its target and dependent CAGR diagnostic were reconciled directly. The 2.0% scenario remains available in the inflation sensitivity table.

## Research objectives and investment problem

The project addresses a liability-aware allocation problem with three stated case objectives:

1. Reserve capital for a USD 2.4 million scholarship-program payment in 2024.
2. Reserve capital for a USD 3.6 million learning-centre payment in 2027.
3. Invest the residual growth capital toward a USD 8 million real-value objective in 2030, expressed in December 2022 purchasing power.

The historical decision date and information cutoff are **31 December 2022**. The requested estimation window is January 2015–December 2022; after aligning asset returns with factor observations, the decision record reports **95 common monthly observations from February 2015 through December 2022**. The frozen out-of-sample evaluation covers **January 2023–December 2025** and is not used to re-estimate or re-optimize the initial policy.

## Methodology

### Liability funding and bond analysis

The notebook analyzes a five-bond case set using yields, spot-curve repricing, duration, convexity, and interest-rate and interpolation sensitivities. The saved funding plan assigns:

| Liability | Funding instrument | Funding treatment | Initial cost in saved output |
|---|---|---|---:|
| 2024 scholarship payment | Beta, a two-year zero-coupon bond | Maturity matched to the payment | USD 2,214,672 |
| 2027 learning-centre payment | Delta, a five-year coupon bond | Coupons ring-fenced; 0% base reinvestment assumption | USD 3,021,151 |

The saved table reports a total liability reserve cost of approximately **USD 5,235,823**. The resulting growth budget before initial trading costs is approximately **USD 6,764,177**.

### Data preparation and return construction

- Daily Yahoo Finance history is retained as a raw CSV and archival pickle. The notebook uses adjusted close, takes the last available adjusted close in each calendar month, and calculates simple monthly returns as \(P_t/P_{t-1}-1\).
- The market universe is AAPL, MSFT, JPM, JNJ, PG, HD, CAT, CVX, KO, WMT, SPY, and IWM. SPY is the growth benchmark.
- Eligibility evidence for the historical decision date is stored in [`data/raw/security_eligibility_2022.csv`](data/raw/security_eligibility_2022.csv).
- Monthly Fama–French `Mkt-RF`, `SMB`, `HML`, and `RF` observations are parsed from the Kenneth French Data Library source file. The raw values are converted from percent to decimal units, then separated into estimation and evaluation periods.
- The source records document retrieval dates, dataset roles, and processing details: [`yahoo_source_record.csv`](data/raw/yahoo_source_record.csv) and [`french_source_record.csv`](data/raw/french_source_record.csv).

### Portfolio construction

The notebook compares mean-variance utility portfolios under sample-covariance and single-index covariance estimates. The base expected-return inputs use an RF-plus-beta-times-market-risk-premium framework; risk aversion is set to \(A=4\), with sensitivity analysis at other risk-aversion values. It also evaluates an `Eta_Historical_MaxSharpe` alternative and compares strategy candidates under common risk assumptions.

The saved constraint table specifies a fully invested, long-only growth sleeve, a 15% common-stock weight cap, and a 35% ETF weight cap. The mandate prohibits borrowing, short selling, and derivatives. Sensitivity analyses examine risk-model choice, return assumptions, concentration limits, trading costs, and decision-reversal conditions.

The initial allocation table includes both liability reserves and growth holdings. The saved decision record assigns approximately **USD 6,757,420** to the growth sleeve after an initial one-way trading-cost assumption of **10 basis points**.

### Factor analysis and frozen evaluation

The analysis includes CAPM and Fama–French three-factor regressions for asset and portfolio diagnostics. The notebook reports annualized alpha, factor loadings, fit statistics, and statistical significance. **The notebook metadata says the FF3 specification still needs confirmation against the course's Lecture 7 material; verify it before presenting those results as final.**

For out-of-sample evaluation, the initial strategy and target weights are held fixed; the policy applies an annual 31 December rebalance and the documented one-way trading cost, without re-estimation or re-optimization. The saved evaluation table reports:

| Strategy | Cumulative return | Annualized return | Annualized volatility | Sharpe ratio* | Maximum drawdown |
|---|---:|---:|---:|---:|---:|
| Utility_SingleIndex | 70.99% | 19.58% | 13.16% | 1.074 | -10.70% |
| SPY benchmark | 85.50% | 22.87% | 11.95% | 1.401 | -8.33% |

*The saved table calculates Sharpe using the evaluation-period risk-free observations. See [`Table_E1_Frozen_Evaluation.csv`](outputs/tables/Table_E1_Frozen_Evaluation.csv) for the recorded metrics.

The notebook also provides an eight-year historical bootstrap diagnostic. Its simulated target-hit share is sample- and assumption-dependent and must not be interpreted as a forecast or guarantee. Target-dependent bootstrap values should not be relied on until the conflicting nominal-target outputs noted above are reconciled.

## Data sources and sample periods

| Dataset | Source and role | Period used |
|---|---|---|
| Equity and ETF prices | Yahoo Finance via `yfinance`; adjusted-close history for the fixed 12-security universe | Raw retrieval requested 2015-01-01 to 2026-01-01 (end date exclusive); estimation through Dec 2022 and evaluation through Dec 2025 |
| U.S. equity factors | Kenneth French Data Library, F-F Research Data Factors; monthly `Mkt-RF`, `SMB`, `HML`, `RF` | Case period Jan 2015–Dec 2025, split into estimation through Dec 2022 and evaluation Jan 2023–Dec 2025 |
| Eligibility evidence | Historical eligibility records and SEC filing references in the checked-in evidence CSV | Evidence associated with the 2022 decision date |

The effective estimation sample begins in February 2015 because the first monthly return requires a prior-month price. The notebook's stored diagnostics report 95 estimation observations and 36 evaluation observations.

## Repository structure

```text
.
├── README.md
├── requirements.txt
├── notebooks/
│   └── BFIN.ipynb                         # Main end-to-end research analysis
├── src/
│   ├── 01_download_market_data.py         # Yahoo Finance data retrieval and diagnostics
│   └── 02_download_french_factors.py      # French factors retrieval and period files
├── data/
│   ├── raw/                               # Source data, eligibility evidence, provenance
│   ├── processed/                         # Monthly aligned prices, returns, and factors
│   └── frozen/                            # Reserved for optional approved policy snapshot
└── outputs/
    ├── figures/                           # Generated figures
    └── tables/                            # Generated CSV summaries and diagnostics
```

### Important data files

- [`data/raw/yahoo_market_data_raw.csv`](data/raw/yahoo_market_data_raw.csv) — portable raw Yahoo Finance data used by the notebook.
- [`data/raw/yahoo_market_data_raw.pkl`](data/raw/yahoo_market_data_raw.pkl) — archival pickle copy; the notebook uses the CSV as its canonical input.
- [`data/raw/F-F_Research_Data_Factors_CSV.zip`](data/raw/F-F_Research_Data_Factors_CSV.zip) and [`data/raw/F-F_Research_Data_Factors_raw.txt`](data/raw/F-F_Research_Data_Factors_raw.txt) — original factor source archive and extracted text.
- [`data/processed/monthly_adjusted_prices.csv`](data/processed/monthly_adjusted_prices.csv), [`monthly_returns_estimation_2015_2022.csv`](data/processed/monthly_returns_estimation_2015_2022.csv), and [`monthly_returns_evaluation_2023_2025.csv`](data/processed/monthly_returns_evaluation_2023_2025.csv) — analysis-ready market data.
- Processed factor files in [`data/processed/`](data/processed/) retain the estimation, evaluation, case, and full-current series.

### Main output groups

The notebook writes CSV results to [`outputs/tables/`](outputs/tables/) and a decision-record preview to [`outputs/Initial_Decision_Record_22Oct2026.pdf`](outputs/Initial_Decision_Record_22Oct2026.pdf). After running the notebook, generate the formal, two-page submission PDF with `python src\04_generate_initial_decision_record.py`; it is saved as [`outputs/Initial_Decision_Record_Formal_22Oct2026.pdf`](outputs/Initial_Decision_Record_Formal_22Oct2026.pdf). The notebook also writes the frozen strategy comparison chart to [`outputs/figures/Figure_E1_Frozen_Strategy_vs_SPY.png`](outputs/figures/Figure_E1_Frozen_Strategy_vs_SPY.png).

- `Section_02_Summary.csv`, `Section_04_Summary.csv` — liability funding and portfolio decision summaries.
- `Table_B*.csv` — bond analytics, funding plans, term structures, and rate/interpolation stresses.
- `Table_D*.csv` — candidate universe, source records, eligibility, return construction, and data diagnostics.
- `Table_P*.csv` — expected returns, covariance estimates, constraints, candidate strategies, allocations, and robustness tests.
- `Table_E*.csv` — frozen out-of-sample performance, rebalancing costs, and trading-cost sensitivity.
- `Table_F*.csv` — factor-model estimates and interpretation.
- `Table_G*.csv` — 2030 goal, inflation sensitivity, reversal thresholds, and historical bootstrap diagnostics.
- `Table_I*.csv` — initial decision record, monitoring triggers, and freeze audit.
- `Table_R1_Revised_Mandate_Status.csv` — records that a revised mandate was not supplied in the reviewed notebook.

Useful entry points include [`Table_B2_Funding_Plan.csv`](outputs/tables/Table_B2_Funding_Plan.csv), [`Table_P8_Decision_Candidates.csv`](outputs/tables/Table_P8_Decision_Candidates.csv), [`Table_P7_Full_Allocation.csv`](outputs/tables/Table_P7_Full_Allocation.csv), [`Table_G1_2030_Goal_Feasibility.csv`](outputs/tables/Table_G1_2030_Goal_Feasibility.csv), and [`Table_I1_Initial_Decision_Record.csv`](outputs/tables/Table_I1_Initial_Decision_Record.csv).

## Installation and setup

The checked-in notebook metadata records Python 3.13.15. The dependency list is intentionally unpinned, so later package releases may produce different behavior or numerical results.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with `source .venv/bin/activate` after creating it. In VS Code, install or enable the Jupyter extension and select the `.venv` Python interpreter as the notebook kernel.

The direct dependencies in [`requirements.txt`](requirements.txt) are `ipykernel`, `matplotlib`, `numpy`, `pandas`, `scipy`, `statsmodels`, and `yfinance`. Python standard-library modules used by the notebook and scripts are not listed separately.

## Running the analysis

Run the single main notebook [`notebooks/BFIN.ipynb`](notebooks/BFIN.ipynb) from top to bottom. The notebook resolves paths whether opened from the repository root or from `notebooks/`.

1. Create and activate the environment, then install `requirements.txt`.
2. Open `notebooks/BFIN.ipynb` and select the project environment as the kernel.
3. Run every cell in order. This prepares case assumptions, analyzes bonds and liabilities, loads/builds market and factor datasets, estimates portfolios, runs sensitivities, evaluates the frozen policy, and writes outputs.
4. Review the generated tables and the caveats below before interpreting or publishing results.

The checked-in raw files support the notebook's offline data workflow. The notebook also contains a separate optional refresh workflow, and the scripts in `src/` can retrieve data independently when internet access is available:

```powershell
python src/01_download_market_data.py
python src/02_download_french_factors.py
```

These scripts overwrite their corresponding downloaded source/processed files. Preserve a copy of the exact inputs used for a result set; refreshing historical market or factor data can change results.

## Assumptions, limitations, and reproducibility

- **Historical information cutoff:** The decision model excludes observations after 31 December 2022 from initial estimation. The 2023–2025 period is reserved for frozen evaluation.
- **Retrospective sources:** The source records show the data were retrieved in October 2026, after the historical decision date. The factor source may revise historical observations, and the current security universe is supported by retrospective eligibility evidence. This is not a point-in-time live backtest and may involve survivorship or look-ahead limitations.
- **Inflation and terminal objective:** The notebook treats 2.5% inflation as a planning assumption and includes sensitivity cases; it is not an inflation forecast. Saved target-dependent outputs currently conflict and require reconciliation.
- **Risk and return estimates:** CAPM-style expected returns, covariance estimates, a historical bootstrap, and regression diagnostics are model-based estimates. They do not guarantee realized return, drawdown, or goal attainment.
- **Risk tolerance:** The case references a trustee loss concern near 15%, but the metric and horizon are not specified in the facts/assumptions table; the notebook treats it as a diagnostic, not a formal constraint.
- **Factor-model confirmation:** Notebook metadata flags the FF3 implementation for confirmation against Lecture 7 before final academic interpretation.
- **Clean-checkout rerun:** Notebook metadata notes that a clean end-to-end rerun requires the submitted raw-data folder. Raw inputs are present in this repository, but verify the complete workflow from a fresh checkout before claiming a fully reproducible submission.
- **Revised mandate:** The notebook marks the revised mandate as not supplied in the reviewed files. Its response section is therefore a placeholder, not a completed recommendation.
- **Initial policy freeze:** The notebook sets `CREATE_INITIAL_FREEZE = False`. Creating the snapshot is an explicit, create-once action that should only be enabled after approval; the repository's `data/frozen/` folder is currently empty.
- **Environment:** `requirements.txt` does not pin package versions. The recorded environment is available in [`Table_A2_Environment.csv`](outputs/tables/Table_A2_Environment.csv); reproduce with the same versions where practical and retain refreshed raw data and generated outputs together.

## Technologies

Python, Jupyter Notebook, pandas, NumPy, SciPy, statsmodels, Matplotlib, and yfinance.

## References

- Kenneth French Data Library — [F-F Research Data Factors](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip); retrieval and unit details are recorded in [`data/raw/french_source_record.csv`](data/raw/french_source_record.csv).
- Yahoo Finance market data retrieved via `yfinance`; settings and retrieval provenance are recorded in [`data/raw/yahoo_source_record.csv`](data/raw/yahoo_source_record.csv).
- Historical security-eligibility evidence, including SEC filing references, is catalogued in [`data/raw/security_eligibility_2022.csv`](data/raw/security_eligibility_2022.csv).
