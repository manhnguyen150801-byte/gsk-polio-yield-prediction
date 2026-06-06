# GSK × IÉSEG Hackathon — AI Yield Prediction for Polio Vaccine Purification

**Title:** New AI methodologies to analyze the production process and improve yield   
**Partner:** GSK Vaccines

---

## Problem Statement

Only ~34% of harvested antigen from the polio vaccine (IPV) purification process reaches final product. Yield varies by several percentage points between batches, and each 1% improvement translates to roughly 16,000 additional doses. This project applies AI and data analytics to move from reactive monitoring to predictive modeling of batch yield across the full purification pipeline.

---

## Purification Stages

```
Clarification → Ultrafiltration (UF) → Gel Filtration (PG) → Ion Exchange (DEAE) → PSV → DPV
```

**Target variable:** `GY_011 PSV - Global Yield total [%]` — the percentage of antigen that reaches the PSV stage across the full pipeline.

---

## Repository Structure

```
gsk_github/
├── notebooks/
│   ├── 01_processing/          ← Time-series merging: sensor + events → basetable v5
│   ├── 02_feature_selection/   ← Pearson + AUC feature selection (local and global)
│   ├── 03_visualization/       ← Descriptive analysis and PCA visualization
│   └── 04_modeling/            ← Stage-by-stage regression models (OLS, RF, HGB)
│
├── dashboard/
│   ├── app_final_yield.py      ← Streamlit prediction app (run with: streamlit run dashboard/app_final_yield.py)
│   ├── test_app.py
│   └── assets/                 ← Logos and static chart images
│
├── data/
│   └── basetable/              ← Merged + imputed + PCA-reduced basetables (Parquet)
│       ├── ip1_basetable_v5.parquet   (88 batches × 864 features)
│       ├── ip2_basetable_v5.parquet   (30 batches × 845 features)
│       └── ip3_basetable_v5.parquet   (87 batches × 861 features)
│
├── models/                     ← Trained stage models per serotype (.pkl)
│
├── outputs/
│   ├── descriptive_analysis/   ← EDA charts (yield distributions, scatter, PCA)
│   └── feature_selection/      ← Pearson score CSVs + per-stage feature ranking charts
│
└── docs/
    ├── Time_Series_Merging_v5_Documentation.md   ← Full pipeline documentation
    ├── GSK_QA_RULES.md                           ← Data quality rules
    ├── PROCESS_CONTEXT.md                        ← Process domain context
    ├── IP1_Dictionary_Final.xlsx                 ← Feature dictionary for Serotype 1
    ├── IP3_Dictionary_Final.xlsx                 ← Feature dictionary for Serotype 3
    ├── Implementation_Guide.xlsx                 ← How to use this repository
    └── Hackathon-Slides_2026.pdf                 ← Final presentation slides
```

---

## Methodology

### 1. Data Sources
- **SAP ZQM105** (3 files: IP1, IP2, IP3) — process parameters and QC measurements for 207 batches across 6 purification stages
- **XTO Sensor data** — ~44 million chromatography sensor readings (10-second frequency) from 7 controller units
- **Events logs** — 7 files recording process step timestamps (start/end per batch per sub-step)

### 2. Basetable Construction (v5 Pipeline)
The basetable creation pipeline is fully documented in `docs/Time_Series_Merging_v5_Documentation.md`. Key steps:

| Step | Output |
|------|--------|
| Events cleaning + duration features | 25 phase-level duration features per batch |
| Child sub-event duration pivoting | 349 sub-step duration features |
| Sub-event time window extraction | 82 qualifying sub-step types (45 PG + 37 DEAE) |
| Full-run sensor aggregation (DuckDB range join) | 264 full-run + 264 elution sensor features |
| Sub-event sensor extraction | 7,216 sub-event sensor features |
| Merge all feature blocks | 206 batches × 8,121 columns |
| SAP join + type-aware imputation | Per-serotype basetables |
| PCA reduction of sub-event sensor block | PG: 3,432 cols → 5 PCs (77.5% var); DEAE: 2,376 cols → 5 PCs (63.0% var) |
| **Final basetables** | IP1: 88×864, IP2: 30×845, IP3: 87×861 |

### 3. Feature Selection
Pearson correlation + AUC-based selection applied per stage (local target) and globally (PSV Global Yield target). Top cross-serotype signals:
- **PSV Ag total** (r ≈ 0.55–0.60) — strongest single predictor
- **Clarification Purification Factor** (r ≈ 0.48–0.55) — earliest upstream signal
- **PG Ag content ELISA** (r ≈ 0.32–0.39) — gel filtration quality
- **DEAE sensor signals** (UV Elution, PIC_I1, Accumulated Volume)

### 4. Modeling
Stage-by-stage regression for each serotype (IP1, IP3). Three model families evaluated:

| Model | Notes |
|-------|-------|
| Linear Regression (OLS) | Baseline |
| Random Forest | Non-linear, handles mixed features |
| Histogram Gradient Boosting (HGB) | Best overall performance |

**Evaluation:** NRMSE (primary), RMSE, R² on chronological 80/20 hold-out split (no random shuffle).

**Best results (Global Yield — HGB):**
- IP1: NRMSE = 0.042, RMSE = 1.49%, R² = 0.778
- IP3: NRMSE = 0.042, RMSE = 1.40%, R² = 0.664

---

## How to Run

### Setup

```bash
pip install -r requirements.txt
```

### Streamlit Dashboard

```bash
streamlit run dashboard/app_final_yield.py
```

The dashboard provides:
- **What-if simulation:** Select a batch, edit process feature values, predict yield
- **Model comparison:** NRMSE / RMSE / R² across all stages and models
- **Stage coverage:** Clarification, UF, PG, PSV, and Global Yield for IP1 and IP3

### Notebooks

Run in order:
1. `notebooks/01_processing/Time_Series_Merging.ipynb` — builds the v5 basetables
2. `notebooks/02_feature_selection/` — Pearson + AUC feature selection
3. `notebooks/03_visualization/` — EDA and PCA plots
4. `notebooks/04_modeling/Modeling.ipynb` — trains and evaluates all models

> **Note:** The raw sensor data (~44M rows) is not included in this repository due to file size. The processed basetables in `data/basetable/` are sufficient to run the feature selection, modeling, and dashboard notebooks directly.

---

## Requirements

See `requirements.txt`. Core dependencies:
- `pandas`, `numpy`, `scikit-learn`, `xgboost`
- `streamlit` (dashboard)
- `joblib` (model serialization)
- `duckdb` (sensor range joins in processing notebook)
- `pyarrow` (Parquet I/O)
- `matplotlib`, `seaborn`, `plotly` (visualization)
