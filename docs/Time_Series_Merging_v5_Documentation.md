# Time Series Merging v4 — Process Documentation

**Notebook:** `Time_Series_Merging_v4.ipynb`  
**Author:** Duc Manh  
**Date:** 2026-05-21  
**Runtime:** ~3–4 hours (two DuckDB sensor passes over 44M rows each)

---

## 1. What This Notebook Does

Links 7 XTO chromatography sensor files (~44M rows total) to their corresponding production
batches using event time windows, then aggregates the sensor readings into one statistical
feature row per batch. v4 extends v3 in two major ways: it adds **sub-event sensor feature
extraction** using Child 2 phase-level time windows (30-minute+ sub-steps within each
chromatography run), and it applies **type-aware imputation** before producing the final
basetables. The output is three ready-to-use merged basetables (SAP + sensor, already
imputed) for IP1, IP2, and IP3 — teammates do not need a separate merge or imputation step
before modeling.

---

## 2. Data Sources Used

| Source | Files | Description |
|--------|-------|-------------|
| SAP cleaned | `ip1_...cleanedApr28.csv`, `ip2_...`, `ip3_...` | 207 valid batch IDs across IP1/IP2/IP3 |
| Events Excel | 7 `.xlsx` files | Process step time windows with BatchID, Start/End timestamps |
| Sensor TXT | 7 `IPV_IESG_XTOxxxxx_*.txt` files | 10-second readings per XTO chromatography machine |

> **UF-events_TRAITEMENT.xlsx is excluded.** The UF events file has no XTO references
> in its `Primary element` column and cannot be used to link sensor data to batches.
> UF duration features are therefore absent; UF-stage features come from SAP directly.

---

## 3. Pipeline Steps

### Cells 1–2 — Setup

Cell 1 installs DuckDB via `subprocess` and imports all libraries (`pandas`, `numpy`,
`tqdm`, `duckdb`, `pathlib`, `re`, `gc`). Cell 2 sets `DEV_MODE = False` (full production
data), configures chunk size (100,000 rows), defines all directory paths, and declares two
key constant lists:

- `PHASE_TO_STAGE` — maps each events file key to its process stage:
  - `pg_up4 → PG`, `deae_up12 → DEAE`
  - `pg_deae_up1`, `pg_deae_up2`, `pg_up3`, `pg_deae_up5`, `pg_up6` → all `PREP`
- `SENSOR_NUMERIC_COLS` — 21 numeric sensor channels aggregated with mean/std/min/max
- `SENSOR_BOOL_COLS` — `['UV Elution']` — used for elution detection only

```
DEV_MODE:           False
CHUNKSIZE:          100000
Sensor numeric cols: 21
Stages mapped:      {'PREP', 'DEAE', 'PG'}
```

---

### Cell 3 — Valid Batch IDs

Loads the three cleaned SAP CSV files and builds `VALID_BATCH_IDS` — the set of 207 batch
IDs present in at least one of IP1/IP2/IP3. All downstream processing is restricted to
these 207 batches; sensor rows belonging to unknown or calibration batches are discarded.

```
IP1 shape: (90, 147)
IP2 shape: (30, 133)
IP3 shape: (87, 144)
Valid SAP batch IDs: 207
```

> **Why filter to 207 batches?** The XTO machines also run CIP (Clean-in-Place) cycles,
> column qualification runs, and test batches. Restricting to VALID_BATCH_IDS ensures
> only real production runs with SAP records are processed, reducing the XTO event map
> from ~1,734 potential entries to 828 confirmed batch-stage windows.

---

### Cell 4 — Events Cleaning

Loads and cleans all 7 Events Excel files (UF excluded). Four cleaning rules are applied
to every file:

1. **Forward-fill BatchID** — blank cells in the source inherit the preceding non-blank
   BatchID (operators enter the ID once at the top of each batch block)
2. **Normalize BatchID** — strips stage suffix to match SAP format: `3_<hash>_DEAE`
   becomes `3_<hash>_` using `str.extract(r'(.*_)')` with fallback for CIP IDs
3. **Convert timestamps** — handles three storage formats: `datetime64` (already parsed
   by pandas), `object` (mixed datetime strings), and `float` (Excel serial dates from
   epoch 1899-12-30)
4. **Compute Duration_hours** — derived as `End time − Start time` in hours, robust to
   any source format

Saves each cleaned table as a parquet file to `cleaned_data/Events/`.

```
XTO_DEAE_events_UP12_batches   53,076 rows   BatchID_nulls=0   timestamps clean
XTO_PG_DEAE_events_UP1         78,786 rows   BatchID_nulls=0   timestamps clean
XTO_PG_DEAE_events_UP2         51,820 rows   BatchID_nulls=0   timestamps clean
XTO_PG_DEAE_events_UP5         90,595 rows   BatchID_nulls=0   timestamps clean
XTO_PG_events_UP3              35,032 rows   BatchID_nulls=0   timestamps clean
XTO_PG_events_UP4_batches      49,773 rows   BatchID_nulls=0   timestamps clean
XTO_PG_events_UP6              16,314 rows   BatchID_nulls=0   timestamps clean
```

