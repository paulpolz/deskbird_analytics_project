# Requirements: Data Model

Scope: high-level data architecture, entity design, dbt layering, and metric definitions. Raw tables are **defined here** but **generated locally** by `scripts/generate_data.py` — not stored in GitHub (see [README.md](README.md)).

## Goals

- Connect three fictional source domains (paid ads, CRM pipeline, product usage) in a scalable, stakeholder-readable way.
- Enforce clear grain discipline from raw events → user/account → dimensions → KPIs.
- Produce artifacts suitable for both the slide deck (conceptual diagram) and the repo (dbt lineage + SQL).

## Presentation formats

| View | Audience | Deliverable |
|------|----------|-------------|
| Conceptual | Growth / leadership (slides) | Layered ER / architecture diagram (raw → staging → marts → metrics) |
| Implementation | Reviewers (repo) | dbt models, `schema.yml`, `dbt docs generate` lineage graph |

Interactive lineage: `cd dbt_deskbird && DBT_PROFILES_DIR=. dbt docs generate && dbt docs serve`.

## Architecture layers

```text
raw (DuckDB)      ← generate_data.py loads tables in warehouse.duckdb
  ↓
staging/          ← 1:1 cleanup, typing, rename (utm → provider/campaign_id)
  ↓
intermediate/     ← spend rollup, funnel pivot, product enrichment, attribution
  ↓
marts/            ← dimensions + lead-journey fact
  ↓
metrics/          ← thin KPI models (pre-aggregated; no raw reads)
```

### Layer responsibilities (as-built)

| Layer | Grain | Models |
|-------|-------|--------|
| Staging | Source row, cleaned | `stg_ads`, `stg_crm_leads`, `stg_crm_funnel`, `stg_crm_wins`, `stg_product_events` |
| Intermediate | Event / touchpoint | `int_campaign_spend`, `int_funnel_events`, `int_lead_attribution`, `int_product_events` |
| Marts | Entity / journey | `dim_campaigns`, `dim_clients`, `dim_date`, `fct_lead_journey` |
| Metrics | KPI snapshot | `metric_cac`, `metric_funnel_rates`, `metric_win_rate`, `metric_funnel_stage_latency`, `metric_seat_utilization`, `metric_feature_adoption_rate` |

KPI models read only from marts/intermediate — not from raw tables or staging directly.

### Staging transforms

| Model | Key changes |
|-------|-------------|
| `stg_ads` | Cast `date`; pass through delivery metrics |
| `stg_crm_leads` | Rename `utm_source` → `provider`, `utm_campaign` → `campaign_id`; keep `segment` |
| `stg_crm_funnel` | Cast `entered_at` |
| `stg_crm_wins` | Derive `has_analytics_addon` from `additional_services` |
| `stg_product_events` | Cast `event_at`; nullable `seats_active`, `feature_name` |

### Intermediate logic

| Model | Purpose |
|-------|---------|
| `int_campaign_spend` | Ads facts + `month` truncation |
| `int_funnel_events` | Pivot stage events to `call_at` … `lost_at`; `call_to_demo_days`; `demo_sla_breached` (var `demo_sla_days=14`) |
| `int_lead_attribution` | Lead grain with `lead_month` |
| `int_product_events` | Product events joined to wins + leads (segment, addon, contract dates) |

### Marts

| Model | Grain | Key fields |
|-------|-------|------------|
| `dim_campaigns` | campaign | `provider`, `campaign_id`, `channel`, `country` (15 rows) |
| `dim_clients` | client | Contract facts + attribution dims from lead |
| `dim_date` | calendar day | Spine from min/max ad date |
| `fct_lead_journey` | lead | Full journey: ads attribution, funnel timestamps, terminal outcome, client/contract fields, latency days |

## Raw source domains (assignment inputs)

1. **Paid ads** — impressions, clicks, spend (campaign × provider × date). No conversion counts on the ad platform.
2. **CRM pipeline** — leads (attribution + segment), opportunity funnel (stage events), wins (client contracts). **Conversions = CRM wins** (`crm_wins`), attributed to campaigns via `lead_id` → lead UTMs → `provider` + `campaign_id` + `country`.
3. **Product usage** — logins, seat utilization, feature adoption (won clients only).

### Conversions (assignment alignment)

The brief lists **conversions** under paid ads. Ad platform data here has **impressions, clicks, spend only** — no conversion counts. **Conversions live in CRM** as closed-won clients (`crm_wins`). Attribute wins to campaigns via `lead_id` → lead UTMs → `provider` + `campaign_id` + `country`. Document this on one slide in the deck.

### Raw tables (generated into `raw` schema)

