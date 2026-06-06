# PROCESS_CONTEXT.md — IPV Production Process Reference
> Biological and process context for the GSK Hackathon project.
> Use this file to understand what each production stage does and why each variable matters.

---

## What is IPV?
**IPV = Inactivated Polio Vaccine** — produced from the wild (Salk) strain of Poliovirus.
- 3 serotypes: **ST1, ST2, ST3** (corresponding to SAP files IP1, IP2, IP3)
- Virus grown in **VERO cells** (African green monkey kidney epithelial cells)
- Virus is killed (inactivated) with **formaldehyde** before use as a vaccine
- Produced at **GSK Wavre, Building WN48**, approved EU (March 2020) and US (December 2020)
- Historical success rate: ~80–90% per production campaign

---

## Full Production Process Overview

### Phase 1: Cell & Virus Culture (~4 weeks)

#### 1a. Stationary Cell Culture (3 weeks)
Growing VERO cells from a frozen ampoule through increasingly large vessels:

```
Cell bank ampoule → 4× T175 flask (Day 0)
→ 16× T175 (Day 4)
→ 3× MT10 (Day 7)
→ 8× MT10 (Day 11)
→ 14-16× MT40 (Day 15)
→ Mixing bag 50L → 600L Bioreactor (Day 20)
```

**Growth medium:** M199 + 5% serum (nutrients, growth factors, amino acids, vitamins)
**Trypsination** used between passages to detach cells from surfaces.

#### 1b. Cell Culture in Bioreactor (5 days)
- **600L bioreactor** with Cytodex microcarrier beads (6g/L) — cells adhere to bead surfaces
- Conditions: T° 36.5°C, agitation 15 RPM, pH 7.00, O2 25%
- Perfusion feeds: 300L (Day 2-3), 600L (Day 3-4), 900L (Day 4-5)
- **QC:** cell count, pH, identity by DNA fingerprinting, sterility tests

#### 1c. Viral Culture (3 days)
- Working seed virus (ST1, ST2, or ST3) inoculated into bioreactor
- **MOI = 0.1** (1 virus per 10 cells) — two infection cycles occur
- Medium changed to M199 maintenance (no serum) after infection (Day 1)
- Tween 80 10% added before harvest to disperse viruses and lyse remaining cells
- **QC:** Polio antigen content by ELISA, sterility tests, protein by Lowry

---

### Phase 2: Purification (3 days) — MAIN DATA FOCUS

**Goal:** Remove cellular debris, proteins, DNA, endotoxins — retain pure Poliovirus.

#### 2a. Clarification (0.5 day)
- **Input:** ~600L bioreactor harvest
- **Output:** ~600L Clarified Bulk
- **Process:** Cytodex beads and cell debris sediment → surnageant filtered through 10µm → 0.5µm → 0.45-0.2µm train
- **Key fact:** ~10% antigen is inherently lost here — virus trapped in Cytodex pellet
- PBS rinse recovers some virus from pellet, but 10% loss is unavoidable
- **QC:** Clarification yield, Polio Ag ELISA, protein by Lowry, pH

#### 2b. Ultrafiltration / UF (0.5 day)
- **Input:** ~600L Clarified Bulk
- **Output:** ~7.5L Retentate (concentrated virus)
- **Process:** 
  - Phase 1 — Concentration ×10 (300 kDa membrane cut-off, 10 cassettes)
  - Phase 2 — Diafiltration: 6 volumes of PBS buffer exchange (removes serum proteins)
  - Phase 3 — Final concentration to ~7.5L
- **Why important:** Removes intracellular proteases released by lysed cells (which could damage virus)
- Permeate (small molecules < 300 kDa) is discarded; Retentate (virus) is kept
- **QC:** UF yield, Ag ELISA, protein Lowry, bioburden

#### 2c. PG — Size Exclusion Chromatography (1 day)
- **Input:** ~7.5L UF Retentate
- **Output:** ~20L Pool PG
- **Process:** Two columns in series; virus (~28-30nm) passes between gel beads (large → fast), small contaminants enter pores (small → slow)
- Poliovirus eluted first, collected by UV280nm detection profile
- **Goal:** Separate virus from BSA, aggregates, and contaminants of different sizes
- **QC:** PG yield, protein Lowry, Ag ELISA, BSA content

#### 2d. DEAE — Ion Exchange Chromatography ← KEY IMPROVEMENT TARGET
- **Input:** ~20L Pool PG
- **Output:** ~20-24L Pool DEAE
- **Process:** Positively charged gel beads; virus (weakly negative) passes through in flow-through; negatively charged contaminants (DNA, endotoxins, BSA) bind to resin and are retained
- **Goal:** Remove final impurities — DNA, endotoxins, BSA
- Column prep: hydration, equilibration, pH check, conductivity check
- **QC:** Bioburden, pH before adjustment, harvested volume, DNA by Q-PCR