**Events hierarchy (Russian dolls):** Each events file has three hierarchy levels. The
`Event name` column identifies the level:

- `Chromatography_UnitProcedure` — top-level row; `Child 1` is NaN; carries the full
  batch time window (e.g., 23 hours for a PG run)
- `Chromatography_Operation` — `Child 1` populated, `Child 2` NaN; sub-step of 1–6 hours
- `Chromatography_Phase` — both `Child 1` and `Child 2` populated; finest granularity,
  down to minutes or seconds

---

### Cell 5 — Events Duration Feature Aggregation (Full-Run)

For each of the 7 event phases, groups by BatchID and computes 5 duration statistics:
`n_events`, `total_duration_h`, `mean_duration_h`, `std_duration_h`, `max_duration_h`.
Columns are prefixed as `ev_{phase}_{metric}`.

```
pg_deae_up1 : 205 batches,  5 features  (UP1 — shared PG/DEAE preparation)
pg_deae_up2 : SKIPPED        (no valid batches after VALID_BATCH_IDS filter — CIP runs)
pg_up3      : SKIPPED        (no valid batches after VALID_BATCH_IDS filter — CIP runs)
pg_up4      : 204 batches,  5 features  (UP4 — actual PG production run)
pg_deae_up5 : 205 batches,  5 features  (UP5 — shared PG/DEAE preparation)
pg_up6      :   9 batches,  5 features  (UP6 — rare preparation step)
deae_up12   : 205 batches,  5 features  (UP12 — actual DEAE production run)

Output: events_features_df — shape (207, 26)
        207 unique batches × 25 duration features + 1 BatchID key
```

---

### Cell 5b — Child 1 / Child 2 Sub-Event Duration Features (NEW in v4)

**What it adds:** Instead of only computing aggregate duration statistics for each full
phase (Cell 5), Cell 5b pivots the individual Child 1 and Child 2 sub-step event names
from the two focus files (`pg_up4` and `deae_up12`) into one column per unique sub-step
type. The value is the duration in hours for that sub-step for that batch; NaN means the
sub-step did not run for that batch.

**80% missing filter:** sub-step types present in fewer than 20% of batches are dropped
to avoid columns that are almost entirely NaN.

```
pg_up4/child1  : 2 columns kept  (1 dropped for >80% missing)
pg_up4/child2  : 162 columns kept  (53 dropped for >80% missing)
deae_up12/child1: 2 columns kept  (1 dropped for >80% missing)
deae_up12/child2: 183 columns kept  (8 dropped for >80% missing)

Output: sub_events_wide — shape (207, 350)
        207 unique batches × 349 sub-event duration cols + 1 BatchID key
```

**Column naming convention:** `{stage}_{level}_{cleaned_event_name}`

Example: `pg_child2_xto_inlet_20x__13_1` = how long `XTO_INLET_20X` instance 13
was active during the PG run for that batch (in hours).

> **Instance numbers are meaningful.** The `__13_1` suffix means "instance 13,
> sub-instance 1" in the XTO protocol. Different instance numbers correspond to
> different process phases with very different durations — for example,
> `xto_inlet_20x__13_1` runs ~1,640 minutes while `xto_inlet_20x__1_1` runs ~0.5
> minutes. These are NOT duplicates. Do not collapse them.

---

### Cell 5c — Child 2 Sub-Event XTO Time Window Map (NEW in v4)

**Purpose:** Builds `child2_xto_map` — the bridge data structure enabling sub-phase
sensor feature extraction in Cell 5d. Unlike Cell 6 (which extracts one full-batch
time window per batch-stage pair), Cell 5c extracts one narrow time window per
(batch, sub-step type) pair.

**Three sequential filters:**

1. **Noise filter:** removes rows whose `Child 2` name contains any of
   `alarm`, `prompt`, `gen_get_val`, `user_request`, `cip`, `init` — these are
   system handshakes and maintenance steps, not process phases
2. **Duration filter:** keeps only sub-steps with median duration ≥ 30 minutes
   (threshold: `CHILD2_MIN_DURATION_H = 30/60`) — removes transient toggles
3. **Coverage filter:** keeps only sub-step types present in ≥ 20% of batches
   (`CHILD2_MIN_BATCH_COVERAGE = 0.20`, i.e., ≥ 42 of 207 batches)

**Last-run-wins:** when a batch had multiple runs of the same sub-step (named
`_PGBIS`, etc.), only the most recent time window is kept using
`groupby(['BatchID', '_step_key']).last()` after sorting by `Start time`.

**Applied per focus phase:**

```
pg_up4:   41,194 rows → 32,182 after noise filter (9,012 removed)
          32,182 → 8,613 after duration filter (>=30 min)
          8,613 → 45 sub-step types survive coverage filter (each in >=42 batches)

deae_up12: 45,114 rows → 35,906 after noise filter (9,208 removed)
           35,906 → 6,723 after duration filter (>=30 min)
           6,723 → 37 sub-step types survive coverage filter (each in >=42 batches)
```

**Surviving sub-step types (PG — 45 types):**

