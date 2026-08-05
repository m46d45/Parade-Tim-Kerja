# Software Impacts — Original Software Publication (OSP) Draft

> **How to use this file**  
> 1. Copy sections into Elsevier’s official **SIMPAC OSP template**  
>    (Word: `SIMPAC_OSP_Template.docx` or LaTeX from the [Guide for Authors](https://www.sciencedirect.com/journal/software-impacts/publish/guide-for-authors)).  
> 2. Replace every `[PLACEHOLDER]` with final author/impact data.  
> 3. Submit **Highlights** as a separate file named `highlights`.  
> 4. Upload figures as separate files (Fig. 1, Fig. 2).  
> 5. This draft is intentionally ~OSP length (short descriptive paper, ≈3 pages in journal layout).  
> 6. *Software Impacts* expects evidence that the software contributed to peer-reviewed research; complete the **Impact Overview** carefully before submission.

---

## Title page

**Title**

Parade Tim Kerja: an open educational simulator of zone-flow construction production, variability, cost, and takt planning

**Authors**

[Given name Family name]<sup>a,*</sup>, [Given name Family name]<sup>a</sup>, …

**Affiliations**

<sup>a</sup> [Department], [Faculty], [University], [Street address], [City], [Postal code], [Country]

**Corresponding author**

* Corresponding author.  
E-mail address: [email@institution.edu] (G. Familyname).  
Postal address: [full postal address].  
Telephone: [+xx …].

**Present address** (if different): [optional footnote]

---

## Abstract

Parade Tim Kerja (“Work-Team Parade”) is an open-source, browser-based simulator for teaching and exploring project-production behaviour in construction. The tool implements a zone-flow *parade of trades* model for a five-trade concrete floor cycle: sequential crews advance across spatial zones under capacity limits, batch handoff policies, and optional per-zone production variability. Learners obtain Line of Balance charts, work-in-process (WIP) trajectories, utilisation, active/idle labour-cost metrics, and multi-scenario comparisons without installing local software. Built-in analytics connect simulation outcomes to Little’s Law, Kingman’s VUT approximation, inventory–fill-rate trade-offs, and an educational takt-planning module that separates physical *bays* from planning *zones* on a fixed floor area. Results export to CSV/Excel for classroom reporting. The software is implemented in Python with a Streamlit interface, documented with an Indonesian teaching manual, and released publicly for reuse in civil engineering education, Lean Construction workshops, and reproducible classroom experiments on workflow variability and handoff batch size.

**Word count (abstract):** ≈168 (≤250 required).

**Keywords (max 7)**  
construction simulation; lean construction; parade of trades; takt planning; Little's Law; educational software; zone flow

---

## Highlights  
*(submit as separate file `highlights`; each bullet ≤85 characters including spaces)*

- Open Streamlit simulator of zone-flow parade for floor-cycle concrete work  
- Links capacity, variability, and batch handoff to LOB, WIP, cost, and util.  
- Embeds Little’s Law, Kingman VUT, and inventory–fill-rate classroom charts  
- Takt module maps 3×3 m bays to discrete zones and owner time per floor  
- Browser demo and CSV/Excel export; no learner-side Python install required  

*(Character counts are within the 85-character guideline; trim further if the journal counter differs.)*

---

## Graphical abstract  
*(encouraged; upload separately)*

**Suggested layout (single wide strip):**  
Left: five coloured trade “wagons” advancing across zones (banner animation concept).  
Centre: Line of Balance with five trade curves under two variability levels.  
Right: takt wagon chart (T1–T5 bars) and one metric strip (duration / idle cost / TD).  

Caption idea: *Parade Tim Kerja connects zone-flow simulation, production analytics, and takt planning in one browser tool.*

---

## 1. Motivation and significance

Construction production systems are chains of specialised trades that hand work to one another across space and time. When upstream production is variable or handoffs are batched, downstream crews starve or wait, project duration grows, work-in-process (WIP) accumulates, and labour spends non-productive time on site. These mechanisms are central to Lean Construction and project production management, yet they remain difficult to *experience* in a lecture: spreadsheet demos are opaque, and paper-based parade games do not scale to multi-metric comparison, cost, or takt arithmetic in one session.

The classic *parade of trades* / Parade Game pedagogy [1] established that workflow variability and trade interdependence drive system performance more than local productivity alone. Factory Physics and related production theory formalise the same ideas through Little’s Law, utilisation–variability–time (VUT) relationships, and inventory–service trade-offs [2,3]. In parallel, takt planning translates customer demand and available time into a production beat and zone structure for construction [4,5]. Educators need a single, transparent, open tool that (i) runs a zone-flow parade with controllable capacity, variability, and batch handoff; (ii) visualises Line of Balance (LOB), WIP, and utilisation; (iii) links outcomes to production laws; and (iv) introduces takt decisions (bays versus zones, time per floor) without requiring learners to install a programming stack.

**Parade Tim Kerja** addresses that gap. It provides:

1. An open, reproducible **zone-flow engine** for a five-trade concrete floor cycle (formwork, rebar, pour, strip, finish), with seedable variability and configurable batch handoff (including one-piece flow).  
2. **Classroom analytics**: LOB, buffer WIP, utilisation, active/idle cost, multi-scenario comparison (2–5 scenarios), and export to CSV/Excel.  
3. **Theory bridges**: Little’s Law / WIP–throughput–cycle-time views, Kingman-style VUT intuition, and inventory–fill-rate charts.  
4. A **takt-plan module** grounded in a fixed floor geometry (360 m², 3×3 m bays → 40 bays) where *bay ≠ zone*; learners choose discrete zone counts {1, 5, 10, 20, 40}, capacity in bays/day, and owner time per floor, then compute train duration \(TD = (TW + TZ - 1) \times t_e\) with \(TW = 5\).  
5. **Zero-install access** via Streamlit in the browser, plus an Indonesian-language teaching manual for regional adoption.

The software is intended primarily for civil engineering and construction management education and Lean workshops; it also supports exploratory academic use wherever a transparent parade model with production metrics is required. Scientific impact is documented in Section 3 and should be updated with peer-reviewed outputs that used the tool [PLACEHOLDER: cite your paper(s)].

---

## 2. Software description

### 2.1. Software architecture

Parade Tim Kerja is implemented in **Python 3** and organised into modular packages:

| Component | Role |
|-----------|------|
| `parade_of_trades_core.py` | Discrete zone-flow simulation engine: trade capacities, per-zone variability draws, batch handoff, production history, duration and idle capacity. |
| `parade_of_trades_analysis.py` | Cost (active/idle), Little’s Law metrics, Kingman-style aggregates, inventory–fill rate, takt plan construction \(TD=(TW+TZ-1)\times t_e\), export helpers. |
| `parade_of_trades_plots.py` | LOB, WIP, utilisation, cost comparison, takt wagon chart, and theory plots (matplotlib). |
| `app.py` | Streamlit UI: sidebar parameters, Simulation / Comparison / Takt plan / Manual tabs, session state, download buttons. |
| `MANUAL.md` | Teaching manual (Indonesian) aligned with the current model. |
| `test_*.py` | Unit/regression tests for core engine and plots. |

**Runtime stack:** Streamlit, matplotlib, NumPy, openpyxl (Excel export).  
**Deployment:** public GitHub repository; Streamlit Community Cloud (or equivalent) for browser use. Learners do not need a local Python environment.  
**Default classroom parameters (sidebar):** 10 zones (aligned with default takt \(TZ=10\)), seed 12345, batch size 4, five fixed trades, labour rate 100 cost units per trade-period (editable).

### 2.2. Software functionalities

**A. Simulation (single scenario).**  
Users select uniform or per-trade capacity profiles (e.g. slow / normal / fast), variability level (none → very high), and batch handoff size. A run produces: project duration; system throughput; summed active and idle *team-periods* (explicitly distinguished from calendar duration); active/idle cost; LOB; buffer WIP; utilisation; and optional deep-dive tabs for Little’s Law, Kingman intuition, and inventory–fill rate. Per-trade tables report start, finish, time on site, active/idle periods, and cost.

**B. Comparison (2–5 scenarios).**  
Quick fills include five variability levels, no-variability vs medium, and batch 1 vs 4. Results are compared on duration, cost (stacked active/idle), WIP, utilisation, and theory metrics—supporting head-to-head classroom debates.

**C. Takt plan (educational).**  
Fixed geometry: each floor is 360 m² with 3×3 m bays (9 m²) → **40 bays per floor**. Users set number of floors, **discrete zone count** \(TZ \in \{1,5,10,20,40\}\) so bays/zone are integers, available **time per floor** (default 15 days), and capacity in **bays/day/team** (default 4). Mapping:

\[
\text{bays/zone} = 40/TZ,\quad
\text{zones/day} = \frac{\text{bays/day}}{\text{bays/zone}},\quad
t_e = 1/(\text{zones/day}).
\]

Train duration per floor uses Little’s Takt Law form \(TD = (TW + TZ - 1)\times t_e\) with \(TW=5\) wagons fixed. Wagon charts label T1–T5 on bars (no redundant legend). Feasibility is checked against time **per floor** only (no aggregate “total budget” narrative).

**D. Export and documentation.**  
CSV/Excel downloads support assessment and presentations. The in-app Manual tab documents model definitions (including cost window = start→own finish; bay ≠ zone).

**E. Illustrative outputs.**  
Fig. 1 shows a representative LOB under variability. Fig. 2 shows a takt wagon chart for \(TZ=10\), normal capacity 4 bays/day (\(t_e=1\) day/zone), \(TD=14\) days/floor.

*[Insert Fig. 1 here — LOB screenshot]*  
**Fig. 1.** Line of Balance for a five-trade zone-flow run (illustrative). Horizontal spacing between curves reflects waiting / buffer between trades.

*[Insert Fig. 2 here — takt wagon screenshot]*  
**Fig. 2.** Takt wagon chart for one floor (\(TW=5\), \(TZ=10\)). Bar labels identify trades T1–T5.

---

## 3. Impact Overview

*[This section is critical for Software Impacts. Replace placeholders with verifiable facts and cite peer-reviewed outputs.]*

### 3.1. Research and educational challenge addressed

The software operationalises parade-of-trades dynamics and production laws in a form suitable for **repeatable classroom experiments** and **exploratory analysis** of variability, batch handoff, labour idle cost, and takt zone granularity—problems that are otherwise taught only qualitatively or with one-off spreadsheets.

### 3.2. Evidence of use and scientific contribution

- **Teaching deployment.** Parade Tim Kerja has been used in [COURSE CODE — Course name] at [University], [Country], with approximately **[N]** students in **[semester/year]**. Students ran controlled scenarios (e.g. variability sweep; batch 1 vs 4) and interpreted LOB, WIP, cost, and takt \(TD\) against owner time per floor.  
- **Workshops.** The tool supported Lean Construction / project production workshops at **[event or institution]**, **[year]**, reaching **[N]** practitioners/students.  
- **Scholarly outputs.** Results obtained with (or enabled by) the software appear in:  
  - [Author et al., Year. Full bibliographic reference of peer-reviewed article.] [PLACEHOLDER — required by journal policy]  
  - [Optional: thesis, conference paper, preprint with DOI.]  
- **Open reuse.** Source code and manual are public; instructors can fork parameters (zones, seed, rates) for local curricula without relicensing friction once an OSI licence is applied to the repository.

### 3.3. Expected ongoing impact

We expect continued use in Indonesian and international construction-management courses, replication of Tommelein-style variability lessons with richer metrics (cost, Little, Kingman), and extensions to multi-floor or project-specific capacity data. Citation of the software and this Software Impacts article will provide a stable reference for reuse.

---

## 4. Illustrative examples

**Example A — Variability and idle cost.**  
With 10 zones, normal capacity, batch 4, and no variability, calendar duration and team-period totals diverge conceptually: five trades overlap, so summed active team-periods can exceed project duration, while idle team-periods stay near zero. Raising variability increases starvation between trades, idle periods, idle cost, and duration—visible on LOB “kinks” and cost comparison charts.

**Example B — Batch handoff.**  
Batch 1 (one-piece flow) versus batch 4, no variability: calendar duration typically shortens under smaller batches while pure active work content may remain similar if crews never wait—reinforcing that **duration ≠ active cost** when idle is zero.

**Example C — Takt zone granularity.**  
Floor 360 m², 40 bays, capacity 4 bays/day/team, \(TW=5\):  
- \(TZ=10\) → 4 bays/zone → 1 zone/day → \(t_e=1\) → \(TD=(5+10-1)\times 1=14\) days/floor.  
- \(TZ=20\) → 2 bays/zone → 2 zones/day → \(t_e=0.5\) → \(TD=(5+20-1)\times 0.5=12\) days/floor.  

Compared with a 15-day owner allowance per floor, both plans are feasible under these nominal parameters; coarser zoning (\(TZ=5\)) lengthens \(TD\) and may violate the allowance—supporting discussion of zone size as a planning decision, not as “customer demand”.

---

## 5. Conclusions and future improvements

Parade Tim Kerja packages a transparent zone-flow parade engine, production-system analytics, labour active/idle costing, multi-scenario comparison, and a bay/zone-aware takt module in an open browser application aimed at construction education and workshop use. Future work may include multi-floor parallel scheduling, bilingual UI, import of real crew productivity samples, accessibility hardening, and packaged CodeOcean capsules for formal reproducibility badges.

---

## CRediT authorship contribution statement

**[Author A]:** Conceptualization, Methodology, Software, Writing – original draft, …  
**[Author B]:** Software, Validation, Writing – review & editing, …  
*[Complete using Elsevier CRediT taxonomy.]*

---

## Declaration of competing interest

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.  
*[Or disclose as appropriate.]*

---

## Acknowledgements

[Optional: colleagues, class testers, funding in prose if not listed below.]

---

## Funding

This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.  
*[Or: This work was supported by … Grant No. ….]*

---

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

*[If applicable, e.g.:]*  
During the preparation of this work the author(s) used [TOOL] in order to [improve language / draft structure]. After using this tool/service, the author(s) reviewed and edited the content as needed and take(s) full responsibility for the content of the publication.  
*[If none: delete this section or state that no generative AI was used for manuscript text.]*

---

## Data availability

Simulation outputs are generated at runtime from user parameters and optional random seeds; they are not deposited as a static dataset. Example exports can be reproduced from the public repository using the documented defaults (total zones = 10, seed = 12345). The teaching manual is included in the repository (`MANUAL.md`).

---

## Code metadata / software availability

| Nr. | Code metadata description | Please fill in this column |
|-----|---------------------------|----------------------------|
| C1 | Current code version | [e.g. v1.0.0] |
| C2 | Permanent link to code/repository used for this code version | https://github.com/m46d45/Parade-Tim-Kerja |
| C3 | Permanent link to reproducible capsule *(optional CodeOcean)* | [URL or “N/A”] |
| C4 | Legal code licence | **[MUST BE OSI-approved, e.g. MIT — add LICENSE file to repo before submit]** |
| C5 | Code versioning system used | git |
| C6 | Software code languages, tools, and services used | Python 3, Streamlit, matplotlib, NumPy, openpyxl |
| C7 | Compilation requirements, operating environments | Python ≥3.10; `pip install -r requirements.txt`; or Streamlit Cloud |
| C8 | If available, link to developer documentation/manual | Repository `MANUAL.md`; in-app Manual tab |
| C9 | Support email for questions | [corresponding author email] |

**Live demonstration (optional but recommended):**  
[https://____.streamlit.app](https://____.streamlit.app) — *[paste public Streamlit URL]*

**Program title:** Parade Tim Kerja  
**Developers:** [Names]  
**Contact address:** [email]  
**Year first available:** 2026  
**Hardware requirements:** Standard web browser / or PC with Python 3  
**Software requirements:** See `requirements.txt`  
**Program language:** Python  
**Program size:** approximately [X] MB source (excluding caches)  
**Source code availability:** https://github.com/m46d45/Parade-Tim-Kerja  

---

## References

*[Any consistent style at submission; ensure DOIs where available.]*

[1] I.D. Tommelein, D. Riley, G.A. Howell, Parade Game: Impact of work flow variability on trade performance, J. Constr. Eng. Manage. 125 (5) (1999) 304–310. https://doi.org/10.1061/(ASCE)0733-9364(1999)125:5(304)

[2] W.J. Hopp, M.L. Spearman, Factory Physics, 3rd ed., Waveland Press, Long Grove, IL, 2011.

[3] J.D.C. Little, S.C. Graves, Little’s Law, in: D. Chhajed, T.J. Lowe (Eds.), Building Intuition, Springer, 2008, pp. 81–100. https://doi.org/10.1007/978-0-387-73699-0_5

[4] Lean Enterprise Institute, Takt time, LEI Lexicon. https://www.lean.org/lexicon-terms/takt-time/ (accessed 5 August 2026).

[5] A. Frandson, K. Berghede, I.D. Tommelein, Takt time planning for construction of exterior cladding, in: Proc. 21st Annual Conference of the International Group for Lean Construction (IGLC), Fortaleza, Brazil, 2013.

[6] Project Production Institute, Little’s Law in production systems with yield loss. https://projectproduction.org/journal/littles-law-in-production-systems-with-yield-loss/ (accessed 5 August 2026).

[7] J.F.C. Kingman, The single server queue in heavy traffic, Math. Proc. Cambridge Philos. Soc. 57 (4) (1961) 902–904. https://doi.org/10.1017/S0305004100036094

[8] [PLACEHOLDER — Your peer-reviewed article that used Parade Tim Kerja, full citation with DOI.]

[9] Lean Built, Is takt really magic? https://leanbuilt.us/is-takt-really-magic/ (accessed 5 August 2026).

---

## Appendix A — Suggested figure files for submission

| File | Content | Notes |
|------|---------|--------|
| `Figure_1_LOB.png` | LOB from Simulation tab, default-like params, with/without variability | ≥300 dpi; width suitable for 1 column |
| `Figure_2_Takt_wagon.png` | Wagon chart TZ=10, labels T1–T5 | No legend required |
| `Graphical_abstract.png` | Composite strip (optional) | 531×1328 px class dimensions preferred |

---

## Appendix B — Author checklist before upload to Editorial Manager

- [ ] Official **SIMPAC OSP template** used (not this Markdown alone)  
- [ ] Abstract ≤250 words  
- [ ] Keywords 1–7  
- [ ] Highlights file (3–5 bullets, ≤85 characters each)  
- [ ] **Impact Overview** filled with real teaching/research evidence  
- [ ] At least one **peer-reviewed** output cited that used the software (journal policy)  
- [ ] **OSI licence** file present on the GitHub default branch  
- [ ] Code metadata table complete; version tag released (e.g. `v1.0.0`)  
- [ ] Streamlit URL verified live  
- [ ] Figures as separate high-resolution files + captions in text  
- [ ] CRediT, funding, competing interest, data availability, AI declaration completed  
- [ ] All authors agree on order and corresponding author  
- [ ] Spelling checked; placeholders removed  

---

## Appendix C — One-paragraph “cover letter” draft

Dear Editor,

Please consider our Original Software Publication entitled “Parade Tim Kerja: an open educational simulator of zone-flow construction production, variability, cost, and takt planning.” The software provides an open, browser-based zone-flow parade simulator with production analytics (LOB, WIP, utilisation, active/idle cost), multi-scenario comparison, and an educational takt module that distinguishes bays from zones. It is released on GitHub and deployable via Streamlit for classroom use without local installation. We believe it fits Software Impacts’ scope of citable research software with documented educational and scientific use. The code is available at https://github.com/m46d45/Parade-Tim-Kerja under [LICENCE].

Sincerely,  
[Corresponding author name]  
[Affiliation, email]

---

*End of draft — edit freely; journal layout will compress this Markdown into ≈3 pages when figures are single-column and Impact/Related text is tightened.*
