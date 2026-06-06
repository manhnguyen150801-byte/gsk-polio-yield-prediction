# GSK_QA_RULES.md — Official GSK Q&A Clarifications
> These are direct answers provided by GSK during the hackathon feedback session (23/03/2026).
> These rules take priority over assumptions. Always check here before making modeling decisions.

---

## Target Variable

**Q: What is the primary target variable?**
> `011 PSV - Global Yield total [%]` — global yield across the full purification process up to PSV stage.

**Q: Should we build separate models for each yield step?**
> Primary target is global yield, but examine individual step yields heavily. No need for completely separate models per step, but **optimizing DEAE step** is the primary lever to drive global yield upward.

**Q: When should the model predict yield — early or late in the process?**
> Predict final yield, but use variables from **early cell culture AND individual purification steps**. Extreme upstream values can have downstream impacts. Correlation with early cell culture variables (e.g., `D0 – Viability [%]`, cell counts) is worth exploring.

**Q: What yield range is considered successful?**
> No specific "bad yield" threshold — the process is stable. A **successful batch performs above the historical median**. Goal is continuous improvement of the mean, not fixing failures. GSK uses a **3-Sigma approach** internally to flag anomalies.

---

## Data Cleaning Rules

**Q: What are `(OBS)` columns?**
> `(OBS)` = **Obsolete**. Historical audit trail values from older calculation methods. **Completely discard all (OBS) columns.** Use only the non-OBS primary measurement columns.

**Q: What causes zero-yield batches?**
> Zero yield in SAP is almost certainly **missing data** — the SAP system auto-fills voids with zeros when data is extracted. A true zero-yield batch would mean total loss, which is extremely unlikely.
> **Exception:** True zeros ARE valid for bioburden measurements.
> **Action:** Wait for GSK's **exclusion list** of interrupted/invalid batches. Only remove zeros listed there.

**Q: Are zero cell counts (`D1 16h-Cells count`, `D4 AM-cell count`) real?**
> No — operators simply stopped measuring at that moment. Zero = missing data. **Do not include zeros from these columns in your analysis.**

**Q: What are "Test BBT" batches?**
> Equipment calibration runs (e.g., injecting water into the chromatography column). **Remove completely** — not real vaccine batches.

**Q: What are "Corrected Parameter" columns?**
> Audit trail notation — a previously wrong value was corrected in the system. **Ignore the text "Corrected Parameter" columns entirely.** Trust and use the numerical data in the main measurement columns.

**Q: How to handle yields > 100%?**
> Testing artifact. The crude biological matrix makes ELISA underestimate starting antigen — so the final calculated yield can mathematically exceed 100% (up to ~140%). **Not real biological improvements.** Flag with 3-Sigma approach and handle as outliers carefully.

**Q: How to handle Pass/Fail missing values?**
> Treat as missing/excluded. A "Fail" typically has an operator comment, and failed batches will likely be on the GSK exclusion list.

---

## SAP Data Rules

**Q: Do IP1, IP2, IP3 files contain different batches?**
> Yes — entirely different batches corresponding to the 3 poliovirus serotypes (ST1, ST2, ST3). Same structure, directly comparable.

**Q: Why does IP2 yield better and have fewer batches?**
> IP1/IP2/IP3 = Serotypes 1, 2, 3. **Serotype 2 behaves very differently biologically** but uses the exact same process and equipment. Fewer IP2 batches because the required patient dose for Type 2 is lower.
> **Model them separately**, but seek improvements applicable to all 3 (ideally ST1 and ST3 first, without negatively impacting ST2).

**Q: Is the SAP column order chronological?**
> Yes — SAP ZQM105 columns follow the process chronologically from left to right (culture → clarification → UF → PG → DEAE → PSV → DPV). A single row = one complete batch.

**Q: Were there process/equipment changes between 2022-2025?**
> No. Equipment is not a factor and there were no "by-design" changes. The data can be treated as coming from a stable process.

**Q: Why is there a massive ~10% yield drop at Clarification?**
> Virus gets physically trapped in the Cytodex microcarrier bead pellet at the bottom of the bioreactor. PBS rinse recovers some, but ~10% loss is inherent to the process.

