"""Generate the formal two-page 22 October initial decision record."""

import csv
import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FROZEN_FILE = PROJECT_ROOT / "data" / "frozen" / "initial_policy_2026-10-22.json"
OUTPUT_FILE = PROJECT_ROOT / "outputs" / "Initial_Decision_Record_Formal_22Oct2026.pdf"

NAVY = "#18324B"
INK = "#243746"
MUTED = "#586B79"
RULE = "#CBD5DC"
PALE = "#F1F5F7"
WHITE = "#FFFFFF"


def read_csv(name):
    path = TABLE_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Required notebook output is missing: {path}")
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


if not FROZEN_FILE.is_file():
    raise FileNotFoundError(f"Frozen notebook policy is missing: {FROZEN_FILE}")

with FROZEN_FILE.open(encoding="utf-8") as source:
    policy = json.load(source)

allocations = read_csv("Table_P10_Full_Allocation.csv")
strategies = read_csv("Table_P8_Decision_Candidates.csv")
risk_sensitivity = read_csv("Table_P6_Risk_Aversion_Sensitivity.csv")
universe = read_csv("Table_D1_Candidate_Universe.csv")
funding_plan = read_csv("Table_B4_Funding_Plan.csv")

if policy.get("AnalysisSource") != "notebooks/BFIN.ipynb":
    raise ValueError("Frozen policy does not identify the current notebook as its source.")
if not allocations or not strategies or not risk_sensitivity or not universe or not funding_plan:
    raise ValueError("A required decision table is empty.")

initial_capital = float(policy["InitialCapitalUSD"])
inflation = float(policy["Assumptions"]["Inflation"])
real_target = float(policy["RealTarget2030USD"])
nominal_target = float(policy["NominalTarget2030USD"])
calculated_target = real_target * (1 + inflation) ** 8
if abs(calculated_target - nominal_target) > 0.01:
    raise ValueError("Frozen nominal target does not reconcile to real target and inflation.")

allocation_total = sum(float(row["DollarAllocation"]) for row in allocations)
if abs(allocation_total - initial_capital) > 0.01:
    raise ValueError("Full allocation does not reconcile to the initial capital.")

recommended = next(
    row for row in strategies if row["Strategy"] == policy["SelectedStrategy"]
)
rejected = next(
    row for row in strategies if row["Strategy"] == policy["RejectedStrategy"]
)
stocks = [row for row in universe if row["SecurityType"] == "Common stock"]
etfs = [row for row in universe if row["SecurityType"] == "ETF"]
if len(stocks) != 10 or len(etfs) != 2:
    raise ValueError("The candidate universe does not match the stated 10-stock, 2-ETF mandate.")

risk_rows = sorted(
    (
        row for row in risk_sensitivity
        if row["RiskModel"] == policy["RiskModel"]
    ),
    key=lambda row: int(row["RiskAversionA"]),
)
if [int(row["RiskAversionA"]) for row in risk_rows] != [2, 4, 6, 8]:
    raise ValueError("The required risk-aversion comparison is incomplete.")

liability_allocations = {
    row["Sleeve"]: row for row in allocations
    if row["Sleeve"] in {"2024 liability", "2027 liability"}
}
if set(liability_allocations) != {"2024 liability", "2027 liability"}:
    raise ValueError("The initial allocation must include both liability reserves.")

output_path = OUTPUT_FILE
output_path.parent.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.5,
    "pdf.fonttype": 42,
    "text.color": INK,
})


def new_page(title, subtitle, page_number):
    fig = plt.figure(figsize=(8.27, 11.69), facecolor=WHITE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 8.27)
    ax.set_ylim(0, 11.69)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 10.84), 8.27, 0.85, color=NAVY, linewidth=0))
    ax.text(0.58, 11.34, title, fontsize=15, fontweight="bold", color=WHITE, va="center")
    ax.text(0.59, 11.04, subtitle, fontsize=8.2, color="#E4EBF0", va="center")
    ax.plot([0.58, 7.69], [0.53, 0.53], color=RULE, linewidth=0.65)
    ax.text(0.59, 0.34, "KAPPA FOUNDATION  |  INITIAL POLICY  |  22 OCTOBER 2026",
            fontsize=7, color=MUTED, va="center")
    ax.text(7.68, 0.34, f"{page_number} / 2", fontsize=7, color=MUTED,
            ha="right", va="center")
    return fig, ax


