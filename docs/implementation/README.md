# Docs

## Goal

Reproducible: clone the repo, generate fictional data locally, model the full customer journey (ads → CRM → product), explore KPIs in Streamlit, then present five core metrics and six insights in a slide deck.

```text
config/config.py + generate_data.py  →  warehouse.duckdb  →  dbt  →  Streamlit  →  slides
```

Nothing under `data/` is committed — only code and docs.

**Data design note:** The assignment lists ads “conversions”; in this model **conversions = CRM wins** (`crm_wins`), attributed to campaigns via `lead_id` → UTMs — not a column on ad platform data. Call this out on one slide.

## Quick run

```bash
python3.11 run.py all    # setup venv, generate raw data, dbt run + test
python3.11 run.py app      # Streamlit dashboard
```

Or: `make all` then `make app`.

## Slides

```bash
make deck    # export PNGs + build deck.pptx
```

Requires warehouse built (`make all`).

## Requirement docs

| Doc | Scope |
|-----|--------|
| [requirements_data_model.md](requirements_data_model.md) | Entities, dbt layers, join keys |
| [requirements_kpis.md](requirements_kpis.md) | Metric definitions, grains, dbt model names |
| [requirements_eda.md](requirements_eda.md) | Runbook, Streamlit dashboard |
| [requirements_insights.md](requirements_insights.md) | Insights (2 ads, 2 CRM, 2 product) and slide deck |

Assignment brief: [../requirements.md](../requirements.md)

## Implemented stack (as-built)

| Layer | Location |
|-------|----------|
| Config & story knobs | `config/config.py` |
| Raw data generator | `scripts/generate_data.py` |
| Pipeline runner | `run.py`, `Makefile` |
| dbt project | `dbt_deskbird/` — 5 staging, 4 intermediate, 4 marts, 6 metrics models |
| Dashboard | `app/` — Ads / CRM / Product tabs |
| Slide deck | `docs/slides/deck.md` + `scripts/export_slide_assets.py` |

**Five assignment metrics → implementation**

| # | Metric | dbt model | Streamlit tab |
|---|--------|-----------|---------------|
| 1 | CAC | `metric_cac` | Ads |
| 2 | Lead → funnel rate | `metric_funnel_rates` (`lead_to_funnel_rate`) | CRM |
| 3 | Win rate | `metric_funnel_rates` / `metric_win_rate` | CRM |
| 4 | Time to activation | Not a dedicated metric; `won_at` + `contract_start_date` on `fct_lead_journey`; CRM tab shows `metric_funnel_stage_latency` instead | CRM (supporting) |
| 5 | Retention | `metric_seat_utilization` (+ `metric_feature_adoption_rate` supporting) | Product |
