# %% [markdown]
# # Kappa Foundation — Sections 01–04 Requirement-Matched Analysis
# 
# **Decision date:** 31 December 2022  
# **Initial capital:** USD 12 million  
# **Mandatory payments:** USD 2.4 million on 31 December 2024 and USD 3.6 million on 31 December 2027  
# **2030 goal:** after the mandatory payments, preserve at least the purchasing power of USD 8 million in December-2022 dollars.
# 
# This notebook is intentionally limited to evidence required for Sections 01–04. It avoids secondary diagnostics that do not materially support the board decision.
# 
# | Requirement | Where addressed |
# |---|---|
# | Full USD 12m allocation; funded payments; real-value goal; risk preference and risk-aversion sensitivity | Sections 01 and 04 |
# | Bond valuation/YTM; incomplete term structure; duration/convexity checked against exact repricing; parallel and curve-shape shocks; link to liabilities | Section 02 |
# | 8–12 stocks across ≥4 sectors + 2 distinct U.S. equity ETFs; benchmark; pre-2023 information discipline; reproducibility | Section 03 |
# | Recommended allocation + credible rejected alternative; sample covariance vs single-index; expected returns, constraints, implementation and sensitivity | Section 04 |
# 
# **Freeze rule for later evaluation:** once the 22 October initial decision is submitted, the target growth weights and benchmark are frozen. The strategy may be rebalanced back to the same target weights on the predeclared schedule, but it is not re-estimated or re-optimized using 2023–2025 information.

# %%
# ============================================================
# 01A. SETUP, CASE FACTS AND MODELLING ASSUMPTIONS
# ============================================================

import numpy as np
import pandas as pd
import statsmodels.api as sm

from scipy.optimize import brentq, minimize
from scipy.stats import norm
from pathlib import Path
from IPython.display import display

pd.set_option("display.float_format", lambda x: f"{x:,.4f}")

# Works whether the notebook is run from /notebooks or project root.
CWD = Path.cwd()
PROJECT_ROOT = CWD.parent if CWD.name.lower() == "notebooks" else CWD
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"