def section_heading(ax, title, x, y, width=7.1):
    ax.text(x, y, title.upper(), fontsize=8.2, fontweight="bold",
            color=NAVY, va="center")
    ax.plot([x, x + width], [y - 0.12, y - 0.12], color=RULE, linewidth=0.65)


def paragraph(ax, text, x, y, width_chars=112, fontsize=8.1, line_height=0.16):
    lines = textwrap.wrap(text, width=width_chars, break_long_words=False)
    ax.text(x, y, "\n".join(f"{line} " for line in lines), fontsize=fontsize,
            color=INK, va="top", linespacing=1.2)
    return y - len(lines) * line_height


def draw_styled_table(ax, cell_text, col_labels, bbox, col_widths=None,
                      font_size=7.6, highlight_rows=()):
    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        colWidths=col_widths,
        cellLoc="left",
        colLoc="left",
        bbox=bbox,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    for (row_index, _), cell in table.get_celld().items():
        cell.set_edgecolor(RULE)
        cell.set_linewidth(0.45)
        cell.PAD = 0.06
        if row_index == 0:
            cell.set_facecolor(NAVY)
            cell.get_text().set_color(WHITE)
            cell.get_text().set_fontweight("bold")
        elif row_index in highlight_rows:
            cell.set_facecolor("#E7EEF2")
            cell.get_text().set_fontweight("bold")
        elif row_index % 2 == 0:
            cell.set_facecolor(PALE)
    return table


