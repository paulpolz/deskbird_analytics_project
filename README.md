# Deskbird Growth Analytics

Reproducible pipeline: generate fictional data → model in dbt → explore KPIs in Streamlit.

```text
generate_data.py  →  warehouse.duckdb  →  dbt  →  Streamlit
```

**Data design:** Ad platforms report impressions, clicks, spend only. **Conversions = CRM wins**, attributed to campaigns via `lead_id` → UTMs.

## Quickstart

```bash
python3.11 run.py all      # setup venv, generate data, run dbt
python3.11 run.py app      # launch Streamlit dashboard
```

Or via Makefile: `make all` then `make app`.

## Manual runbook

### 1. Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```



### 2. Generate raw data

```bash
python scripts/generate_data.py
```

Creates `raw.*` tables in `data/warehouse.duckdb` (gitignored).

### 3. Run dbt

```bash
cd dbt_deskbird
DBT_PROFILES_DIR=. dbt run
DBT_PROFILES_DIR=. dbt test
```

Builds `staging`, `intermediate`, `marts`, `metrics` schemas in the same warehouse.

### 4. Launch dashboard

```bash
streamlit run app/app.py
```

Streamlit reads **marts/metrics only** — never `raw.`*.

## Project structure

```text
config/config.py       # central params (seeds, dimensions, story knobs)
scripts/generate_data.py   # Faker data generator
dbt_deskbird/          # dbt models (staging → metrics)
app/                   # Streamlit dashboard
run.py                 # centralized runner
```



## Five core metrics


| Metric             | Model                       | Tab     |
| ------------------ | --------------------------- | ------- |
| CAC                | `metric_cac`                | Ads     |
| Lead → funnel rate | `metric_funnel_rates`       | CRM     |
| Win rate           | `metric_funnel_rates`       | CRM     |
| Time to activation | `metric_time_to_activation` | CRM     |
| Seat utilization   | `metric_seat_utilization`   | Product |


See `docs/` for full requirements.