```
xto_common_20x:  __3_1, __28_1–__44_1 (12 instances)
xto_control_20x: __1_1, __4_1, __7_1, __14_1–__30_1 (14 instances)
xto_inlet_20x:   __1_1, __4_1–__13_1 (6 instances)
xto_inline_201:  __1_1, __7_1–__16_1 (6 instances)
xto_outlet_20x:  __1_1, __5_1–__18_1 (7 instances)
```

**Surviving sub-step types (DEAE — 37 types):**

```
xto_common_20x:  __22_1, __29_1, __34_1–__57_1 (8 instances)
xto_control_20x: __4_1, __7_1, __15_1–__31_1 (8 instances)
xto_inlet_20x:   __5_1, __6_1, __12_1–__18_1 (7 instances)
xto_inline_201:  __7_1, __8_1, __16_1–__28_1 (5 instances)
xto_outlet_20x:  __8_1–__24_1 (9 instances)
```

**child2_xto_map output:**

```
shape: (14,897, 6)   — one row per (batch, sub-step, XTO machine)
Unique sub-step types: 66   (45 PG + 37 DEAE; some overlap in step names)
Unique BatchIDs:       207
Batch coverage per step: 45–205 batches (all above the 42-batch threshold)
```

> **IMPORTANT — instance numbers must not be collapsed.** `xto_inlet_20x__13_1` and
> `xto_inlet_20x__1_1` are different process phases. The `__13_1` number is an
> instance counter in the XTO UNICORN chromatography control protocol. Do not strip
> or normalize these suffixes. The exact interpretation of each instance number
> requires the XTO controller protocol from GSK.

---

### Cell 5d — Sub-Event Sensor Feature Extraction (NEW in v4)

Runs a **second DuckDB sensor pass**, scoped to `child2_xto_map` time windows instead
of the full-batch windows from Cell 6. This produces sensor features that capture
conditions during specific sub-phases only.

**Key design decision — in-loop filtering to avoid MemoryError:** For each sensor file,
the pipeline determines the time range covered by the relevant `child2_xto_map` windows
before reading the file. Only rows within that time range are kept in memory; the DuckDB
range join is then applied to this filtered subset. This prevents the ~13M-row files from
being held in RAM simultaneously.

**Per file processing:**

1. Read 3 rows to identify the XTO ID (`_xto` column)
2. Look up the XTO ID in `child2_xto_map`; skip the file if no matching sub-step windows exist
3. Determine the global time range from `child2_xto_map` for that XTO
4. Read the full file in 100,000-row chunks, keeping only rows within that time range
5. DuckDB range join: match each sensor row to a (batch, sub_step) pair
6. Aggregate matched rows: mean, std, min, max per (batch, sub_step, sensor_channel)

**Actual rows processed (Cell 5d — sub-event pass):**

```
XTO53101:  13,047,405 loaded →  3,835,104 kept (29.4%)  → 3,542,403 matched
XTO53103:  35,732,978 loaded →    832,033 kept  (2.3%)  → 1,479,026 matched
XTO53104:  13,047,409 loaded → 11,194,811 kept (85.8%)  → 9,143,762 matched
XTO53201:  13,047,411 loaded →    751,095 kept  (5.8%)  → 1,214,824 matched
XTO53202:  13,047,412 loaded → 11,774,536 kept (90.2%)  → 4,565,866 matched
XTO53501:  13,047,414 loaded →  3,818,646 kept (29.3%)  → 1,687,720 matched
XTO53601:  13,047,415 loaded → 11,896,181 kept (91.2%)  → 6,189,951 matched

Total rows processed (child2 pass): 44,102,406
Total rows matched:                  27,823,552
```

**Output:**

```
child2_sensor_wide shape: (206, 7217)
Unique batches:     206
Sub-step groups:    82   (45 PG + 37 DEAE sub-steps × 4 stats × 21 channels + 1 key)
```

**Column naming convention:** `{stage}_sub_{step_key}_sensor_{channel}_{stat}`

Example: `pg_sub_xto_inlet_20x__13_1_sensor_UV Light_mean` = mean UV absorbance
**specifically during** the `XTO_INLET_20X` instance 13 phase of the PG run for that
batch. This is more targeted than `pg_sensor_UV Light_mean` which averages UV across
the entire 25-hour PG run including equilibration and regeneration.

---

### Cell 6 — XTO-to-Batch Event Window Map

Scans all 7 cleaned Events parquets for rows where `Primary element` matches
`^XTO\d+$` (the XTO machine identifier) **and `Child 1` is NaN** (top-level
`Chromatography_UnitProcedure` rows only). This two-part filter is the key v4
improvement over v2/v3.

**Three v4 improvements over v2:**

1. **Top-level filter (new):** only `UnitProcedure` rows (`Child 1 = NaN`) are kept.
   In v2/v3, all XTO rows (including Operation and Phase sub-rows with short durations
   down to 10 seconds) were included, inflating the window count to 139,388 and causing
   match rates above 100%. By keeping only top-level rows, each batch has at most one
   time window per stage.

2. **Last-run-wins:** when a batch had multiple runs on the same equipment (re-runs
   named `_PGBIS`, `_DBAEBIS`, etc.), `groupby(['BatchID', 'phase']).last()` keeps
   only the most recent window after sorting by `Start time`.