| Table | Grain | Key fields |
|-------|-------|------------|
| `raw.ads_campaign_daily` | provider × campaign × date | `provider`, `campaign_id`, `channel`, `country`, `date`, impressions, clicks, spend |
| `raw.crm_leads` | lead | `lead_id`, `utm_source`, `utm_campaign`, `channel`, `country`, `created_at`, **`segment`** |
| `raw.crm_opportunity_funnel` | funnel stage event | `funnel_event_id`, `lead_id`, `stage`, `entered_at` |
| `raw.crm_wins` | client (won) | `client_id`, `lead_id`, contract dates, `seats`, `contract_length_months`, `additional_services`, `market` |
| `raw.product_events` | event | `event_id`, `client_id`, `user_id`, `event_type`, `event_at`, `seats_active`, `feature_name` |

**Countries:** `DE`, `AT`, `CH`, `UK`, `US` on ads campaigns and leads; `crm_wins.market` must match lead `country`.

**Funnel stages:** `call` → `demo` → `proposal` → `won` | `lost`. Many leads remain **in progress** (open pipeline). Conversions (`crm_wins`) map to ads campaigns through lead attribution — not from ad platform reporting.

**Segment taxonomy:** `SMB` / `Enterprise` assigned at **lead creation** (`raw.crm_leads.segment`); seat counts at win follow segment ranges (<200 SMB, ≥200 Enterprise). Threshold mirrored in dbt var `seat_segment_threshold: 200`.

### Join keys (identity resolution)

| Link | Keys | Notes |
|------|------|-------|
| Ads → leads | `provider` + `campaign_id` + `country` ↔ UTMs + lead `country` | Geo-targeted campaigns |
| Ads → conversions | `provider` + `campaign_id` ↔ lead UTMs via `lead_id` on `crm_wins` | Wins are the conversion event; no conversion column on ads |
| Leads → funnel | `lead_id` | Stage events per lead |
| Funnel → wins | `lead_id` | Row in `crm_wins` only when terminal stage = `won` |
| Wins → product | `client_id` | Product usage starts after contract |
| Time alignment | `created_at`, `entered_at`, contract dates, `event_at` | Funnel velocity, win-to-contract lag, product retention |

## dbt project structure

```text
dbt_deskbird/
├── dbt_project.yml           # schemas: staging, intermediate, marts, metrics
├── profiles.yml              # DuckDB → ../data/warehouse.duckdb
├── models/
│   ├── sources.yml           # raw.* tables
│   ├── schema.yml            # tests + metric descriptions
│   ├── staging/              # 5 models
│   ├── intermediate/         # 4 models
│   ├── marts/                # 4 models
│   └── metrics/              # 6 models
```

### Raw → staging

- **`sources.yml`** declares the five `raw` tables in `data/warehouse.duckdb`.
- Staging models select from `{{ source('raw', 'table_name') }}` — no `dbt seed`, no CSV reads.

### Model relations in dbt

- **`ref()` / `source()`** — automatic lineage in `dbt docs`.
- **`schema.yml`** — column docs, `not_null`, `unique`, `relationships` tests on staging and core marts.
- **Example relationship test:** `fct_lead_journey.client_id` → `dim_clients.client_id` (where not null).

## Five growth metrics (assignment deliverable)

Each metric requires: definition, grain, source mart(s), and rationale for slides. **As implemented:**

| # | Metric | Category | Definition (as-built) | Primary sources | Streamlit |
|---|--------|----------|----------------------|-----------------|-----------|
| 1 | CAC | Acquisition | Ad spend ÷ won clients, grain `provider` × `campaign_id` × `month` | `int_campaign_spend`, `fct_lead_journey` | Ads |
| 2 | Lead → funnel rate | Conversion | **CRM leads ÷ ad clicks** (month × channel × country × segment) | `metric_funnel_rates` | CRM |
| 3 | Win rate | Conversion | **Wins ÷ proposals** (same grain); open pipeline excluded from denominator | `metric_funnel_rates`, `metric_win_rate` | CRM |
| 4 | Time to activation | Conversion | **Not a dedicated metrics model.** Latent fields: `won_at`, `contract_start_date` on `fct_lead_journey`. UI shows **`metric_funnel_stage_latency`** (lead creation → call/demo/proposal days by outcome) as supporting CRM metric | `fct_lead_journey` | CRM (expander) |
| 5 | Retention | Retention | **`metric_seat_utilization`** (seats_active / contracted seats, client × day). **`metric_feature_adoption_rate`** as supporting engagement metric. No WAU retention model in current codebase | `int_product_events`, `dim_clients` | Product |

## Stack

- **dbt-core** + **dbt-duckdb** — local warehouse, no cloud dependency.
- Single warehouse file: `data/warehouse.duckdb` — generator writes `raw.*`; dbt adds staging/marts/metrics; Streamlit reads marts/metrics/intermediate (gitignored; rebuilt via runbook).

## Acceptance criteria

- [x] Layered model documented for slide deck / dbt docs.
- [x] Staging → marts → metrics DAG runs with `dbt run`.
- [x] Relationship and not-null tests pass with `dbt test`.
- [x] Core KPIs in `metrics/` with definitions in `schema.yml`.
- [x] Identity resolution (join keys) described for stakeholder audience.
