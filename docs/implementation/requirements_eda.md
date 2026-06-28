# Requirements: EDA & Delivery

Scope: runbook and Streamlit dashboard with KPI charts. The repo ships **code only**; reviewers generate data and the DuckDB warehouse locally (nothing under `data/` is committed — see [README.md](README.md)).

Insights and slide deck are a separate next step — see [requirements_insights.md](requirements_insights.md).

## End-to-end flow

```text
config/config.py + generate_data.py  →  raw tables (DuckDB)  →  dbt  →  Streamlit
```

All steps share **`data/warehouse.duckdb`**. Streamlit queries **staging-derived schemas only** (`intermediate`, `marts`, `metrics`) — never `raw.*`.

## Runbook

Documented in root `README.md`. Reviewers should reproduce findings in order:

### 1. Environment setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Or: `python3.11 run.py setup`

### 2. Generate raw data (load into DuckDB)

```bash
python scripts/generate_data.py
# or: python run.py generate
```

Creates schema `raw` and five tables in `data/warehouse.duckdb`.

### 3. Run dbt pipeline

```bash
cd dbt_deskbird
DBT_PROFILES_DIR=. dbt run
DBT_PROFILES_DIR=. dbt test
DBT_PROFILES_DIR=. dbt docs generate   # optional lineage
```

Or: `python run.py dbt` (runs `dbt run` + `dbt test` with `DBT_PROFILES_DIR` and `WAREHOUSE_PATH` set).

**Warehouse:** DuckDB at `data/warehouse.duckdb` (configured in `profiles.yml`).

### 4. Launch Streamlit

```bash
streamlit run app/app.py
# or: python run.py app
```

### Makefile / run.py

```bash
make all      # setup (if needed), generate, dbt
make app      # streamlit
```

Equivalent: `python3.11 run.py all` then `python3.11 run.py app`.

### Gitignore (required)

All generated/runtime artifacts stay out of GitHub:

```gitignore
data/warehouse.duckdb
*.duckdb
.venv/
```

Clean clone → runbook → full pipeline. No data files in the repo.

## Streamlit dashboard

| Item | Spec |
|------|------|
| Entry point | `app/app.py` — page config, global sidebar filters, tab routing |
| Data access | `app/connectors/duckdb.py` — read-only connection to `data/warehouse.duckdb` |
| Purpose | KPI visualization across Ads, CRM, and Product domains |

### App structure (as-built)

Split by responsibility. **Repeatable logic lives in functions** — no copy-pasted Streamlit blocks across tabs.

```text
app/
├── app.py                  # entry: tabs, global filters, delegate to tabs
├── connectors/
│   └── duckdb.py           # DuckDBConnector — run_query(), table_exists()
├── queries/
│   └── funnel_rates.py     # metric_funnel_rates source + inline fallback
├── views/
│   ├── filters.py          # render_global_filters(), render_crm_filters(), render_product_filters()
│   ├── charts.py           # plot_bar, plot_line, plot_funnel, rolling helpers
│   └── metrics.py          # METRIC_DEFS, render_definition(), render_funnel_definitions()
└── tabs/
    ├── ads.py              # render(db, filters)
    ├── crm.py              # render(db, filters, crm_filters)
    └── product.py          # render(db, filters, product_filters)
```

| Layer | Role |
|-------|------|
| **`connectors/`** | DuckDB I/O only — parameterized SQL → `pandas` DataFrames. Cached read-only connection. |
| **`queries/`** | SQL source helpers (e.g. funnel rates with stale-warehouse fallback). |
| **`views/`** | Reusable UI — filters, Plotly charts, metric definition captions. |
| **`tabs/`** | One module per domain tab; composes connectors + views. |
| **`app.py`** | Streamlit shell only — sidebar, `st.tabs`, delegate to `tabs.*.render()`. |

**Conventions**

- Global filters passed from `app.py`; CRM and Product tabs add sidebar filters via dedicated render functions.
- SQL lives in tab modules or `queries/` — not scattered inline without structure.
- Chart styling defaults in `views/charts.py`.

### Tabs (domain split)

| Tab | Charts / tables | dbt sources |
|-----|-----------------|-------------|
| **Ads** | Daily spend & rolling CTR; **CAC by channel** (bar + spend/wins/seats table) and CAC by country; spend share | `intermediate.int_campaign_spend`, `metrics.metric_cac`, `marts.dim_clients` |
| **CRM** | Funnel chart (Ad clicks → CRM leads → Calls → Demos → Proposals → Wins); step conversion rate tables by channel/country/segment; stage latency by outcome (expander) | `metrics.metric_funnel_rates` (via `queries/funnel_rates.py`), `metrics.metric_funnel_stage_latency` |
| **Product** | 7-day rolling seat utilization by segment, contract length, seats bucket, analytics addon; feature adoption rate by segment and buckets | `metrics.metric_seat_utilization`, `metrics.metric_feature_adoption_rate` |

Cross-domain funnel view lives on the **CRM** tab (clicks through wins in one chart).

### Filters (as-built)

| Scope | Filters |
|-------|---------|
| **Global (sidebar)** | Date range, `channel` (google/linkedin/meta), `country` (DE/AT/CH/UK/US) |
| **CRM (sidebar)** | `segment` (SMB/Enterprise), funnel stage visibility (multiselect for chart) |
| **Product (sidebar)** | Analytics addon (All / Yes / No) |

Not implemented in UI: `provider`, `campaign_id`, `stage`, `utm_campaign`, `feature_name` filters (available in warehouse for extension).

### UX notes

- Plotly charts throughout; 7-day rolling means on rate/utilization time series.
- Metric definitions inline via `views/metrics.py` (aligned with dbt `schema.yml` descriptions).
- App caption states conversions = CRM wins via UTMs.

### Dependencies

In root `requirements.txt`:

- `streamlit`, `plotly`, `pandas`, `duckdb`

Exploration deliverable is **Streamlit** (primary). An optional `analyse.ipynb` may exist for ad-hoc work but is not part of the reviewer runbook.

## Repo structure (delivery)

```text
deskbird_hometask/
├── README.md
├── Makefile
├── run.py
├── requirements.txt
├── config/config.py
├── scripts/generate_data.py
├── data/warehouse.duckdb     # gitignored
├── dbt_deskbird/
├── app/
│   ├── app.py
│   ├── connectors/
│   ├── queries/
│   ├── views/
│   └── tabs/
└── docs/implementation/
```

## Acceptance criteria

- [x] Clean `git clone` + runbook reproduces warehouse and dashboard.
- [x] Streamlit loads without querying `raw.*` directly.
- [x] Five assignment metrics covered across tabs (time to activation via stage latency + latent journey fields; retention via seat utilization).
- [x] Domain KPIs from [requirements_kpis.md](requirements_kpis.md) charted on the correct tabs where implemented.
- [x] `dbt test` passes before demo / submission.