3. **DEAE_UP12 preference:** when `DEAE_UP12` and `PG_DEAE_UP1` both cover the same
   batch and overlap in time, the `PG_DEAE_UP1` DEAE-assigned row is removed.

**Output:**

```
After last-run-wins filter:
  Total entries:   828
  Unique BatchIDs: 207

stage
PREP    419
DEAE    205
PG      204

Removed 0 PG_DEAE_UP1 rows that were duplicates of DEAE_UP12 entries

Unique XTO IDs:  7
Total entries:   828
Unique BatchIDs: 207
```

> **Why 828 vs 139,388 in v2?** The top-level filter + `groupby().last()` reduces to
> at most one row per (batch, phase) combination. With 207 batches × ~4 active phases
> per batch ≈ 828 total windows. 139,388 in v2 included Operation and Phase sub-rows
> with their small time windows, causing a sensor row to match multiple windows
> simultaneously (hence v2's 124.7% match rate). The v4 rate of 17.1% means ~1 in 6
> sensor readings fell within a valid batch process window — physically reasonable given
> that the equipment also runs CIP cycles, column qualification, and standby time between
> batches.

---

### Cell 7 — Full-Run Sensor Processing (DuckDB Range Join)

The main sensor processing pass. Processes each of the 7 sensor `.txt` files
sequentially in four phases:

1. **Load** in 100,000-row chunks (memory-safe for ~13M row files)
2. **Pre-filter** sensor rows to the time range of valid batches
3. **DuckDB range join** — matches each sensor row to a (batch, stage) pair:
   ```sql
   ON s.XTO = x.XTO
   AND s._timestamp >= x."Start time"
   AND s._timestamp <= x."End time"
   ```
4. **Aggregate** matched rows to (batch, stage)-level statistics (`mean`, `std`, `min`,
   `max` for numeric channels; elution rows aggregated separately). RAM freed after each file.

**Actual rows processed (Cell 7 — full-run pass):**

```
XTO53101:  13,047,405 loaded →  3,835,188 pre-filtered →    718,656 matched
XTO53103:  35,732,978 loaded →    831,633 pre-filtered →    297,510 matched
XTO53104:  13,047,409 loaded → 11,194,662 pre-filtered →  1,864,863 matched
XTO53201:  13,047,411 loaded →    751,118 pre-filtered →    248,171 matched
XTO53202:  13,047,412 loaded → 11,774,643 pre-filtered →  1,169,596 matched
XTO53501:  13,047,414 loaded →  3,818,739 pre-filtered →    713,366 matched
XTO53601:  13,047,415 loaded → 11,896,266 pre-filtered →  2,524,332 matched

Total rows processed: 44,102,249
Total rows matched:    7,536,494
Match rate:            17.1%
```

> **Why 17.1% is physically correct:** The top-level filter in Cell 6 gives each batch
> exactly one time window per stage. A sensor row can match at most one window. 17.1%
> means roughly 1 in 6 sensor readings fell within a confirmed production batch window —
> the rest were during CIP cycles, column qualification, or equipment standby between
> batches. This is a realistic match rate for continuous chromatography equipment.

---

### Cells 8–9 — Aggregation and Elution Flags

**Cell 8** concatenates all per-file aggregations, re-aggregates by `(batch, stage)`
to handle batches split across multiple sensor files (takes mean), then pivots to one
row per batch with separate column groups for PG, DEAE, and PREP stages.

```
Final sensor_agg shape: (550, 178)
Unique batches: 206
Stages: {DEAE: 205, PREP: 202, PG: 143}

Wide sensor table: (206, 529)
Sample columns: pg_sensor_AI_A1_mean, pg_sensor_AI_A1_std, ...
```

> **Note on 143 PG batches:** 204 batches have UP4 event windows but only 143 have
> matching sensor data. The remaining 61 batches likely ran on a PG controller not
> covered by the 7 sensor files (see Known Limitations). These 61 batches will have
> NaN in `pg_sensor_*` columns, handled by imputation in Cell 13.

**Cell 9** adds two binary flags indicating whether elution sensor data was captured
for each batch. These flags are important because elution was not recorded for every
batch.

```
Batches with PG elution data:   130 / 206
Batches with DEAE elution data: 194 / 206
```

**Why elution is detected separately:** A chromatography run passes through several
sub-phases in sequence: `Equilibration → Loading → Washing → [Elution] → Regeneration`.
The `UV Elution` boolean flag in the sensor data is set to `1` by the UNICORN
chromatography control system precisely when the equipment enters elution mode — the
moment the buffer conditions change to wash the bound product off the column and
collect it.

Averaging UV absorbance across the full 25-hour run would dilute this signal with the
baseline (~0) during equilibration and CIP. The elution flag + elution-period statistics
give the model direct access to the UV peak shape that describes peak separation quality
and product recovery. DEAE is GSK's primary improvement target, and DEAE is a
flow-through process where elution conditions — timing, flow rate, conductivity —
determine how cleanly the virus is collected.

---

### Cell 10 — Merge All Features

Left-joins four feature tables into one wide table on `ev_batch_id`:

1. `sensor_wide` — 529 columns (full-run + elution sensor stats from Cell 8–9)
2. `events_features_df` — 26 columns (phase-level duration features from Cell 5)
3. `sub_events_wide` — 350 columns (Child 2 duration features from Cell 5b)
4. `child2_sensor_wide` — 7,217 columns (Child 2 sub-event sensor features from Cell 5d)

```
Full sensor + events + sub-events + child2 sensor shape: (206, 8121)
Total columns:  8121
Unique batches: 206
```

Column breakdown:
- 529 — full-run sensor (264 sensor stats + 264 elution stats + 1 key)
- 26 — events duration (25 features + 1 BatchID key, merged by join)
- 350 — Child 2 duration (349 features + 1 key, merged by join)
- 7,217 — Child 2 sub-event sensor (7,216 features + 1 key, merged by join)
- 2 — elution flags (`pg_has_elution_data`, `deae_has_elution_data`)

---

### Cells 11–12 — Save and Split

**Cell 11** saves the complete 8,121-column feature table:

```
Saved to: C:\Hackathon-GSK\data\processed\sensor_aggregated_features_v4.parquet
Shape: (206, 8121)
```

**Cell 12** splits `full_sensor_features` into two separate feature sets:

- `sensor_fullrun` (206 × 7,857) — `{stage}_sensor_*` columns + all `ev_cols`
- `sensor_elution` (206 × 7,857) — `{stage}_elution_*` columns + all `ev_cols`

The `ev_cols` category in v4 is significantly larger than in v2:

```
Key column:             1
Full-run sensor cols:   264
Elution sensor cols:    264
Elution flag cols:        2
  Events duration cols (ev_*):   25
  Child 1 duration cols:          4
  Child 2 duration cols:        345
  Child 2 sub-event sensor cols: 7,216
Total ev_cols:          7,590

Full-run feature set shape: (206, 7,857)
Elution feature set shape:  (206, 7,857)

Saved: C:\Hackathon-GSK\data\processed\sensor_features_fullrun_v4.parquet
Saved: C:\Hackathon-GSK\data\processed\sensor_features_elution_v4.parquet
```

---

### Cell 13 — Build Final Basetables (Type-Aware Imputation)

Merges each SAP file (IP1, IP2, IP3) with `sensor_fullrun` using a **type-aware
imputation strategy** — different column groups have different missing-value semantics
and therefore require different treatments.

**Before merging, 2 known problematic IP1 batches are dropped:**
```
IP1: dropped 2 problematic batches → 88 rows remain
```

**Column group classification and imputation strategy:**

#### Type 1/2 — Full-run sensor (`pg_sensor_*`, `deae_sensor_*`, `prep_sensor_*`)

- **Cause of NaN:** 61 batches have PG event windows but no sensor data (processed on an
  unlisted PG controller not in the 7 sensor files). These batches are entirely missing
  all `pg_sensor_*` columns.
- **Treatment:** Column-mean imputation using the **serotype's own mean** (not the global
  mean), plus a binary flag `sensor_data_imputed = 1` for each batch where all full-run
  sensor columns were NaN.
