# BFIN Group Assignment — Kappa Foundation

## Project purpose
This repository contains the reproducible analysis for the Kappa Foundation group assignment.

Current completed scope:
- Section 01 — Mandate, assumptions and real-value objective
- Section 02 — Bond valuation and liability funding
- Section 03 — Market data, universe and reproducibility
- Section 04 — Portfolio construction and robustness

Planned next sections:
- Section 05 — Market and factor models
- Section 06 — Frozen 2023–2025 evaluation and evidence against the recommendation
- Section 07 — Final recommendation, monitoring and response to the revised mandate

## Project structure

```text
BFIN-Group-Assignment/
├── README.md
├── requirements.txt
├── .gitignore
│
├── notebooks/
│   └── Assignment_Upgraded_Sections_1_4_V2.ipynb
│
├── src/
│   ├── 01_download_market_data.py
│   └── 02_download_french_factors.py
│
├── data/
│   ├── raw/
│   └── processed/
│
└── outputs/
    ├── tables/
    └── figures/
```

## Environment setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install required packages:

```bash
pip install -r requirements.txt
```

## Data retrieval

Run the Yahoo Finance retrieval script:

```bash
python src/01_download_market_data.py
```

Run the Kenneth French factor retrieval script:

```bash
python src/02_download_french_factors.py
```

These scripts save raw source files and source records under:

```text
data/raw/
```

Processed analysis-ready files are stored under:

```text
data/processed/
```

## Running the analysis

Open:

```text
notebooks/Assignment_Upgraded_Sections_1_4_V2.ipynb
```

Select the project `.venv` kernel in VS Code / Jupyter.

Then use:

```text
Restart Kernel → Run All
```

The notebook is designed to rebuild Sections 01–04 from the saved project data without manual edits.

## Information cutoff

The case decision date is 31 December 2022.

Decision-stage estimation uses information no later than 31 December 2022.

The period January 2023 to December 2025 is reserved for frozen out-of-sample evaluation and must not be used to revise the original 31 December 2022 decision.

## Initial frozen policy

The initial policy is frozen for the 22 October 2026 decision record.

Current policy framework:
- mandatory liabilities funded first;
- growth allocation based on the Section 04 initial decision;
- SPY used as the growth benchmark;
- annual rebalancing back to frozen target weights;
- no borrowing;
- no short selling;
- no derivatives.

Any later recommendation change must be recorded separately rather than overwriting the initial policy.

## Collaboration workflow

Before starting work:

```bash
git pull
```

Create a branch for substantial work:

```bash
git checkout -b section5-factor-model
```

After changes:

```bash
git add .
git commit -m "Add Section 5 factor model analysis"
git push -u origin section5-factor-model
```

Open a Pull Request on GitHub for review before merging into `main`.

## Notebook collaboration warning

Jupyter notebooks can create difficult merge conflicts if multiple people edit the same notebook simultaneously.

Recommended approach:
- assign ownership of sections;
- avoid editing the same notebook cells at the same time;
- use separate branches;
- review Pull Requests before merging.

## Reproducibility

The final submission should retain:
- raw downloads;
- processed datasets;
- generated tables and figures;
- source records;
- executed notebook/scripts;
- `requirements.txt`;
- rebuild instructions;
- initial decision record and later decision log.

Do not manually edit raw downloaded files.

## Academic integrity

Any material AI assistance should be disclosed in accordance with the course policy.

Every team member should be able to explain the analysis submitted under their name.