with PdfPages(
    output_path,
    metadata={
        "Title": "Kappa Foundation Initial Decision Record",
        "Subject": "22 October 2026 submission; historical information cutoff 31 December 2022",
        "Author": "Kappa Foundation BFIN Group",
    },
) as pdf:
    fig, ax = new_page(
        "INITIAL DECISION RECORD",
        "Submission deadline: 22 October 2026  |  Historical decision date and information cutoff: 31 December 2022",
        1,
    )

    ax.text(
        0.59, 10.55,
        "DECISION",
        fontsize=8.2, fontweight="bold", color=NAVY, va="center",
    )
    paragraph(
        ax,
        f"Reserve sufficient capital for the irrevocable 2024 and 2027 programme payments, "
        f"then invest the residual growth budget in {policy['SelectedStrategy']} to pursue "
        f"the Foundation's 2030 real-value objective. The policy uses only information "
        f"available through {policy['HistoricalInformationCutoff']}; later observations do "
        f"not revise this initial decision.",
        0.59, 10.34, width_chars=114, fontsize=8.4, line_height=0.17,
    )

    section_heading(ax, "Mandate and liability funding", 0.59, 9.62)
    payment_rows = []
    payment_labels = {
        "2024 liability": ("Scholarship programme", "31 Dec 2024", "USD 2,400,000"),
        "2027 liability": ("Learning centre", "31 Dec 2027", "USD 3,600,000"),
    }
    for sleeve in ("2024 liability", "2027 liability"):
        row = liability_allocations[sleeve]
        label, date, payment = payment_labels[sleeve]
        payment_rows.append([
            label,
            date,
            payment,
            row["SecurityOrUse"],
            f"USD {float(row['DollarAllocation']):,.2f}",
        ])
    payment_ax = fig.add_axes([0.59 / 8.27, 9.18 / 11.69, 7.1 / 8.27, 0.78 / 11.69])
    payment_ax.axis("off")
    draw_styled_table(
        payment_ax,
        payment_rows,
        ["Commitment", "Due date", "Payment", "Funding asset", "Initial cost"],
        [0, 0, 1, 1],
        col_widths=[0.28, 0.19, 0.18, 0.14, 0.21],
        font_size=7.7,
    )
    paragraph(
        ax,
        f"Beta is a two-year zero-coupon maturity match. Delta is a five-year coupon bond; "
        f"interim coupons are ring-fenced and assumed to earn 0% before the 2027 payment. "
        f"Liability reserve: USD {sum(float(r['DollarAllocation']) for r in liability_allocations.values()):,.2f}. "
        f"Growth budget before trading costs: USD {initial_capital - sum(float(r['DollarAllocation']) for r in liability_allocations.values()):,.2f}.",
        0.59, 8.58, width_chars=114, fontsize=7.8, line_height=0.15,
    )

    section_heading(ax, "Information set and candidate universe", 0.59, 8.02)
    stock_tickers = ", ".join(row["Ticker"] for row in stocks)
    etf_descriptions = "; ".join(
        f"{row['Ticker']} ({row['SectorOrMandate']})" for row in etfs
    )
    paragraph(
        ax,
        f"Estimation window: January 2015-December 2022; after alignment, "
        f"{policy['EstimationCommonMonths']} common monthly observations from February 2015 "
        "through December 2022. Candidate universe: "
        f"10 U.S. common stocks across {len({row['SectorOrMandate'] for row in stocks})} sectors "
        f"({stock_tickers}) and two U.S. equity ETFs ({etf_descriptions}). "
        f"{policy['Benchmark']} is the simple investable growth benchmark. "
        "Dated source evidence supports decision-date eligibility.",
        0.59, 7.80, width_chars=114, fontsize=7.9, line_height=0.15,
    )

    section_heading(ax, "Growth decision and risk comparison", 0.59, 7.02)
    paragraph(
        ax,
        f"Recommend {policy['SelectedStrategy']} using CAPM-style expected returns, "
        f"single-index covariance, constrained long-only mean-variance utility and "
        f"base risk aversion A={policy['Assumptions']['RiskAversionA']:g}. "
        f"Under a common A=4 evaluation lens, the recommended portfolio has expected return "
        f"{float(recommended['ExpectedReturn_CommonLens']):.2%}, annual volatility "
        f"{float(recommended['Volatility_CommonLens']):.2%} and utility "
        f"{float(recommended['Utility_A4_CommonLens']):.4f}. The credible rejected alternative, "
        f"{policy['RejectedStrategy']}, has utility {float(rejected['Utility_A4_CommonLens']):.4f}. "
        "Expected return is an assumption, not a promised compound return.",
        0.59, 6.80, width_chars=114, fontsize=7.8, line_height=0.145,
    )

    risk_data = [[
        row["RiskAversionA"],
        f"{float(row['ExpectedReturn']):.2%}",
        f"{float(row['Volatility']):.2%}",
        f"{float(row['Utility']):.4f}",
    ] for row in risk_rows]
    risk_ax = fig.add_axes([0.075, 0.436, 0.44, 0.066])
    risk_ax.axis("off")
    risk_ax.text(
        0, 1.12, "Risk-aversion sensitivity: single-index model",
        fontsize=8, fontweight="bold", color=NAVY, transform=risk_ax.transAxes,
    )
    draw_styled_table(
        risk_ax, risk_data, ["A", "Expected return", "Volatility", "Utility"],
        [0, 0, 1, 1], col_widths=[0.16, 0.31, 0.27, 0.26],
        font_size=7.4, highlight_rows=(2,),
    )
    paragraph(
        ax,
        "A=2, 4, 6 and 8 are compared under both covariance models in the risk-sensitivity analysis. "
        "Increasing A changes the risk-return trade-off and optimized weights; A=4 is the "
        "selected base preference, not an inference from the trustee's loss statement.",
        4.42, 5.72, width_chars=53, fontsize=7.6, line_height=0.14,
    )

    section_heading(ax, "Material assumptions and governance", 0.59, 4.88)
    assumptions = [
        f"2030 objective: USD {real_target:,.0f} in December-2022 dollars; baseline inflation {inflation:.2%} annually; nominal target USD {nominal_target:,.2f} = real target x (1 + inflation)^8. This is a planning target, not a guarantee.",
        f"Growth sleeve: long-only and fully invested; common-stock cap {policy['Assumptions']['StockCap']:.0%}; ETF cap {policy['Assumptions']['ETFCap']:.0%}; borrowing, short selling and derivatives prohibited. Initial one-way equity trading cost {policy['Assumptions']['OneWayTradingCost']:.2%}.",
        "The trustee's concern about losses approaching 15% specifies no horizon or metric; it is treated as a diagnostic rather than a hard optimization constraint.",
        f"Evaluation: January 2023-December 2025, comparing the frozen growth strategy with {policy['Benchmark']} as the growth benchmark. Rebalance annually on 31 December after any scheduled liability payment, back to original 2022 growth target weights; do not re-estimate or re-optimize with evaluation-period data.",
    ]
    y = 4.65
    for assumption in assumptions:
        y = paragraph(ax, assumption, 0.59, y, width_chars=114, fontsize=7.55, line_height=0.145) - 0.06

    pdf.savefig(fig)
    plt.close(fig)

    fig, ax = new_page(
        "INITIAL CAPITAL ALLOCATION",
        "Frozen 2022 policy  |  Dollar amounts from the full-allocation schedule",
        2,
    )
    ax.text(
        0.59, 10.47,
        f"Initial capital: USD {initial_capital:,.0f}     |     "
        f"Liability reserve: USD {sum(float(r['DollarAllocation']) for r in liability_allocations.values()):,.2f}     |     "
        f"Growth purchases: USD {float(policy['GrowthInvestedNotionalUSD']):,.2f}",
        fontsize=8.4, color=INK, va="center",
    )
    ax.plot([0.59, 7.68], [10.25, 10.25], color=RULE, linewidth=0.8)

    allocation_rows = []
    for row in allocations:
        amount = float(row["DollarAllocation"])
        sleeve_weight = (
            amount / float(policy["GrowthInvestedNotionalUSD"])
            if row["Sleeve"] == "Growth" else None
        )
        purpose = {
            "2024 liability": "Fund 2024 scholarship payment",
            "2027 liability": "Fund 2027 learning-centre payment",
            "Growth": "Pursue 2030 real-value objective",
            "Implementation": "Initial growth-purchase cost",
        }[row["Sleeve"]]
        allocation_rows.append([
            row["Sleeve"],
            row["SecurityOrUse"],
            f"{amount:,.2f}",
            f"{float(row['PercentOfInitialFund']):.2%}",
            f"{sleeve_weight:.2%}" if sleeve_weight is not None else "-",
            purpose,
        ])
    allocation_rows.append([
        "TOTAL", "All uses", f"{allocation_total:,.2f}", "100.00%", "-",
        "Reconciles to initial capital",
    ])

    allocation_ax = fig.add_axes([0.075, 0.265, 0.85, 0.62])
    allocation_ax.axis("off")
    draw_styled_table(
        allocation_ax,
        allocation_rows,
        ["Sleeve", "Security / use", "USD", "% of fund", "% growth sleeve", "Purpose"],
        [0, 0, 1, 1],
        col_widths=[0.15, 0.16, 0.18, 0.13, 0.15, 0.23],
        font_size=7.5,
        highlight_rows=(len(allocation_rows),),
    )
    allocation_ax.text(
        0, 1.03,
        "Growth weights are shown as a share of growth capital invested; fund weights include reserves and trading cost.",
        fontsize=7.5, color=MUTED, transform=allocation_ax.transAxes,
    )

    ax.text(0.59, 2.48, "ALLOCATION NOTES", fontsize=8.2, fontweight="bold", color=NAVY, va="center")
    ax.plot([0.59, 7.68], [2.34, 2.34], color=RULE, linewidth=0.65)
    paragraph(
        ax,
        f"The liability assets are set aside before allocating the growth sleeve. Interim Delta coupons are ring-fenced under the base 0% reinvestment assumption. The listed equity and ETF purchases sum to USD {float(policy['GrowthInvestedNotionalUSD']):,.2f}; the separate initial trading-cost allowance is USD {float(next(row['DollarAllocation'] for row in allocations if row['Sleeve'] == 'Implementation')):,.2f}.",
        0.59, 2.12, width_chars=114, fontsize=7.8, line_height=0.15,
    )
    paragraph(
        ax,
        "This record states the initial decision and its predeclared evaluation rule. Any later trustee mandate or policy revision must be documented separately and compared with this frozen baseline.",
        0.59, 1.42, width_chars=114, fontsize=7.8, line_height=0.15,
    )
    pdf.savefig(fig)
    plt.close(fig)

print(f"Formal two-page initial decision record written to {output_path}")
