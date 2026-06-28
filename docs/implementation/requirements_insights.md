# Requirements: Insights & Slide Deck

Scope: exploratory insights and stakeholder presentation. **Prerequisite:** [requirements_eda.md](requirements_eda.md) — runbook and Streamlit dashboard with KPI charts.

## End-to-end flow

```text
Streamlit (KPI charts)  →  document insights  →  slide deck (communicate)
```

Insights are derived from the dashboard after KPIs are visible. The deck communicates findings — it is not part of the EDA deliverable.

## Insight workflow

1. Explore KPI charts in Streamlit (Ads / CRM / Product tabs).
2. Document **6 insights** — **2 Ads**, **2 CRM**, **2 Product** — tied to embedded data stories (see [requirements_kpis.md](requirements_kpis.md)).
3. Export key charts (Plotly → PNG) for the deck.
4. Synthesize **recommendations** for the Growth team.

## Slide export workflow

1. Build the warehouse (if missing): `python run.py all` or `make all`
2. Export chart and diagram PNGs: `python scripts/export_slide_assets.py` or `make slides`
   - Plotly charts use the same queries and helpers as Streamlit (`app/tabs/*`, `app/views/charts.py`)
   - Outputs land in `docs/slides/assets/`
   - Mermaid sources in `docs/slides/diagrams/`; rendered via `@mermaid-js/mermaid-cli` when Node.js is available, otherwise Pillow fallbacks
3. Build PPTX from `deck.md`: `python scripts/build_deck.py` or `make deck`
   - Editable text boxes + separate PNG shapes (Marp `--pptx` rasterizes the whole slide)
   - Optional HTML preview: `cd docs/slides && npm run preview`

```bash
make deck
```

**External tools:** `@mermaid-js/mermaid-cli` (optional diagrams). **Python:** `kaleido` (Plotly PNG), `python-pptx` (deck build).

Each insight should include:

- Metric definition (what, grain, formula).
- Chart (exported from Streamlit).
- Recommendation (actionable for Growth team).



### Data Insigts Found


| #   | Domain  | Story hook (examples)                                                                                                                                                                                                                                                                  |
| --- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Ads     | LinkedIn vs Google CAC: Google ~$1.5k / ~257 wins (~$381k spend); LinkedIn ~$28k / ~43 wins (~$1.2M spend, ~3× budget). Avg seats ~295 on both; Enterprise win mix ~47% on both (Ent ~505 seats, SMB ~105) — deal size does **not** explain the CAC gap. Other diffs: Google ~4× lead volume, ~5× lower CPC, ~3× higher CTR; cost per seat ~$5 vs ~$93. Outcome: LinkedIn is expensive for acquisition overall; reallocate or cap spend unless non-CAC goals (brand, ABM lists) justify it. Google is the efficient channel for both SMB and Enterprise volume. |
| 2   | Ads     | Meta ~$115k CAC, ~4.3% CTR, ~$230k spend, **2 wins** (~6.7k leads). Strong delivery (highest CTR, lowest CPC, most leads) but **demo→proposal ~7%** vs ~55% on Google/LinkedIn; call→demo also weaker (~37% vs ~66%). Outcome: awareness/volume channel, not a scalable close channel. Recommendation: audit targeting and post-demo motion before scaling; check Meta-specific landing pages/creative if any; pause or cut spend if ICP mismatch is confirmed (not a tracking bug). |
| 3   | CRM     | UK ~44% and US ~42% proposal→win vs DACH ~31%; early funnel rates match (~30% demo→proposal, ~6d call→demo). UK/US move faster through the CRM funnel — ~13d lead→proposal vs ~16d DACH, ~12d proposal→win vs ~16d, ~25d lead→win vs ~32d. Deal sizes similar (~295 seats). Outcome: higher win rate tracks funnel velocity, not lead quality or deal size; use market-specific targets and close playbooks; prioritize DACH proposal-stage speed and conversion blockers (procurement, pricing, legal). |
| 4   | CRM     | Enterprise proposal→win **~40%** vs SMB **~33%**; gap persists in DACH (36% vs 28%) and across channels (Google 46% vs 37%, LinkedIn 41% vs 34%). Deal size differs (~515 vs ~106 seats) but timing is similar (~15d to proposal). Outcome: don't run one global close motion — prioritize Enterprise playbooks in DACH; diagnose SMB proposal-stage drop-off separately. |
| 5   | Product | **Analytics addon lifts seat utilization (SMB).** Baseline util sits **~50–65%** across seat buckets without a clear segment winner. With the addon, SMB util jumps to **~72%** overall (no addon **~56%**); **\<100** and **100–199** seat buckets reach **~73%** and **~71%** vs **~54%** and **~58%** without. Enterprise shows no addon lift (~54% vs ~57%). Outcome: strong product dependency — analytics drives usage where it is adopted. Recommendation: **package analytics for SMB** (default attach, trial, or bundled tier) so smaller accounts get the same utilization lift mid-market sees on addon. Chart: utilization by analytics addon; utilization by contracted seats (filter SMB + addon). |
| 6   | Product | **Longer contracts and Enterprise correlate with lower utilization — high-value accounts at churn risk.** Contract **25–36 mo** averages **~56%** util vs **~60–64%** for **12–18** and **19–24 mo** buckets. **Enterprise ~56%** vs **SMB ~63%** — same pattern (Enterprise tends toward longer contracts and more seats). These are the most valuable clients but the hardest to keep engaged. Outcome: low usage precedes renewal risk on the accounts that matter most. Recommendation: **proactive CS playbooks** for Enterprise and 25–36 mo cohorts — onboarding health checks, executive QBRs, utilization targets, analytics addon push where missing. Strategic theme across insights 4 + 6: **prioritize the most valuable, important, and difficult clients** (Enterprise close motion + post-sale usage). Charts: utilization by contract length; utilization by segment. |




## Slide deck (final paper)

**6–10 pages** per assignment brief. Content derived from Streamlit exploration, not a screenshot dump.

### Required slide content


| Section                               | Source                                                                                                                                                           |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Data model diagram                    | Mermaid / dbt docs export ([requirements_data_model.md](requirements_data_model.md))                                                                             |
| Conversions in CRM (not ads)          | One slide: wins = conversions; attributed to campaigns via `lead_id` ([requirements_data_model.md](requirements_data_model.md#conversions-assignment-alignment)) |
| 5 metrics with rationale              | Metrics layer + definitions ([requirements_kpis.md](requirements_kpis.md))                                                                                       |
| Exploratory insights + visualizations | Streamlit (exported charts) — **6 insights**                                                                                                                     |
| Recommendations                       | Synthesized from dashboard findings; include **SMB analytics packaging** and **Enterprise / long-contract CS focus**                                             |


Store deck assets under `docs/slides/` (slide source, PNG exports, built PPTX).

## Repo structure (delivery)

```text
docs/
├── implementation/
│   └── requirements_insights.md   # this doc
└── slides/
    ├── deck.md                    # slide source (parsed by build_deck.py)
    ├── assets/                    # exported chart + diagram PNGs
    └── diagrams/                  # Mermaid sources (.mmd)
scripts/
├── export_slide_assets.py         # Plotly → PNG (+ diagram export)
└── build_deck.py                  # deck.md → deck.pptx (editable text + PNGs)
```



## Acceptance criteria

- [x] **6 insights** (2 Ads, 2 CRM, 2 Product) with charts suitable for slide export.
- [x] Slide deck (6–10 pages) references model, metrics, insights, and recommendations.
- [x] Slide deck cites grain and formula for each metric shown.