#### 2e. PSV — Pre-filtration and pH Adjustment
- **Input:** ~20-24L Pool DEAE
- **Output:** ~8-10.5L PSV (Pre-filtered Sterile Virus)
- **Process:** pH adjustment of DEAE pool → 0.22µm filtration to reduce bioburden
- pH correction prevents calcium phosphate precipitates (which could trap virus and block formaldehyde inactivation)
- **QC:** pH after adjustment, protein Lowry (µg/dose AND µg/ml), Ag ELISA, PSV yield, **Global purification yield** ← our target

#### 2f. DPV — Dilution
- **Input:** PSV
- **Output:** DPV (Diluted Purified Virus) → 55-220L (depending on 1-3 lots pooled)
- **Process:** 1 part PSV + 2 parts M199 inactivation medium (3× dilution)
- M199 inactivation contains Tween 80, glycine (prevents viral aggregation during inactivation)
- **QC:** Sterility (FTM + TSB), endotoxin by gel clot, DNA content, pH

---

### Phase 3: Inactivation (15 days)

**Goal:** Kill (inactivate) the virus using formaldehyde so it can no longer cause disease, while preserving antigenic structure for immune response.

Timeline:
- **Day -1:** 0.22µm filtration of DPV (remove aggregates)
- **Day 0:** Add formaldehyde solution (target: 100µg/ml), check pH and formol concentration
- **Days 1-3:** Monitor and adjust formol concentration
- **Day 6:** Filter and switch tanks (ensure all virus contacts formaldehyde)
- **Day 10:** Inactivation verification
- **Day 15:** Final sterile filtration (0.22µm) ← critical last sterilization before patient injection

Storage: +4°C, max 12-18 months, 62-68L per lot (from 1 DPV)

---

## Key Biological Concepts for Feature Engineering

| Concept | Relevance |
|---------|-----------|
| ELISA (Ag content in DU/ml) | Measures antigen quantity — primary yield measurement |
| Protein by Lowry (µg/ml) | Measures total protein — purity indicator (lower = better after purification) |
| Bioburden (CFU/ml) | Microbial contamination count — safety indicator |
| Endotoxin (EU/ml) | Toxic bacterial byproduct — must be below threshold |
| BSA (ng/ml) | Bovine Serum Albumin — residual from growth medium, must be eliminated |
| Purification factor | Ratio of purity improvement (Ag/protein ratio after vs before step) |
| Protein/Ag ratio | Purity indicator — lower = purer |
| % protein elimination | How much host protein was removed at each step |
| pH correction | Critical for preventing Ca-phosphate precipitates (traps virus) |
| Conductivity | Ion exchange equilibration quality indicator |
| MOI (Multiplicity of Infection) | 0.1 — 1 virus per 10 cells at infection |

---

## Serotype Differences

| | ST1 (IP1) | ST2 (IP2) | ST3 (IP3) |
|---|---|---|---|
| Doses/lot | ~1.6M | ~4.3M | ~1.7M |
| Batch frequency | High | Low (lower patient dose needed) | High |
| Biology | Similar to ST3 | Very different | Similar to ST1 |
| Equipment/process | Identical for all three | | |

> Model each serotype separately. Seek improvements applicable to ST1 + ST3 first (similar biology), then test on ST2.

---

## Volume Flow Through Process

```
Bioreactor (600L)
  → Clarification (~600L Clarified Bulk)
  → Ultrafiltration (~7.5L Retentate)
  → PG Chromatography (~20L Pool PG)
  → DEAE Chromatography (~20-24L Pool DEAE)
  → PSV filtration/pH adjustment (~8-10.5L)
  → DPV dilution (×3) → (~55-220L, 1-3 lots)
  → Inactivation → Storage (62-68L/lot)
```

---

## Sensor Naming Conventions (Partial — await full GSK dictionary)

Sensor names are machine-generated. Known patterns:
- `TT` → Temperature transmitter
- `AI` → Analog input (e.g., pH, UV absorbance)
- `PIC` → Pressure indicator controller
- `FIC` → Flow indicator controller

Key distinction for sensor analysis:
- Sensors **before column** (inlet): measure input conditions
- Sensors **after column** (outlet): measure process output / separation quality

---

## QC Test Categories Reference

| Category | Meaning |
|----------|---------|
| Test de release (QR) | Must pass before batch is released for use |
| Quality decision (QD) | Triggers go/no-go decision |
| Monitoring QC (PM) | Ongoing monitoring, not a gate |
| Contrôle Production (MC) | Production control check |
| Caractérisation | Characterization only, not a release criterion |