- **Rationale:** Mean imputation preserves the feature distribution and allows the model
  to train on all batches. The flag lets the model learn that imputed batches may behave
  differently.

#### Type 3 — Child 2 sub-event sensor (`*_sub_*_sensor_*`)

- **Cause of NaN:** The specific sub-step did not run for that batch (e.g., a batch that
  used a shortened protocol skipped certain phases).
- **Treatment:** Zero-fill + one binary `{prefix}_ran` flag per sub-step type
  (1 = at least one sensor reading was captured for that sub-step).
- **Rationale:** Zero is semantically correct — if a sub-step did not run, its sensor
  reading was zero (absent). Mean imputation would be wrong because the mean of readings
  during a step that ran is not a valid substitute for a step that never ran.

#### Type 4 — Elution sensor (`*_elution_*`)

- **Cause of NaN:** No UV elution peak was captured for that batch (UV Elution flag never
  reached 1 during the batch window).
- **Treatment:** Zero-fill (no peak = 0 absorbance).

#### Type 5 — Duration/event features (`ev_*`, `_child1_*`, `_child2_*`)

- **Cause of NaN:** The event/sub-step did not occur for that batch.
- **Treatment:** Zero-fill (no event = 0 hours of duration).

**Final basetable dimensions:**

```
IP1: 88 rows, 88 unique BatchIDs, 0 duplicates
IP2: 30 rows, 30 unique BatchIDs, 0 duplicates
IP3: 87 rows, 87 unique BatchIDs, 0 duplicates
```

---

### Cell 13b — PCA Reduction of Child 2 Sub-Event Sensor Features

**Why PCA is needed:** After imputation, each basetable contains ~3,872 `pg_sub_*_sensor_*`
columns and ~2,376 `deae_sub_*_sensor_*` columns — roughly 6,248 sub-event sensor features
for only 88 rows. This extreme high-dimensional regime will cause any standard model to
overfit without very aggressive regularization. PCA compresses each block into 5 orthogonal
components while preserving as much variance as possible.

**Which columns are reduced:**
- `pg_sub_*_sensor_*` — PG-stage Child 2 sub-event sensor stats (mean/std/min/max per sub-step per channel)
- `deae_sub_*_sensor_*` — DEAE-stage Child 2 sub-event sensor stats