for directory in [RAW_DIR, PROCESSED_DIR, TABLE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# -------------------------
# Case facts
# -------------------------
DECISION_DATE = pd.Timestamp("2022-12-31")
INITIAL_CAPITAL = 12_000_000
LIABILITIES = {2024: 2_400_000, 2027: 3_600_000}
REAL_TARGET_2030 = 8_000_000
FACE_VALUE = 1_000

BOND_DATA = pd.DataFrame({
    "Bond": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
    "Maturity": [1, 2, 3, 5, 8],
    "CouponRate": [0.000, 0.000, 0.040, 0.035, 0.045],
    "Price": [958.77, 922.78, 1002.49, 986.07, 1040.71],
})

# -------------------------
# Information windows
# -------------------------
ESTIMATION_START = "2015-01-01"
ESTIMATION_END = "2022-12-31"
EVALUATION_START = "2023-01-01"
EVALUATION_END = "2025-12-31"

# -------------------------
# Team assumptions / policy choices
# -------------------------
# Inflation is a planning assumption, not a promised forecast.
BASE_INFLATION = 0.025

# A=4 is a moderate base preference, not inferred mechanically from the 15% concern.
# The required comparison is performed for A = 2, 4, 6, 8.
BASE_RISK_AVERSION = 4
RISK_AVERSION_VALUES = [2, 4, 6, 8]

# Additional concentration limits chosen by the team.
MAX_STOCK_WEIGHT = 0.15
MAX_ETF_WEIGHT = 0.35

# One-way implementation cost assumption.
BASE_TRADING_COST = 0.001  # 10 bps

# Bond stress magnitudes. These are stress scenarios, not forecasts.
PARALLEL_SHOCK = 0.0100      # +/-100 bp
CURVE_SHAPE_SHOCK = 0.0075   # +/-75 bp slope change

NOMINAL_TARGET_2030 = REAL_TARGET_2030 * (1 + BASE_INFLATION) ** 8

Table_A1_Mandate_Assumptions = pd.DataFrame({
    "Item": [
        "Initial capital",
        "2024 mandatory payment",
        "2027 mandatory payment",
        "2030 real-value objective",
        "Base inflation assumption",
        "2030 nominal target",
        "Trustee loss concern",
        "Base risk aversion A",
        "Risk-aversion comparison",
        "Maximum stock weight",
        "Maximum ETF weight",
        "One-way trading cost",
    ],
    "Value": [
        INITIAL_CAPITAL,
        LIABILITIES[2024],
        LIABILITIES[2027],
        REAL_TARGET_2030,
        BASE_INFLATION,
        NOMINAL_TARGET_2030,
        "Losses approaching 15%; horizon/metric unspecified",
        BASE_RISK_AVERSION,
        str(RISK_AVERSION_VALUES),
        MAX_STOCK_WEIGHT,
        MAX_ETF_WEIGHT,
        BASE_TRADING_COST,
    ],
    "Treatment": [
        "Case fact", "Case fact", "Case fact", "Case fact",
        "Team planning assumption; document source/rationale in final memo",
        "Derived from real target and inflation assumption",
        "Case fact; treated as diagnostic rather than hard constraint",
        "Base preference parameter; sensitivity required",
        "Shows how assumed risk preference changes the choice",
        "Additional concentration limit",
        "Additional concentration limit",
        "Implementation assumption",
    ],
})

display(Table_A1_Mandate_Assumptions)

# %% [markdown]
# # 02. Bond Valuation & Liability Funding
# 
# This section keeps only the bond evidence explicitly required by the assignment:
# 
# 1. YTM and valuation of all five case bonds;
# 2. a stated treatment of the incomplete term structure;
# 3. duration and convexity checked against exact repricing;
# 4. a funded-payment plan for 2024 and 2027;
# 5. one parallel-rate stress and one curve-shape stress, related back to the payment obligations.
# 
# **Incomplete curve treatment:** known spot rates are bootstrapped from the quoted bonds. Missing annual maturities are filled by **linear interpolation of spot rates**. This is an explicit modelling assumption, not an observed market curve.

# %%
# ============================================================
# 02A. BOND FUNCTIONS AND ONE EXPLICIT TERM-STRUCTURE METHOD
# ============================================================

def bond_cashflows(face, coupon_rate, maturity):
    coupon = face * coupon_rate
    cashflows = np.full(int(maturity), coupon, dtype=float)
    cashflows[-1] += face
    return cashflows


def price_from_ytm(face, coupon_rate, maturity, ytm):
    cashflows = bond_cashflows(face, coupon_rate, maturity)
    t = np.arange(1, int(maturity) + 1)
    return np.sum(cashflows / (1 + ytm) ** t)


def solve_ytm(face, coupon_rate, maturity, market_price):
    objective = lambda y: price_from_ytm(face, coupon_rate, maturity, y) - market_price
    return brentq(objective, -0.50, 1.00)


def duration_convexity(face, coupon_rate, maturity, ytm):
    cashflows = bond_cashflows(face, coupon_rate, maturity)
    t = np.arange(1, int(maturity) + 1)
    pv = cashflows / (1 + ytm) ** t
    price = pv.sum()

    macaulay = np.sum(t * pv) / price
    modified = macaulay / (1 + ytm)
    convexity = (
        np.sum(cashflows * t * (t + 1) / (1 + ytm) ** (t + 2)) / price
    )
    return macaulay, modified, convexity


def price_from_spot_curve(face, coupon_rate, maturity, spot_curve):
    cashflows = bond_cashflows(face, coupon_rate, maturity)
    return sum(
        cashflows[t - 1] / (1 + spot_curve[t]) ** t
        for t in range(1, int(maturity) + 1)
    )


def linear_spot(t, t_left, r_left, t_right, r_right):
    weight = (t - t_left) / (t_right - t_left)
    return r_left + weight * (r_right - r_left)


def build_spot_curve():
    """Bootstrap 1Y, 2Y, 3Y, 5Y, 8Y; linearly interpolate 4Y, 6Y, 7Y."""
    curve = {}

    alpha = BOND_DATA.loc[BOND_DATA["Bond"] == "Alpha"].iloc[0]
    beta = BOND_DATA.loc[BOND_DATA["Bond"] == "Beta"].iloc[0]
    gamma = BOND_DATA.loc[BOND_DATA["Bond"] == "Gamma"].iloc[0]
    delta = BOND_DATA.loc[BOND_DATA["Bond"] == "Delta"].iloc[0]
    epsilon = BOND_DATA.loc[BOND_DATA["Bond"] == "Epsilon"].iloc[0]

    curve[1] = FACE_VALUE / alpha["Price"] - 1
    curve[2] = (FACE_VALUE / beta["Price"]) ** (1 / 2) - 1

    gamma_coupon = FACE_VALUE * gamma["CouponRate"]
    remaining_gamma_cf = (
        gamma["Price"]
        - gamma_coupon / (1 + curve[1])
        - gamma_coupon / (1 + curve[2]) ** 2
    )
    curve[3] = ((FACE_VALUE + gamma_coupon) / remaining_gamma_cf) ** (1 / 3) - 1

    def delta_error(s5):
        s4 = linear_spot(4, 3, curve[3], 5, s5)
        temp = {1: curve[1], 2: curve[2], 3: curve[3], 4: s4, 5: s5}
        return price_from_spot_curve(
            FACE_VALUE, delta["CouponRate"], int(delta["Maturity"]), temp
        ) - delta["Price"]

    curve[5] = brentq(delta_error, -0.25, 0.50)
    curve[4] = linear_spot(4, 3, curve[3], 5, curve[5])

    def epsilon_error(s8):
        s6 = linear_spot(6, 5, curve[5], 8, s8)
        s7 = linear_spot(7, 5, curve[5], 8, s8)
        temp = {
            1: curve[1], 2: curve[2], 3: curve[3], 4: curve[4], 5: curve[5],
            6: s6, 7: s7, 8: s8,
        }
        return price_from_spot_curve(
            FACE_VALUE, epsilon["CouponRate"], int(epsilon["Maturity"]), temp
        ) - epsilon["Price"]

    curve[8] = brentq(epsilon_error, -0.25, 0.50)
    curve[6] = linear_spot(6, 5, curve[5], 8, curve[8])
    curve[7] = linear_spot(7, 5, curve[5], 8, curve[8])
    return curve


spot_curve = build_spot_curve()
Table_B1_Term_Structure = pd.DataFrame({
    "MaturityYear": sorted(spot_curve),
    "SpotRate": [spot_curve[t] for t in sorted(spot_curve)],
    "Status": [
        "Bootstrapped" if t in {1, 2, 3, 5, 8} else "Linear spot interpolation"
        for t in sorted(spot_curve)
    ],
})

display(Table_B1_Term_Structure)

# %%
# ============================================================
# 02B. YTM, DURATION/CONVEXITY AND EXACT REPRICING CHECK
# ============================================================

DC_CHECK_SHOCK = 0.0100  # +/-100 bp local YTM check
bond_rows = []
dc_rows = []

for _, row in BOND_DATA.iterrows():
    ytm = solve_ytm(FACE_VALUE, row["CouponRate"], int(row["Maturity"]), row["Price"])
    macaulay, modified, convexity = duration_convexity(
        FACE_VALUE, row["CouponRate"], int(row["Maturity"]), ytm
    )
    spot_reprice = price_from_spot_curve(
        FACE_VALUE, row["CouponRate"], int(row["Maturity"]), spot_curve
    )

    bond_rows.append({
        "Bond": row["Bond"],
        "MarketPrice": row["Price"],
        "YTM": ytm,
        "MacaulayDuration": macaulay,
        "ModifiedDuration": modified,
        "Convexity": convexity,
        "SpotCurveReprice": spot_reprice,
        "SpotRepricingError": spot_reprice - row["Price"],
    })

    for shock in [-DC_CHECK_SHOCK, DC_CHECK_SHOCK]:
        exact_price = price_from_ytm(
            FACE_VALUE, row["CouponRate"], int(row["Maturity"]), ytm + shock
        )
        exact_change = exact_price / row["Price"] - 1
        approx_change = -modified * shock + 0.5 * convexity * shock ** 2
        dc_rows.append({
            "Bond": row["Bond"],
            "YieldShock": shock,
            "ExactPriceChangePct": exact_change,
            "DurationConvexityApproxPct": approx_change,
            "ApproximationErrorPctPts": approx_change - exact_change,
        })

Table_B2_Bond_Analytics = pd.DataFrame(bond_rows)
Table_B3_Duration_Convexity_Check = pd.DataFrame(dc_rows)

# Internal QA: the chosen curve should reproduce quoted bonds closely.
if Table_B2_Bond_Analytics["SpotRepricingError"].abs().max() > 1e-4:
    raise ValueError("Spot-curve construction does not reproduce quoted bond prices closely enough.")

display(Table_B2_Bond_Analytics)
display(Table_B3_Duration_Convexity_Check)

# %%
# ============================================================
# 02C. FUNDED-PAYMENT PLAN
# ============================================================

beta = BOND_DATA.loc[BOND_DATA["Bond"] == "Beta"].iloc[0]
delta = BOND_DATA.loc[BOND_DATA["Bond"] == "Delta"].iloc[0]

# 2024: exact 2-year zero-coupon maturity match.
beta_units = LIABILITIES[2024] / FACE_VALUE
beta_initial_cost = beta_units * beta["Price"]
beta_contractual_cash_2024 = beta_units * FACE_VALUE

# 2027: Delta matures in year 5. Interim coupons are ring-fenced as cash.
# Base funding assumption: 0% reinvestment on pre-2027 coupons.
delta_cashflows_per_bond = bond_cashflows(
    FACE_VALUE, delta["CouponRate"], int(delta["Maturity"])
)
delta_2027_value_per_bond_at_zero_reinvestment = delta_cashflows_per_bond.sum()
delta_units = LIABILITIES[2027] / delta_2027_value_per_bond_at_zero_reinvestment
delta_initial_cost = delta_units * delta["Price"]
delta_contractual_cash_2027 = delta_units * delta_2027_value_per_bond_at_zero_reinvestment

LIABILITY_BUCKET_COST = beta_initial_cost + delta_initial_cost
GROWTH_BUDGET_BEFORE_COSTS = INITIAL_CAPITAL - LIABILITY_BUCKET_COST

Table_B4_Funding_Plan = pd.DataFrame({
    "Liability": ["2024 scholarship", "2027 learning centre"],
    "RequiredPayment": [LIABILITIES[2024], LIABILITIES[2027]],
    "FundingAsset": ["Beta", "Delta"],
    "Units": [beta_units, delta_units],
    "InitialCost": [beta_initial_cost, delta_initial_cost],
    "ContractualCashAvailable": [beta_contractual_cash_2024, delta_contractual_cash_2027],
    "FundingRatio": [
        beta_contractual_cash_2024 / LIABILITIES[2024],
        delta_contractual_cash_2027 / LIABILITIES[2027],
    ],
    "FundingMethod": [
        "2Y zero-coupon maturity match",
        "5Y Delta; interim coupons ring-fenced; 0% base reinvestment",
    ],
})

display(Table_B4_Funding_Plan)
print(f"Up-front liability reserve cost: USD {LIABILITY_BUCKET_COST:,.2f}")
print(f"Residual budget available for the growth sleeve before trading cost: USD {GROWTH_BUDGET_BEFORE_COSTS:,.2f}")

# %%
# ============================================================
# 02D. REQUIRED RATE STRESSES AND LINK TO PAYMENT OBLIGATIONS
# ============================================================

def shift_spot_curve(base_curve, parallel_shift=0.0, slope_shift=0.0):
    maturities = sorted(base_curve)
    midpoint = (min(maturities) + max(maturities)) / 2
    half_range = (max(maturities) - min(maturities)) / 2

    shocked = {}
    for t in maturities:
        slope_loading = (t - midpoint) / half_range
        shocked[t] = base_curve[t] + parallel_shift + slope_shift * slope_loading
    return shocked


curve_scenarios = {
    "Base": (0.0, 0.0),
    "Parallel +100bp": (PARALLEL_SHOCK, 0.0),
    "Parallel -100bp": (-PARALLEL_SHOCK, 0.0),
    "Steepener (+/-75bp slope)": (0.0, CURVE_SHAPE_SHOCK),
    "Flattener (+/-75bp slope)": (0.0, -CURVE_SHAPE_SHOCK),
}

price_rows = []
liability_rows = []

for scenario, (parallel, slope) in curve_scenarios.items():
    shocked_curve = shift_spot_curve(spot_curve, parallel, slope)

    scenario_prices = {}
    for _, row in BOND_DATA.iterrows():
        p = price_from_spot_curve(
            FACE_VALUE, row["CouponRate"], int(row["Maturity"]), shocked_curve
        )
        scenario_prices[row["Bond"]] = p
        price_rows.append({
            "Scenario": scenario,
            "Bond": row["Bond"],
            "ExactRepricedPrice": p,
            "PriceChangePct": p / row["Price"] - 1,
        })

    liability_rows.append({
        "Scenario": scenario,
        "BetaMarketValue": beta_units * scenario_prices["Beta"],
        "DeltaMarketValue": delta_units * scenario_prices["Delta"],
        "TotalLiabilitySleeveMarketValue": (
            beta_units * scenario_prices["Beta"] + delta_units * scenario_prices["Delta"]
        ),
        "2024ContractualFundingRatioIfHeld": 1.0,
        "2027ContractualFundingRatioIfHeldAndCouponsRingFenced": 1.0,
    })

Table_B6_Rate_Scenarios = pd.DataFrame(price_rows)
Table_B7_Liability_Sleeve_Under_Rate_Stress = pd.DataFrame(liability_rows)

# Exact repricing changes mark-to-market values. The held-to-maturity contractual
# payment cash flows remain unchanged under these default-free case assumptions.
display(Table_B6_Rate_Scenarios)
display(Table_B7_Liability_Sleeve_Under_Rate_Stress)

for name, table in {
    "Table_A1_Mandate_Assumptions": Table_A1_Mandate_Assumptions,
    "Table_B1_Term_Structure": Table_B1_Term_Structure,
    "Table_B2_Bond_Analytics": Table_B2_Bond_Analytics,
    "Table_B3_Duration_Convexity_Check": Table_B3_Duration_Convexity_Check,
    "Table_B4_Funding_Plan": Table_B4_Funding_Plan,
    "Table_B6_Rate_Scenarios": Table_B6_Rate_Scenarios,
    "Table_B7_Liability_Sleeve_Under_Rate_Stress": Table_B7_Liability_Sleeve_Under_Rate_Stress,
}.items():
    table.to_csv(TABLE_DIR / f"{name}.csv", index=False)

# %% [markdown]
# # 03. Candidate Universe, Market Data & Reproducibility
# 
# The candidate universe is fixed before optimization: **10 U.S. common stocks across multiple sectors plus 2 U.S.-listed U.S.-equity ETFs with different mandates**. SPY is the simple investable benchmark and market proxy.
# 
# The notebook does **not** treat historical price existence as sufficient evidence of eligibility. Final submission must include a dated `security_eligibility_2022.csv` documenting what each security was at the case date and the source used to verify it.
# 
# January 2015–December 2022 is the estimation period. January 2023–December 2025 is isolated for later frozen-strategy evaluation and is not used to construct the initial portfolio.

# %%
# ============================================================
# 03A. FIXED CANDIDATE UNIVERSE AND ELIGIBILITY EVIDENCE
# ============================================================

STOCKS = [
    "AAPL", "MSFT", "JPM", "JNJ", "PG",
    "HD", "CAT", "CVX", "KO", "WMT",
]
ETFS = ["SPY", "IWM"]
BENCHMARK = "SPY"
CANDIDATE_TICKERS = STOCKS + ETFS

sector_or_mandate = {
    "AAPL": "Information Technology",
    "MSFT": "Information Technology",
    "JPM": "Financials",
    "JNJ": "Health Care",
    "PG": "Consumer Staples",
    "HD": "Consumer Discretionary",
    "CAT": "Industrials",
    "CVX": "Energy",
    "KO": "Consumer Staples",
    "WMT": "Consumer Staples",
    "SPY": "Broad U.S. large-cap equity ETF",
    "IWM": "U.S. small-cap equity ETF",
}

Table_D1_Candidate_Universe = pd.DataFrame({
    "Ticker": CANDIDATE_TICKERS,
    "SecurityType": ["ETF" if t in ETFS else "Common stock" for t in CANDIDATE_TICKERS],
    "SectorOrMandate": [sector_or_mandate[t] for t in CANDIDATE_TICKERS],
    "Role": [
        "Simple investable benchmark and market proxy" if t == BENCHMARK
        else "Growth/diversification candidate"
        for t in CANDIDATE_TICKERS
    ],
})

# Required evidence file — do not substitute present-day survival or price existence.
ELIGIBILITY_FILE = RAW_DIR / "security_eligibility_2022.csv"
required_eligibility_columns = {
    "Ticker",
    "SecurityTypeAtDecisionDate",
    "SectorOrMandateAtDecisionDate",
    "EligibleAtDecisionDate",
    "EvidenceSource",
    "EvidenceDateOrArchiveDate",
    "SelectionRationale",
}

if not ELIGIBILITY_FILE.exists():
    raise FileNotFoundError(
        "Missing data/raw/security_eligibility_2022.csv. "
        "Create dated case-date eligibility evidence before final submission."
    )

Table_D2_Eligibility_Evidence = pd.read_csv(ELIGIBILITY_FILE)
missing_columns = required_eligibility_columns - set(Table_D2_Eligibility_Evidence.columns)
if missing_columns:
    raise ValueError(f"Eligibility evidence is missing columns: {sorted(missing_columns)}")

eligibility = Table_D2_Eligibility_Evidence.set_index("Ticker").reindex(CANDIDATE_TICKERS)
if eligibility.isna().all(axis=1).any():
    missing = eligibility.index[eligibility.isna().all(axis=1)].tolist()
    raise ValueError(f"Missing case-date eligibility evidence for: {missing}")

eligible_flag = eligibility["EligibleAtDecisionDate"].astype(str).str.lower().isin(
    ["true", "1", "yes", "y"]
)
if not eligible_flag.all():
    failed = eligibility.index[~eligible_flag].tolist()
    raise ValueError(f"These candidates are not verified as eligible at the case date: {failed}")

display(Table_D1_Candidate_Universe)
display(Table_D2_Eligibility_Evidence)

# %%
# ============================================================
# 03B. LOAD SAVED RAW YAHOO DATA AND CONSTRUCT MONTHLY RETURNS
# ============================================================

RAW_MARKET_FILE = RAW_DIR / "yahoo_market_data_raw.pkl"
YAHOO_SOURCE_RECORD_FILE = RAW_DIR / "yahoo_source_record.csv"

for required_file in [RAW_MARKET_FILE, YAHOO_SOURCE_RECORD_FILE]:
    if not required_file.exists():
        raise FileNotFoundError(
            f"Missing {required_file}. Run the market-data retrieval script first."
        )

market_raw = pd.read_pickle(RAW_MARKET_FILE)
Table_D3_Yahoo_Source_Record = pd.read_csv(YAHOO_SOURCE_RECORD_FILE)

if not isinstance(market_raw.columns, pd.MultiIndex):
    raise ValueError("Expected saved Yahoo data to have MultiIndex columns.")

available_fields = market_raw.columns.get_level_values(0).unique().tolist()
available_tickers = market_raw.columns.get_level_values(1).unique().tolist()

missing_tickers = [t for t in CANDIDATE_TICKERS if t not in available_tickers]
if missing_tickers:
    raise ValueError(f"Missing candidate tickers in Yahoo raw data: {missing_tickers}")
if "Adj Close" not in available_fields:
    raise ValueError("Adj Close is missing; do not continue return construction.")

adjusted_close_daily = market_raw["Adj Close"][CANDIDATE_TICKERS].copy()
monthly_prices = adjusted_close_daily.resample("ME").last()
monthly_returns = monthly_prices.pct_change(fill_method=None)

estimation_precheck = monthly_returns.loc[
    "2015-01-31":"2022-12-31", CANDIDATE_TICKERS
].copy()
evaluation_precheck = monthly_returns.loc[
    "2023-01-31":"2025-12-31", CANDIDATE_TICKERS
].copy()

# No imputation: use common complete months only.
estimation_returns = estimation_precheck.dropna(how="any")
evaluation_returns = evaluation_precheck.dropna(how="any")

if len(estimation_returns) < 60:
    raise ValueError("Fewer than 60 common monthly observations in 2015–2022.")
if estimation_returns.index.max() > DECISION_DATE:
    raise ValueError("Post-2022 information leaked into the estimation sample.")

# The first return in the estimation window may be mechanically unavailable because
# pct_change requires a prior-month price. Separate that from genuine missing observations.
initial_return_unavailable = estimation_precheck.iloc[0].isna()
other_estimation_missing = estimation_precheck.iloc[1:].isna().sum()
evaluation_missing = evaluation_precheck.isna().sum()

Table_D4_Return_Construction = pd.DataFrame({
    "Item": [
        "Market-data source",
        "Raw frequency",
        "Monthly sampling",
        "Return definition",
        "Corporate-action treatment",
        "Estimation window",
        "Evaluation window",
        "Missing-data treatment",
        "Benchmark",
        "Retrospective-selection limitation",
    ],
    "Treatment": [
        "Yahoo Finance via yfinance; saved raw response",
        "Daily",
        "Last available adjusted close in each calendar month",
        "P_adj,t / P_adj,t-1 - 1",
        "Yahoo Adjusted Close; retrieval settings documented in source record",
        "Jan 2015-Dec 2022",
        "Jan 2023-Dec 2025; isolated from initial decision",
        "Common complete months only; no imputation",
        BENCHMARK,
        "Case universe selected retrospectively; disclosed rather than presented as an unbiased live sample",
    ],
})

monthly_prices.to_csv(PROCESSED_DIR / "monthly_adjusted_prices.csv")
monthly_returns.to_csv(PROCESSED_DIR / "monthly_returns_full.csv")
estimation_returns.to_csv(PROCESSED_DIR / "monthly_returns_estimation_2015_2022.csv")
evaluation_returns.to_csv(PROCESSED_DIR / "monthly_returns_evaluation_2023_2025.csv")

print(f"Estimation observations: {len(estimation_returns)}")
print(f"Evaluation observations: {len(evaluation_returns)}")

if initial_return_unavailable.all() and other_estimation_missing.sum() == 0 and evaluation_missing.sum() == 0:
    print(
        "The only unavailable estimation return is the first month, which is mechanical: "
        "a prior-month price is required to compute a return. No other asset-month observations are missing."
    )
else:
    missing_summary = pd.DataFrame({
        "Ticker": CANDIDATE_TICKERS,
        "InitialReturnUnavailable": initial_return_unavailable.values,
        "OtherEstimationMissing": other_estimation_missing.values,
        "EvaluationMissing": evaluation_missing.values,
    })
    print("Missing observations detected; no values are imputed:")
    display(missing_summary)

display(Table_D3_Yahoo_Source_Record)
display(Table_D4_Return_Construction)

for name, table in {
    "Table_D1_Candidate_Universe": Table_D1_Candidate_Universe,
    "Table_D2_Eligibility_Evidence": Table_D2_Eligibility_Evidence,
    "Table_D3_Yahoo_Source_Record": Table_D3_Yahoo_Source_Record,
    "Table_D4_Return_Construction": Table_D4_Return_Construction,
}.items():
    table.to_csv(TABLE_DIR / f"{name}.csv", index=False)

# %% [markdown]
# # 04. Portfolio Decision, Risk Preferences & Initial Policy
# 
# The portfolio comparison holds the **candidate universe, expected-return inputs, risk aversion and constraints constant** while changing only the required risk estimator:
# 
# - sample covariance; and
# - single-index covariance using SPY as the market proxy.
# 
# Expected returns use a CAPM-style common systematic framework estimated only with information through December 2022. Historical arithmetic means are retained as one compact sensitivity check, not as the base forecast.
# 
# The initial decision uses **single-index utility** as the recommended growth allocation and **Eta's historical maximum-Sharpe strategy** as the credible rejected alternative. The recommendation is a policy choice supported by the evidence, not an automatic model output.

# %%
# ============================================================
# 04A. ALIGN PRE-2023 FRENCH FACTORS AND BUILD EXPECTED RETURNS
# ============================================================

FRENCH_ESTIMATION_FILE = PROCESSED_DIR / "french_factors_estimation_2015_2022.csv"
FRENCH_SOURCE_RECORD_FILE = RAW_DIR / "french_source_record.csv"

if not FRENCH_ESTIMATION_FILE.exists():
    raise FileNotFoundError(
        "Missing processed French factor file. Run the French-factor retrieval script first."
    )
if not FRENCH_SOURCE_RECORD_FILE.exists():
    raise FileNotFoundError(
        "Missing data/raw/french_source_record.csv. Final submission must document dataset, "
        "retrieval date, requested dates/settings and package/version details."
    )

french_estimation = pd.read_csv(
    FRENCH_ESTIMATION_FILE, index_col="Date", parse_dates=True
)
Table_P1_French_Source_Record = pd.read_csv(FRENCH_SOURCE_RECORD_FILE)

common_dates = estimation_returns.index.intersection(french_estimation.index)
returns_for_model = estimation_returns.loc[common_dates, CANDIDATE_TICKERS].copy()
factors_for_model = french_estimation.loc[common_dates].copy()

if len(common_dates) < 60:
    raise ValueError("Fewer than 60 common Yahoo/French monthly observations.")
if common_dates.max() > DECISION_DATE:
    raise ValueError("Post-2022 factor information leaked into estimation.")

rf_monthly = factors_for_model["RF"]
market_excess_monthly = factors_for_model["Mkt-RF"]
BASE_RF_ANNUAL = rf_monthly.mean() * 12
BASE_MARKET_PREMIUM_ANNUAL = market_excess_monthly.mean() * 12

expected_return_rows = []
for ticker in CANDIDATE_TICKERS:
    asset_return = returns_for_model[ticker]
    asset_excess = asset_return - rf_monthly
    X = sm.add_constant(market_excess_monthly)
    model = sm.OLS(asset_excess, X).fit()

    beta = model.params["Mkt-RF"]
    expected_return_rows.append({
        "Ticker": ticker,
        "CAPMBeta": beta,
        "CAPMAlphaMonthly_DiagnosticOnly": model.params["const"],
        "BaseExpectedReturn": BASE_RF_ANNUAL + beta * BASE_MARKET_PREMIUM_ANNUAL,
        "HistoricalAnnualMean_SensitivityOnly": asset_return.mean() * 12,
    })

Table_P2_Expected_Return_Inputs = pd.DataFrame(expected_return_rows).set_index("Ticker")
BASE_EXPECTED_RETURNS = Table_P2_Expected_Return_Inputs["BaseExpectedReturn"]
HISTORICAL_EXPECTED_RETURNS = Table_P2_Expected_Return_Inputs[
    "HistoricalAnnualMean_SensitivityOnly"
]

print("Base expected returns use RF + beta × market risk premium. Estimated CAPM alpha is reported only as a diagnostic and is not added to the forecast.")
display(Table_P1_French_Source_Record)
display(Table_P2_Expected_Return_Inputs)

# %%
# ============================================================
# 04B. REQUIRED SAMPLE-COVARIANCE AND SINGLE-INDEX RISK MODELS
# ============================================================

candidate_returns = returns_for_model[CANDIDATE_TICKERS].copy()
SAMPLE_COV = candidate_returns.cov() * 12

market_returns = returns_for_model[BENCHMARK]
market_variance_monthly = market_returns.var(ddof=1)

si_betas = {}
si_residual_variances = {}
for ticker in CANDIDATE_TICKERS:
    if ticker == BENCHMARK:
        si_betas[ticker] = 1.0
        si_residual_variances[ticker] = 0.0
    else:
        X = sm.add_constant(market_returns)
        model = sm.OLS(candidate_returns[ticker], X).fit()
        si_betas[ticker] = model.params[BENCHMARK]
        si_residual_variances[ticker] = model.resid.var(ddof=1)

single_index_monthly = pd.DataFrame(
    index=CANDIDATE_TICKERS, columns=CANDIDATE_TICKERS, dtype=float
)
for i in CANDIDATE_TICKERS:
    for j in CANDIDATE_TICKERS:
        systematic = si_betas[i] * si_betas[j] * market_variance_monthly
        single_index_monthly.loc[i, j] = systematic + (
            si_residual_variances[i] if i == j else 0.0
        )

SINGLE_INDEX_COV = single_index_monthly * 12

# Internal numerical QA only; not a material decision output.
if np.linalg.eigvalsh(SAMPLE_COV.values).min() < -1e-10:
    raise ValueError("Sample covariance is not positive semidefinite within tolerance.")
if np.linalg.eigvalsh(SINGLE_INDEX_COV.values).min() < -1e-10:
    raise ValueError("Single-index covariance is not positive semidefinite within tolerance.")

# %%
# ============================================================
# 04C. PORTFOLIO FUNCTIONS, CONSTRAINTS AND BASE DECISIONS
# ============================================================

BASE_BOUNDS = [
    (0.0, MAX_ETF_WEIGHT if t in ETFS else MAX_STOCK_WEIGHT)
    for t in CANDIDATE_TICKERS
]


def portfolio_statistics(weights, expected_returns, covariance):
    mu = np.asarray(expected_returns)
    sigma = np.asarray(covariance)
    expected_return = weights @ mu
    variance = weights @ sigma @ weights
    return expected_return, np.sqrt(variance), variance


def optimize_mean_variance_utility(expected_returns, covariance, risk_aversion, bounds):
    mu = np.asarray(expected_returns)
    sigma = np.asarray(covariance)
    n = len(mu)

    def objective(w):
        return -(w @ mu - 0.5 * risk_aversion * (w @ sigma @ w))

    result = minimize(
        objective,
        np.repeat(1 / n, n),
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if not result.success:
        raise RuntimeError(f"Utility optimization failed: {result.message}")
    return result.x


def optimize_max_sharpe(expected_returns, covariance, risk_free_rate, bounds):
    mu = np.asarray(expected_returns)
    sigma = np.asarray(covariance)
    n = len(mu)

    def objective(w):
        vol = np.sqrt(w @ sigma @ w)
        if vol <= 0:
            return 1e6
        return -((w @ mu - risk_free_rate) / vol)

    result = minimize(
        objective,
        np.repeat(1 / n, n),
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if not result.success:
        raise RuntimeError(f"Max-Sharpe optimization failed: {result.message}")
    return result.x


Table_P3_Constraints = pd.DataFrame({
    "Constraint": [
        "Long only",
        "Fully invested growth sleeve",
        "Maximum common-stock weight",
        "Maximum ETF weight",
        "Borrowing",
        "Short selling",
        "Derivatives",
    ],
    "Policy": [
        "Yes", "Yes", MAX_STOCK_WEIGHT, MAX_ETF_WEIGHT,
        "Prohibited", "Prohibited", "Prohibited",
    ],
    "Reason": [
        "Mandate",
        "Compare complete growth allocations on the same capital base",
        "Limit single-name concentration and estimation error",
        "Permit a diversified ETF core without allowing one ETF to dominate",
        "Mandate", "Mandate", "Mandate",
    ],
})

display(Table_P3_Constraints)

# %%
# ============================================================
# 04D. REQUIRED RISK-MODEL COMPARISON
# ============================================================

mu_base = BASE_EXPECTED_RETURNS.loc[CANDIDATE_TICKERS].values

sample_weights = optimize_mean_variance_utility(
    mu_base, SAMPLE_COV.values, BASE_RISK_AVERSION, BASE_BOUNDS
)
single_index_weights = optimize_mean_variance_utility(
    mu_base, SINGLE_INDEX_COV.values, BASE_RISK_AVERSION, BASE_BOUNDS
)

Table_P4_Risk_Model_Comparison = pd.DataFrame({
    "Ticker": CANDIDATE_TICKERS,
    "SampleCovWeight": sample_weights,
    "SingleIndexWeight": single_index_weights,
    "Difference": single_index_weights - sample_weights,
})

risk_model_turnover = 0.5 * np.abs(single_index_weights - sample_weights).sum()

summary_rows = []
for name, weights, cov in [
    ("Sample covariance", sample_weights, SAMPLE_COV.values),
    ("Single-index covariance", single_index_weights, SINGLE_INDEX_COV.values),
]:
    er, vol, var = portfolio_statistics(weights, mu_base, cov)
    summary_rows.append({
        "RiskModel": name,
        "ExpectedReturn": er,
        "Volatility": vol,
        "Utility_A4_UnderOwnRiskModel": er - 0.5 * BASE_RISK_AVERSION * var,
        "LargestWeight": weights.max(),
    })

Table_P5_Risk_Model_Summary = pd.DataFrame(summary_rows)
Table_P5_Risk_Model_Summary["AllocationTurnoverVsOtherModel"] = risk_model_turnover

display(Table_P4_Risk_Model_Comparison)
display(Table_P5_Risk_Model_Summary)
print("Each row above is evaluated under the same covariance model used to optimize that row. A common comparison lens is applied later when choosing the initial policy.")

# %%
# ============================================================
# 04E. RISK-AVERSION COMPARISON + ONE EXPECTED-RETURN SENSITIVITY
# ============================================================

risk_aversion_rows = []
for model_name, covariance in {
    "Sample covariance": SAMPLE_COV.values,
    "Single-index covariance": SINGLE_INDEX_COV.values,
}.items():
    for A in RISK_AVERSION_VALUES:
        w = optimize_mean_variance_utility(mu_base, covariance, A, BASE_BOUNDS)
        er, vol, var = portfolio_statistics(w, mu_base, covariance)
        top3_idx = np.argsort(w)[::-1][:3]
        top3 = ", ".join(f"{CANDIDATE_TICKERS[i]} {w[i]:.1%}" for i in top3_idx)
        risk_aversion_rows.append({
            "RiskModel": model_name,
            "RiskAversionA": A,
            "ExpectedReturn": er,
            "Volatility": vol,
            "Utility": er - 0.5 * A * var,
            "LargestWeight": w.max(),
            "Top3Holdings": top3,
        })

Table_P6_Risk_Aversion_Sensitivity = pd.DataFrame(risk_aversion_rows)

# Compact sensitivity to the expected-return specification.
mu_historical = HISTORICAL_EXPECTED_RETURNS.loc[CANDIDATE_TICKERS].values
historical_mu_weights = optimize_mean_variance_utility(
    mu_historical, SINGLE_INDEX_COV.values, BASE_RISK_AVERSION, BASE_BOUNDS
)
expected_return_turnover = 0.5 * np.abs(historical_mu_weights - single_index_weights).sum()

base_er, base_vol, base_var = portfolio_statistics(
    single_index_weights, mu_base, SINGLE_INDEX_COV.values
)
hist_er_under_hist_mu, hist_vol, hist_var = portfolio_statistics(
    historical_mu_weights, mu_historical, SINGLE_INDEX_COV.values
)

Table_P7_Expected_Return_Sensitivity = pd.DataFrame({
    "ExpectedReturnSpecification": ["CAPM-style base", "Historical arithmetic mean"],
    "ExpectedReturn": [base_er, hist_er_under_hist_mu],
    "Volatility": [base_vol, hist_vol],
    "LargestWeight": [single_index_weights.max(), historical_mu_weights.max()],
    "TurnoverVsBase": [0.0, expected_return_turnover],
})

display(Table_P6_Risk_Aversion_Sensitivity)
display(Table_P7_Expected_Return_Sensitivity)
print(f"Risk-model allocation turnover: {risk_model_turnover:.2%}")
print(f"Expected-return-specification turnover: {expected_return_turnover:.2%}")

# %%
# ============================================================
# 04F. RECOMMENDED STRATEGY VS CREDIBLE REJECTED ALTERNATIVE
# ============================================================

# Eta's claim is operationalized as the strongest in-sample historical
# risk-adjusted portfolio: a historical-mean / sample-covariance max-Sharpe portfolio.
historical_mu = candidate_returns.mean().values * 12
historical_rf = rf_monthly.mean() * 12
eta_weights = optimize_max_sharpe(
    historical_mu, SAMPLE_COV.values, historical_rf, BASE_BOUNDS
)

strategy_weights = {
    "Utility_SampleCov": sample_weights,
    "Utility_SingleIndex": single_index_weights,
    "Eta_Historical_MaxSharpe": eta_weights,
}

# Initial policy choice. The single-index specification is used as the primary, parsimonious
# risk model; the sample-covariance portfolio is retained as the required robustness comparison.
# This is the strategy to freeze in the 22-Oct decision record.
INITIAL_GROWTH_STRATEGY = "Utility_SingleIndex"
CREDIBLE_REJECTED_ALTERNATIVE = "Eta_Historical_MaxSharpe"
initial_growth_weights = strategy_weights[INITIAL_GROWTH_STRATEGY]

# Common-evaluation lens: base expected returns + single-index covariance.
decision_rows = []
for strategy, weights in strategy_weights.items():
    er, vol, var = portfolio_statistics(weights, mu_base, SINGLE_INDEX_COV.values)
    decision_rows.append({
        "Strategy": strategy,
        "ExpectedReturn_CommonLens": er,
        "Volatility_CommonLens": vol,
        "Sharpe_CommonLens": (er - BASE_RF_ANNUAL) / vol,
        "Utility_A4_CommonLens": er - 0.5 * BASE_RISK_AVERSION * var,
        "LargestWeight": weights.max(),
        "DecisionStatus": (
            "Recommended initial growth policy" if strategy == INITIAL_GROWTH_STRATEGY
            else "Credible rejected alternative" if strategy == CREDIBLE_REJECTED_ALTERNATIVE
            else "Required model-comparison portfolio"
        ),
    })

Table_P8_Decision_Candidates = pd.DataFrame(decision_rows)
Table_P9_Strategy_Weights = pd.DataFrame({
    "Ticker": CANDIDATE_TICKERS,
    **{name: weights for name, weights in strategy_weights.items()},
})

display(Table_P8_Decision_Candidates)
display(Table_P9_Strategy_Weights)

# %%
# ============================================================
# 04G. FULL USD 12M INITIAL ALLOCATION
# ============================================================

# The residual budget must cover both growth holdings and initial trading cost.
GROWTH_INVESTED_NOTIONAL = GROWTH_BUDGET_BEFORE_COSTS / (1 + BASE_TRADING_COST)
INITIAL_TRADING_COST = GROWTH_INVESTED_NOTIONAL * BASE_TRADING_COST
growth_dollar_allocations = initial_growth_weights * GROWTH_INVESTED_NOTIONAL

allocation_rows = [
    {
        "Sleeve": "2024 liability",
        "SecurityOrUse": "Beta",
        "DollarAllocation": beta_initial_cost,
        "Role": "Fund 31-Dec-2024 scholarship payment",
    },
    {
        "Sleeve": "2027 liability",
        "SecurityOrUse": "Delta",
        "DollarAllocation": delta_initial_cost,
        "Role": "Fund 31-Dec-2027 learning-centre payment",
    },
]

for ticker, amount in zip(CANDIDATE_TICKERS, growth_dollar_allocations):
    allocation_rows.append({
        "Sleeve": "Growth",
        "SecurityOrUse": ticker,
        "DollarAllocation": amount,
        "Role": "Pursue 2030 real-value objective",
    })

allocation_rows.append({
    "Sleeve": "Implementation",
    "SecurityOrUse": "Initial trading cost",
    "DollarAllocation": INITIAL_TRADING_COST,
    "Role": f"{BASE_TRADING_COST:.2%} one-way cost on initial growth purchases",
})

Table_P10_Full_Allocation = pd.DataFrame(allocation_rows)
Table_P10_Full_Allocation["PercentOfInitialFund"] = (
    Table_P10_Full_Allocation["DollarAllocation"] / INITIAL_CAPITAL
)

allocation_total = Table_P10_Full_Allocation["DollarAllocation"].sum()
if not np.isclose(allocation_total, INITIAL_CAPITAL, atol=0.01):
    raise ValueError("Initial allocation does not reconcile to USD 12 million.")

display(Table_P10_Full_Allocation)
print(f"Full initial use of capital: USD {allocation_total:,.2f}")

# %%
# ============================================================
# 04H. TRUSTEE 15% LOSS CONCERN AND FROZEN IMPLEMENTATION RULE
# ============================================================

recommended_row = Table_P8_Decision_Candidates.loc[
    Table_P8_Decision_Candidates["Strategy"] == INITIAL_GROWTH_STRATEGY
].iloc[0]

# Diagnostic only: use a one-year normal approximation for the growth sleeve.
# The case does not define a horizon or probability for the 15% concern.
z_5pct = norm.ppf(0.05)
growth_5pct_return = (
    recommended_row["ExpectedReturn_CommonLens"] + z_5pct * recommended_row["Volatility_CommonLens"]
)
growth_share_of_total = GROWTH_INVESTED_NOTIONAL / INITIAL_CAPITAL
approx_total_fund_5pct_growth_impact = growth_share_of_total * growth_5pct_return

Table_P11_Risk_Tolerance = pd.DataFrame({
    "Metric": [
        "Trustee reference loss level",
        "Growth share of initial fund",
        "Approximate 5% one-year growth-sleeve return",
        "Approximate growth-only contribution to total-fund return",
        "Difference versus -15% reference",
    ],
    "Value": [
        -0.15,
        growth_share_of_total,
        growth_5pct_return,
        approx_total_fund_5pct_growth_impact,
        approx_total_fund_5pct_growth_impact - (-0.15),
    ],
    "Interpretation": [
        "Reference concern only; not a formal hard limit",
        "Fixed-payment reserve is separated before growth allocation",
        "Normal approximation; diagnostic, not guarantee",
        "Growth sleeve only; this is not a complete total-fund downside measure because bond mark-to-market risk is assessed separately in Section 02",
        "Diagnostic comparison only; the trustee statement does not define a formal horizon or probability",
    ],
})

Table_P12_Implementation_Policy = pd.DataFrame({
    "PolicyItem": [
        "Liability priority",
        "Frozen initial growth strategy",
        "Benchmark",
        "Rebalancing schedule",
        "Rebalancing rule",
        "Re-estimation during 2023-2025 evaluation",
        "Rebalancing trading cost",
        "Maximum stock weight",
        "Maximum ETF weight",
        "Borrowing / shorting / derivatives",
        "Status after 22-Oct submission",
    ],
    "Policy": [
        "Fund mandatory payments before allocating growth capital",
        INITIAL_GROWTH_STRATEGY,
        BENCHMARK,
        "Annually on 31 December; make any scheduled liability payment first",
        "After the liability payment, rebalance the remaining growth sleeve back to the original frozen target weights",
        "No re-estimation or re-optimization; future data cannot rewrite the initial decision",
        f"{BASE_TRADING_COST:.2%} one-way on traded notional",
        f"{MAX_STOCK_WEIGHT:.0%}",
        f"{MAX_ETF_WEIGHT:.0%}",
        "Prohibited",
        "Frozen policy; later evidence is compared against it and recorded in the decision log",
    ],
})

Table_I1_Initial_Decision_Record = pd.DataFrame({
    "DecisionItem": [
        "Case decision date",
        "Candidate universe",
        "Estimation window",
        "Benchmark",
        "2024 payment funding",
        "2027 payment funding",
        "Recommended growth strategy",
        "Rejected alternative",
        "Risk model",
        "Growth capital invested",
        "2030 real-value objective",
        "Base inflation assumption",
        "Base nominal 2030 target",
        "Base risk aversion",
        "Stock / ETF caps",
        "Evaluation window",
        "Rebalancing rule",
        "Re-estimation in evaluation",
        "Initial trading cost",
    ],
    "FrozenPolicy": [
        DECISION_DATE.date().isoformat(),
        ", ".join(CANDIDATE_TICKERS),
        f"Jan-2015 to Dec-2022; {len(common_dates)} common monthly observations",
        BENCHMARK,
        f"Beta zero-coupon; initial cost USD {beta_initial_cost:,.0f}",
        f"Delta + ring-fenced coupons at 0% reinvestment; initial cost USD {delta_initial_cost:,.0f}",
        INITIAL_GROWTH_STRATEGY,
        CREDIBLE_REJECTED_ALTERNATIVE,
        "Single-index covariance",
        f"USD {GROWTH_INVESTED_NOTIONAL:,.2f}",
        f"USD {REAL_TARGET_2030:,.0f} in December-2022 dollars",
        f"{BASE_INFLATION:.2%}",
        f"USD {NOMINAL_TARGET_2030:,.2f}",
        f"A={BASE_RISK_AVERSION}; sensitivity {RISK_AVERSION_VALUES}",
        f"Stock {MAX_STOCK_WEIGHT:.0%}; ETF {MAX_ETF_WEIGHT:.0%}",
        "Jan-2023 to Dec-2025",
        "Annual 31-Dec rebalance to frozen target weights after any scheduled liability payment",
        "None",
        f"{BASE_TRADING_COST:.2%} one-way per dollar traded",
    ],
})
Table_P9b_Initial_Decision_Record = Table_I1_Initial_Decision_Record.rename(
    columns={"DecisionItem": "Item", "FrozenPolicy": "FrozenDecision"}
)

import hashlib
import json

FROZEN_DIR = PROJECT_ROOT / "data" / "frozen"
FROZEN_DIR.mkdir(parents=True, exist_ok=True)
FROZEN_POLICY_FILE = FROZEN_DIR / "initial_policy_2026-10-22.json"
CREATE_INITIAL_FREEZE = False
source_files_to_fingerprint = {
    "YahooRawCSV": RAW_DIR / "yahoo_market_data_raw.csv",
    "FrenchRawText": RAW_DIR / "F-F_Research_Data_Factors_raw.txt",
    "EligibilityEvidence": RAW_DIR / "security_eligibility_2022.csv",
}
for source_name, source_path in source_files_to_fingerprint.items():
    if not source_path.exists():
        raise FileNotFoundError(f"Cannot freeze without {source_name}: {source_path}")

current_snapshot = {
    "SubmissionDate": "2026-10-22",
    "AnalysisSource": Path(__file__).name,
    "HistoricalDecisionDate": DECISION_DATE.date().isoformat(),
    "HistoricalInformationCutoff": ESTIMATION_END,
    "EstimationCommonMonths": len(common_dates),
    "Benchmark": BENCHMARK,
    "CandidateTickers": list(CANDIDATE_TICKERS),
    "SelectedStrategy": INITIAL_GROWTH_STRATEGY,
    "RejectedStrategy": CREDIBLE_REJECTED_ALTERNATIVE,
    "RiskModel": "Single-index covariance",
    "InitialCapitalUSD": float(INITIAL_CAPITAL),
    "RealTarget2030USD": float(REAL_TARGET_2030),
    "NominalTarget2030USD": float(NOMINAL_TARGET_2030),
    "GrowthInvestedNotionalUSD": float(GROWTH_INVESTED_NOTIONAL),
    "GrowthWeights": {
        ticker: float(weight)
        for ticker, weight in zip(CANDIDATE_TICKERS, initial_growth_weights)
    },
    "FullDollarAllocation": [
        {
            "Sleeve": str(row.Sleeve),
            "SecurityOrUse": str(row.SecurityOrUse),
            "DollarAllocation": float(row.DollarAllocation),
        }
        for row in Table_P10_Full_Allocation.itertuples(index=False)
    ],
    "Assumptions": {
        "Inflation": float(BASE_INFLATION),
        "RiskAversionA": float(BASE_RISK_AVERSION),
        "StockCap": float(MAX_STOCK_WEIGHT),
        "ETFCap": float(MAX_ETF_WEIGHT),
        "OneWayTradingCost": float(BASE_TRADING_COST),
        "ParallelRateShock": float(PARALLEL_SHOCK),
        "CurveShapeShock": float(CURVE_SHAPE_SHOCK),
    },
    "MandatoryPaymentsUSD": {str(year): float(amount) for year, amount in LIABILITIES.items()},
    "EvaluationWindow": [EVALUATION_START, EVALUATION_END],
    "EvaluationRule": "Annual 31-Dec rebalance to fixed 2022 target weights; no re-optimization",
    "SourceSHA256": {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in source_files_to_fingerprint.items()
    },
}

if CREATE_INITIAL_FREEZE:
    FROZEN_POLICY_FILE.write_text(
        json.dumps(current_snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    freeze_status = "REBUILT FROM REQUIREMENT-MATCHED ANALYSIS"
elif not FROZEN_POLICY_FILE.exists():
    raise FileNotFoundError(f"Missing frozen policy snapshot: {FROZEN_POLICY_FILE}")
else:
    frozen_snapshot = json.loads(FROZEN_POLICY_FILE.read_text(encoding="utf-8"))
    for field in [
        "SubmissionDate", "HistoricalDecisionDate", "HistoricalInformationCutoff",
        "Benchmark", "CandidateTickers", "SelectedStrategy", "RejectedStrategy",
        "RiskModel", "RealTarget2030USD", "NominalTarget2030USD",
        "MandatoryPaymentsUSD", "EvaluationWindow", "EvaluationRule",
        "Assumptions", "SourceSHA256",
    ]:
        if frozen_snapshot[field] != current_snapshot[field]:
            raise RuntimeError(f"FROZEN POLICY MISMATCH in {field}.")
    for ticker in CANDIDATE_TICKERS:
        if not np.isclose(
            frozen_snapshot["GrowthWeights"][ticker],
            current_snapshot["GrowthWeights"][ticker],
            atol=1e-7,
            rtol=0,
        ):
            raise RuntimeError(f"Frozen growth weight changed for {ticker}.")
    for old, new in zip(
        frozen_snapshot["FullDollarAllocation"],
        current_snapshot["FullDollarAllocation"],
    ):
        if (old["Sleeve"], old["SecurityOrUse"]) != (new["Sleeve"], new["SecurityOrUse"]):
            raise RuntimeError("Frozen allocation holding order/identity changed.")
        if not np.isclose(old["DollarAllocation"], new["DollarAllocation"], atol=0.10, rtol=0):
            raise RuntimeError(f"Frozen dollar allocation changed for {old['SecurityOrUse']}.")
    if not np.isclose(
        frozen_snapshot["GrowthInvestedNotionalUSD"],
        current_snapshot["GrowthInvestedNotionalUSD"],
        atol=0.01,
        rtol=0,
    ):
        raise RuntimeError("Frozen growth-notional amount changed.")
    freeze_status = "VERIFIED: requirement-matched analysis and raw files unchanged"

Table_I3_Freeze_Audit = pd.DataFrame([{
    "Status": freeze_status,
    "SnapshotFile": str(FROZEN_POLICY_FILE.relative_to(PROJECT_ROOT)),
    "AnalysisSource": current_snapshot["AnalysisSource"],
    "SelectedStrategy": INITIAL_GROWTH_STRATEGY,
    "NumberOfTickers": len(CANDIDATE_TICKERS),
    "BaseInflation": BASE_INFLATION,
    "NominalTarget2030USD": NOMINAL_TARGET_2030,
    "InputFilesFingerprinted": ", ".join(source_files_to_fingerprint),
}])

display(Table_P11_Risk_Tolerance)
display(Table_P12_Implementation_Policy)
display(Table_I1_Initial_Decision_Record)
display(Table_I3_Freeze_Audit)

# %%
# ============================================================
# 04I. MATERIAL OUTPUTS ONLY — EXPORT FOR MEMO / SLIDES
# ============================================================

material_outputs = {
    "Table_A1_Mandate_Assumptions": Table_A1_Mandate_Assumptions,
    "Table_B2_Bond_Analytics": Table_B2_Bond_Analytics,
    "Table_B3_Duration_Convexity_Check": Table_B3_Duration_Convexity_Check,
    "Table_B4_Funding_Plan": Table_B4_Funding_Plan,
    "Table_B6_Rate_Scenarios": Table_B6_Rate_Scenarios,
    "Table_B7_Liability_Sleeve_Under_Rate_Stress": Table_B7_Liability_Sleeve_Under_Rate_Stress,
    "Table_D1_Candidate_Universe": Table_D1_Candidate_Universe,
    "Table_D2_Eligibility_Evidence": Table_D2_Eligibility_Evidence,
    "Table_D4_Return_Construction": Table_D4_Return_Construction,
    "Table_P2_Expected_Return_Inputs": Table_P2_Expected_Return_Inputs.reset_index(),
    "Table_P3_Constraints": Table_P3_Constraints,
    "Table_P4_Risk_Model_Comparison": Table_P4_Risk_Model_Comparison,
    "Table_P6_Risk_Aversion_Sensitivity": Table_P6_Risk_Aversion_Sensitivity,
    "Table_P7_Expected_Return_Sensitivity": Table_P7_Expected_Return_Sensitivity,
    "Table_P8_Decision_Candidates": Table_P8_Decision_Candidates,
    "Table_P9_Strategy_Weights": Table_P9_Strategy_Weights,
    "Table_P10_Full_Allocation": Table_P10_Full_Allocation,
    "Table_P11_Risk_Tolerance": Table_P11_Risk_Tolerance,
    "Table_P12_Implementation_Policy": Table_P12_Implementation_Policy,
    "Table_I1_Initial_Decision_Record": Table_I1_Initial_Decision_Record,
    "Table_P9b_Initial_Decision_Record": Table_P9b_Initial_Decision_Record,
    "Table_I3_Freeze_Audit": Table_I3_Freeze_Audit,
}

for name, table in material_outputs.items():
    table.to_csv(TABLE_DIR / f"{name}.csv", index=False)

# Matrices are saved for reproducibility but are not displayed as decision evidence.
SAMPLE_COV.to_csv(TABLE_DIR / "Matrix_Sample_Covariance.csv")
SINGLE_INDEX_COV.to_csv(TABLE_DIR / "Matrix_Single_Index_Covariance.csv")

print("Sections 01–04 requirement-matched outputs exported.")
print(f"Recommended initial growth strategy: {INITIAL_GROWTH_STRATEGY}")
print(f"Credible rejected alternative: {CREDIBLE_REJECTED_ALTERNATIVE}")