**Q: Which purification step contributes most to antigen loss?**
> The **Clarification step** — approximately 10% drop occurs immediately upon harvest. This is an inherent process loss, not an improvable parameter. **Focus on DEAE step for improvement.**

**Q: What do the IP2 column name differences mean (NaOH vs vol)?**
> Data entry quirk — no actual process difference between the three serotypes for that parameter.

---

## Events Data Rules

**Q: What do events represent?**
> Events are hierarchical ("Russian dolls"): broad phases → smaller sub-steps (Child 1 → Child 2). Use more specific levels (Chromatography_Procedure or lower) for your analysis, not the broad `Chromatography_UnitProcedure`.

**Q: What format are the timestamps in Events?**
> **Excel Serial Date floats** — represent year/month/day/hour/minute/second/millisecond. Convert with `pd.to_datetime` using Excel epoch (January 1, 1900). Do NOT treat as Unix timestamps.

**Q: What are the Duration column units in Events?**
> Duration = End time − Start time, both as Excel Serial floats (days). Duration is therefore also in **fractional days** — convert to hours/minutes/seconds.

**Q: What to do with blank BatchIDs in Events?**
> **Forward-fill** the Batch ID down the column until a new ID appears. The first listed Batch ID applies to all rows below it until a new one is encountered.

**Q: How do XTO files relate to Events files?**
> XTO files are time-series sensor samplings from chromatography equipment. Use the **start and end timestamps from the Events tables** to "cut" (slice) the XTO time-series data, isolating what happened during each specific step.

**Q: What is `Chromatography_Procedure` vs `Chromatography_UnitProcedure`?**
> `Chromatography_UnitProcedure` is broader/overarching. `Chromatography_Procedure` is more specific. **Focus on `Chromatography_Procedure` or lower-level steps.**

---

## Sensor / Time-Series Data Rules

**Q: What are the units of sensor columns (AI_A1, PIC_A1, FIC_C11, etc.)?**
> GSK will provide a **sensor dictionary** mapping probe names to metrics (temperature in °C, conductivity in mS/cm, pressure in bar, flow in L/min, pH, UV absorbance, etc.).

**Q: Where are the sensors physically located?**
> Key distinction: sensors are either **before the column** (pre-column inlet) or **after the column** (post-column outlet). This affects interpretation significantly.

**Q: How to link sensor data to batches?**
> Use the Event file's time window (start/end) to slice the XTO sensor data. Assign the corresponding Batch ID. That Batch ID can then be joined with the SAP data.

---

## Merging / Integration Rules

**Q: How do SAP and Events Batch IDs relate?**
> They are encrypted keys. **If the string matches exactly, it is the same batch.** No transformation needed.

**Q: How to link sensor data to SAP if there's no direct Batch ID?**
> Use **time brackets from Events** to slice sensor data → assign Events Batch ID → join with SAP using that ID.

**Q: What is the relationship between SAP time window and Events?**
> SAP ZQM105 encompasses the **entire batch overarching timeframe** (culture to end of purification). Events are **smaller time windows within** that SAP timeline — like Russian dolls inside the larger SAP batch window.

---

## Genealogy & CoA Data Rules

**Q: Should we use Genealogy data?**
> GSK guidance: **"Focus mainly on SAP data first and then time series data. If you got time, go for Genealogy."** It maps complex raw material composition across batches — treat as secondary/optional.

**Q: What about CoA (Certificate of Analysis) materials?**
> External supplier raw materials. **Not actively trended by GSK.** Only explore if you have extra time after completing SAP + time-series analysis.

---

## Modeling Guidance

**Q: Should we find one universal model for all serotypes?**
> Model serotypes separately, but **the ideal outcome is improvements applicable to all 3** (or at least ST1 and ST3 without negatively impacting ST2).

**Q: What is GSK's anomaly detection approach?**
> Internally uses **3-Sigma (3 standard deviations)** — if a metric deviates beyond this, it triggers an internal investigation.

**Q: Is the process currently stable?**
> Yes — no yield crisis. Goal is **continuous improvement** of the mean yield, not fixing broken batches. Any improvement above the current historical median is a success.

**Q: Which step is the key area for improvement?**
> The **final Ion Exchange (DEAE) step** is highlighted by GSK as the primary area to focus improvement efforts.