**Which columns are NOT reduced (kept as-is):**
- Full-run sensor cols (`pg_sensor_*`, `deae_sensor_*`, `prep_sensor_*`) — individually interpretable
- Elution sensor cols (`*_elution_*`) — physically meaningful signal, interpretable per-channel
- Event duration cols (`ev_*`, `*_child1_*`, `*_child2_*`) — process timing, already low-dimensional
- SAP columns — never modified by the sensor pipeline

**Two separate PCAs — one per stage:** PG and DEAE are physically distinct purification
processes. A single combined PCA would conflate unrelated variance; two separate PCAs keep
the components interpretable within each stage context.

**Fit strategy:** The scaler (`StandardScaler`) and `PCA` are fit on **IP1 only** (the
largest dataset, 88 rows), then the same fitted objects are applied to IP2 and IP3. This
ensures all three basetables share the same PC axes — a requirement for training a single
model across serotypes or comparing PC scores between serotypes.

**Common-column intersection:** Only columns present in all three of IP1/IP2/IP3 are used
to fit the PCA (some sub-step types may be absent from IP2 due to small sample size). Any
missing column in a given basetable is zero-filled before transforming.

**PGA input/output before and after PCA:**

```
PG   sub-event sensor cols in IP1 : 3,872
     common across IP1/IP2/IP3   : 3,432

DEAE sub-event sensor cols in IP1 : 2,376
     common across IP1/IP2/IP3   : 2,376

Shapes before PCA:
  IP1: (88, 7102)
  IP2: (30, 6643)
  IP3: (87, 7099)
```

**PG PCA — explained variance (5 PCs from 3,432 cols):**

```
PC1: 62.7%  (cumulative 62.7%)
PC2:  6.3%  (cumulative 69.0%)
PC3:  3.5%  (cumulative 72.5%)
PC4:  2.8%  (cumulative 75.3%)
PC5:  2.2%  (cumulative 77.5%)

  IP1: 3,872 cols dropped, 5 PCs added → shape (88, 3235)
  IP2: 3,432 cols dropped, 5 PCs added → shape (30, 3216)
  IP3: 3,872 cols dropped, 5 PCs added → shape (87, 3232)
```

**DEAE PCA — explained variance (5 PCs from 2,376 cols):**

```
PC1: 28.3%  (cumulative 28.3%)
PC2: 14.2%  (cumulative 42.5%)
PC3:  9.0%  (cumulative 51.5%)
PC4:  6.3%  (cumulative 57.8%)
PC5:  5.3%  (cumulative 63.0%)

  IP1: 2,376 cols dropped, 5 PCs added → shape (88, 864)
  IP2: 2,376 cols dropped, 5 PCs added → shape (30, 845)
  IP3: 2,376 cols dropped, 5 PCs added → shape (87, 861)
```

**Final shapes after both PCAs:**

```
  IP1: (88, 7102)  →  (88, 864)   (removed 6,238 cols)
  IP2: (30, 6643)  →  (30, 845)   (removed 5,798 cols)
  IP3: (87, 7099)  →  (87, 861)   (removed 6,238 cols)
```

**Output column names:** `pg_sub_pc1` … `pg_sub_pc5` and `deae_sub_pc1` … `deae_sub_pc5`
(10 new columns total per basetable). Generated by `f'{prefix}_pc{k+1}'` where prefix is
`pg_sub` or `deae_sub`.

**Saved PCA model files** (to `OUTPUT_DIR/pca_models/`):

```
  pg_sub_scaler.joblib    — StandardScaler fit on IP1 pg_sub_* sensor cols
  pg_sub_pca.joblib       — PCA(n_components=5) fit on scaled IP1 pg_sub_* sensor cols
  deae_sub_scaler.joblib  — StandardScaler fit on IP1 deae_sub_* sensor cols
  deae_sub_pca.joblib     — PCA(n_components=5) fit on scaled IP1 deae_sub_* sensor cols
```

> **Data leakage note:** PCA is fit on all batches before any train/test split. Acceptable
> for proof-of-concept. The saved `.joblib` files allow new batches to be projected onto the
> same PC axes in the dashboard or at scoring time without re-fitting.

> **DEAE PC1 explains only 28.3%** — much lower than PG PC1 (62.7%). This reflects that
> DEAE sub-event sensor patterns are more diverse: different DEAE sub-steps capture distinct
> phases (equilibration, loading, washing, elution) with very different sensor profiles,
> so no single direction dominates. More PCs would be needed to reach the same cumulative
> variance as PG.

---

### Cell 14 — Save Final Basetables

Three parquet files are saved to `OUTPUT_DIR/basetable_v5/`. Both imputation (Cell 13)
and PCA reduction (Cell 13b) are baked in — no separate preprocessing step is needed.

```
Saving to: C:\Hackathon-GSK\data\processed\basetable_v5\

  ip1_basetable_v5.parquet    shape=(88, 864)
  ip2_basetable_v5.parquet    shape=(30, 845)
  ip3_basetable_v5.parquet    shape=(87, 861)
```

> Column counts differ between serotypes because IP1/IP2/IP3 have different SAP column
> counts (147/133/144) and different numbers of `_ran` binary flag columns from the
> Child 2 sub-step imputation in Cell 13.

---

## 4. Output Files

All outputs at `C:\Hackathon-GSK\data\processed\`

### Intermediate files

| File | Shape | Description |
|------|-------|-------------|
| `sensor_aggregated_features_v4.parquet` | (206, 8121) | Full combined feature table (fullrun + elution + events + child2) |
| `sensor_features_fullrun_v4.parquet` | (206, 7857) | Full-run sensor stats + ev_cols (for modeling) |
| `sensor_features_elution_v4.parquet` | (206, 7857) | Elution sensor stats + ev_cols (for modeling) |

### PCA model files (`pca_models/`)

| File | Description |
|------|-------------|
| `pg_sub_scaler.joblib` | `StandardScaler` fit on IP1 `pg_sub_*_sensor_*` columns |
| `pg_sub_pca.joblib` | `PCA(n_components=5)` fit on scaled IP1 PG sub-event sensor cols |
| `deae_sub_scaler.joblib` | `StandardScaler` fit on IP1 `deae_sub_*_sensor_*` columns |
| `deae_sub_pca.joblib` | `PCA(n_components=5)` fit on scaled IP1 DEAE sub-event sensor cols |

### Final basetables (`basetable_v5/`)

These are the primary outputs for modeling. Each file is fully merged, imputed, and PCA-reduced.
The `*_sub_*_sensor_*` block (~6,238 columns) has been replaced by 10 PCA components.

#### `ip1_basetable_v5.parquet` — 88 rows × 864 cols

| Column group | Count | Description |
|---|---|---|
| SAP columns (`clarif_*`, `UF_*`, `PG_*`, `DEAE_*`, `PSV_*`, `GY_*`) | ~147 | Original SAP process parameters for all purification stages |
| `pg_sensor_*`, `deae_sensor_*`, `prep_sensor_*` | 264 | Full-run sensor stats (mean/std/min/max per channel per stage) |
| `pg_elution_*`, `deae_elution_*` | 264 | Sensor stats recorded only during the elution phase |
| `pg_sub_pc1` … `pg_sub_pc5` | 5 | PCA of PG sub-event sensor block (77.5% cumulative variance) |
| `deae_sub_pc1` … `deae_sub_pc5` | 5 | PCA of DEAE sub-event sensor block (63.0% cumulative variance) |
| `{prefix}_ran` | ~82 | Binary flag: 1 = sub-step ran for this batch |
| `ev_*` | 25 | Phase-level event duration features from Cell 5 |
| `pg_child2_*`, `deae_child2_*` | 345 | Child 2 sub-event duration in hours |
| `pg_child1_*`, `deae_child1_*` | 4 | Child 1 operation duration in hours |
| `sensor_data_imputed` | 1 | 1 = full-run sensor values are imputed |
| `pg_has_elution_data`, `deae_has_elution_data` | 2 | 1 = elution was recorded for this batch |

#### `ip2_basetable_v5.parquet` — 30 rows × 845 cols

Same column structure as IP1 but with SAP IP2 columns (~133 SAP cols).

#### `ip3_basetable_v5.parquet` — 87 rows × 861 cols

Same column structure as IP1 but with SAP IP3 columns (~144 SAP cols).

---

## 5. How to Use the Outputs

The v5 basetables are already merged, imputed, and PCA-reduced. The separate merge and
imputation steps from the v2 workflow are **not needed**.

```python
import pandas as pd
from pathlib import Path

BT_DIR = Path(r"C:\Hackathon-GSK\data\processed\basetable_v5")

ip1 = pd.read_parquet(BT_DIR / 'ip1_basetable_v5.parquet')
ip2 = pd.read_parquet(BT_DIR / 'ip2_basetable_v5.parquet')
ip3 = pd.read_parquet(BT_DIR / 'ip3_basetable_v5.parquet')

# Target variable — note the GY_ prefix used in v5 basetables
target_col = 'GY_011 PSV - Global Yield total [%]'
y = ip1[target_col]
X = ip1.drop(columns=[target_col])
```

**Before modeling — 4 recommended steps:**

1. **Sub-event sensor dimensionality is already reduced** — Cell 13b applied PCA and
   replaced ~6,238 `*_sub_*_sensor_*` columns with 10 PC scores (`pg_sub_pc1`–`pc5`,
   `deae_sub_pc1`–`pc5`). You do not need to apply variance threshold or correlation
   filter to the sub-event sensor block; that is handled.

2. **Drop quasi-constant columns** (variance threshold) — the remaining duration and
   elution columns may still have near-zero variance for some serotypes.
   Use `VarianceThreshold(threshold=0.01)` on the non-PCA columns.

3. **Feature selection** — ~864 features for 88 rows is still high-dimensional.
   Use Pearson r (feature_selection_local/global notebooks), Lasso (L1 regularization),
   or Random Forest feature importance to reduce to a tractable feature set.

4. **Keep IP1 and IP3 separate** — do not pool serotypes in the same model. IP1
   (Serotype 1) and IP3 (Serotype 3) have different biology and different batch
   counts; models trained on pooled data will be biased toward whichever serotype
   is more numerous.

```python
from sklearn.feature_selection import VarianceThreshold

# Step 1: drop near-constant columns
selector = VarianceThreshold(threshold=0.01)
X_var = pd.DataFrame(selector.fit_transform(X),
                     columns=X.columns[selector.get_support()])

# Step 2: drop highly correlated columns
corr = X_var.corr().abs()
upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
to_drop = [col for col in upper.columns if any(upper[col] > 0.95)]
X_filtered = X_var.drop(columns=to_drop)

# Step 3: chronological train/test split (NO random shuffle)
X_train = X_filtered.iloc[:int(0.8 * len(X_filtered))]
X_test  = X_filtered.iloc[int(0.8 * len(X_filtered)):]
```

---

## 6. Sensor Channels

21 numeric channels are aggregated (mean, std, min, max) and 1 boolean channel is used
for elution detection.

| Column | Type | Likely meaning |
|--------|------|---------------|
| `AI_A1`, `AI_A2`, `AI_A3` | Numeric | Analog inputs — likely UV absorbance at different wavelengths or positions |
| `Accumulated Volume` | Numeric | Cumulative process volume passed through the column (mL or L) |
| `FIC_C11` | Numeric | Flow indicator/controller — volumetric flow rate |
| `MT_I1_OUT`, `MT_I2_OUT` | Numeric | Motor or actuator outputs — pump drive signals |
| `PIC_A1` | Numeric | Pressure inlet (analog) — inlet pressure to the column |
| `PIC_I1`, `PIC_I1_OUT` | Numeric | Pressure inlet (instrument) — inline pressure measurement and output |
| `PI_A2` | Numeric | Pressure indicator (analog, position 2) — possibly outlet pressure |
| `TA_A2_ASYM` | Numeric | Column quality: peak asymmetry measured at position A2 |
| `TA_A2_HETP` | Numeric | Column quality: HETP (Height Equivalent of a Theoretical Plate) at A2 |
| `TA_O1_ASYM` | Numeric | Column quality: peak asymmetry at outlet O1 |
| `TA_O1_HETP` | Numeric | Column quality: HETP at outlet O1 |
| `TI_A1`, `TI_A2` | Numeric | Temperature at positions A1 and A2 — buffer or column temperature |
| `UV Light` | Numeric | UV absorbance — primary signal tracking virus elution peak |
| `XV-O1_ZSO` | Numeric | Valve position (outlet valve 1) — 0=closed, 1=open |
| `RunCalc_UV_DuringHarvest` | Numeric | Software-computed UV absorbance during the harvest collection window |
| `RunCalc_UV_ForIntegral_v2` | Numeric | Software-computed UV integral — proportional to total product collected |
| `UV Elution` | Boolean (0/1) | Flag: 1 = the UNICORN control system is in elution/collection mode |

> A full sensor-to-physical-measurement dictionary mapping `AI`, `PIC`, `TI` to specific
> sensor locations on the XTO equipment is pending from GSK.

**Column naming in basetables:**

- Full-run: `{stage}_sensor_{channel}_{stat}` — e.g., `deae_sensor_UV Light_mean`
- Elution-phase: `{stage}_elution_{channel}_{stat}` — e.g., `deae_elution_UV Light_mean`
- Sub-event: `{stage}_sub_{step_key}_sensor_{channel}_{stat}` — e.g.,
  `deae_sub_xto_inlet_20x__14_1_sensor_PIC_I1_mean`

---

## 7. Known Limitations

| Issue | Impact | Recommendation |
|-------|--------|----------------|
| 61 batches missing PG sensor data | `pg_sensor_*` columns set to serotype column mean; `sensor_data_imputed=1` for those batches | Request the missing XTO PG sensor files from GSK (batches likely ran on an unlisted controller) |
| 1 SAP batch missing from sensor output (206 vs 207) | Minor; one batch has no events coverage in any of the 7 files | Acceptable — batch will be SAP-only in the basetable |
| Child 2 sub-event columns: 7,216 cols for 88–87 rows | Extreme high-dimensional regime; standard linear models will overfit without strong regularization | Use Lasso / Elastic Net, or Random Forest with importance threshold before any linear model |
| Instance numbers (`__13_1`, `__7_1`) undocumented | Cannot interpret which specific phase each instance represents without the XTO controller protocol | Request XTO UNICORN protocol documentation from GSK; do not strip instance suffixes until documented |
| `pg_deae_up2` and `pg_up3` skipped | No `ev_pg_deae_up2_*` or `ev_pg_up3_*` columns in the basetables | These are CIP and column qualification runs; skipping is correct per the `_batches` naming convention |
| Child 2 `_ran` flags based on 20% coverage filter | Sub-step types present in < 20% of batches are excluded entirely from both duration and sensor features | Adjust `CHILD2_MIN_BATCH_COVERAGE` if a rare but potentially important step needs to be included |
| Sub-event sensor pass match rate varies widely by XTO | XTO53103 has only 2.3% of rows kept (low density of sub-step windows); XTO53104 has 85.8% | Expected: XTO53103 covers a wider calendar date range with long idle periods between batches |
