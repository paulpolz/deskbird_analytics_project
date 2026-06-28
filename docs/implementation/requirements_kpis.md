# Requirements: KPIs & Granularity

Scope: metric definitions, grains, dimension splits, and measurement logic for the Growth analytics stack. KPI models live in `dbt_deskbird/models/metrics/` and read only from marts/intermediate (see [requirements_data_model.md](requirements_data_model.md)).

## Granularity tiers

| Tier | Use case | Typical time grain | Entity grain |
|------|----------|-------------------|--------------|
| **Operational** | Campaign / sales ops tuning | Daily, weekly | Campaign × day, lead, stage event |
| **Tactical** | Channel / market reviews | Weekly, monthly | Channel, country, segment |
| **Strategic** | Board / leadership scorecards | Monthly, quarterly | All-up, segment, market |
| **Cohort** | Funnel velocity, activation, retention | Event-relative (day 0 = lead created / contract start) | Lead cohort, client cohort |

**Rule:** store facts at the finest useful grain in marts; aggregate in metrics layer or Streamlit. Pre-aggregate in `metrics/` when the grain is fixed and reused.

---

## Dimension vocabulary (all domains)

| Dimension | Source | Values / notes |
|-----------|--------|----------------|
| `date` / `day` | Ads, product | Calendar day; roll up to week / month |
| `month` | Metrics roll-ups | `date_trunc('month', …)` |
| `channel` | Ads, leads | `google`, `linkedin`, `meta` (1:1 with provider) |
| `provider` | Ads, leads | Same as channel; join key to UTMs |
| `campaign_id` | Ads, leads | Scoped to `provider`; format `{provider}_{country}_{nnn}` |
| `country` | Ads, leads | `DE`, `AT`, `CH`, `UK`, `US` |
| `market` | Wins | Same country codes; must match lead `country` |
| `segment` | Leads (raw + marts) | `SMB` / `Enterprise` at lead creation; seats at win follow segment ranges |
| `stage` | Funnel | `call` → `demo` → `proposal` → `won` \| `lost` |
| `outcome` | `fct_lead_journey` | `win`, `loss`, `open` (derived from terminal stage) |
| `client_id` | Wins, product | Won customers only for product domain |
| `event_type` | Product | `login`, `feature_adopted`, `seat_snapshot` |
| `feature_name` | Product | `analytics`, `scheduling`, `integrations`, `reporting` |
| `has_analytics_addon` | Wins / dbt | Boolean from `additional_services` containing `analytics` |
| `contract_length_bucket` | Metrics | `12-18 mo`, `19-24 mo`, `25-36 mo` |
| `seats_bucket` | Metrics | `<100`, `100-199`, `200-399`, `400+` |

---

## dbt metric models (as-built)

| Model | Grain | Domain | In Streamlit |
|-------|-------|--------|--------------|
| `metric_cac` | `provider` × `campaign_id` × `country` × `month` | Cross (Ads→CRM) | Ads |
| `metric_funnel_rates` | `month` × `channel` × `country` × `segment` | Cross + CRM | CRM |
| `metric_win_rate` | same (where `proposals > 0`) | CRM | CRM (via funnel rates) |
| `metric_funnel_stage_latency` | lead (`lead_id`) | CRM | CRM (expander) |
| `metric_seat_utilization` | client × `day` | Product | Product |
| `metric_feature_adoption_rate` | `month` × segment × buckets × `feature_name` | Product | Product |

**Not in current codebase** (may exist as stale views until warehouse rebuild): `metric_lead_to_funnel_rate`, `metric_time_to_activation`, `metric_wau_retention`. Functionality consolidated into `metric_funnel_rates` and `metric_funnel_stage_latency`.

---

## Assignment deliverable: 5 core growth metrics

### 1. Customer Acquisition Cost (CAC)

| Attribute | Spec |
|-----------|------|
| **Category** | Acquisition (cross-domain: Ads → CRM) |
| **Definition** | Total ad spend ÷ count of won clients in the same campaign × month slice |
| **Formula** | `total_spend / won_clients` where wins attributed via lead UTMs |
| **Primary grain** | `provider` × `campaign_id` × `country` × `month` |
| **Sources** | `int_campaign_spend`, `fct_lead_journey` |
| **Attribution** | Win `lead_id` → lead `provider` + `campaign_id` + `country` ↔ ads spend |
| **Dimension splits** | `campaign_id`, `provider`, `channel`, `country`; segment available via journey join |
| **Streamlit** | Ads tab — CAC bar chart + summary table by channel (spend, wins, avg seats) |
| **Rationale** | Standard acquisition efficiency; compare dollar CAC with deal size (seats) |

**Observed channel ranking (full warehouse, filter-dependent):**

| Channel | Spend | Wins | CAC | Avg seats | Read |
|---------|-------|------|-----|-----------|------|
| Google | ~$381k | ~257 | ~$1.5k | ~295 (SMB ~105, Ent ~516) | Volume SMB + Enterprise; lowest CAC |
| LinkedIn | ~$1.22M | ~43 | ~$28k | ~293 (Ent ~505) | High CAC, large deals — viable Enterprise play |
| Meta | ~$230k | **2** | ~$115k | ~138 (SMB) | Strong CTR/leads; near-zero close rate → worst CAC |

Meta wins in current data: 1 each in AT and CH (Jul 2025). Channels with zero wins show undefined CAC in the chart.

---

### 2. Lead → Funnel Rate

| Attribute | Spec |
|-----------|------|
| **Category** | Conversion (Ads → CRM) |
| **Definition (as-built)** | **CRM leads created ÷ ad clicks** in the same month × channel × country |
| **Formula** | `leads / clicks` from `metric_funnel_rates` |
| **Note** | Original spec used “leads reaching `call` / all leads”; implementation uses full top-of-funnel click→lead ratio for the CRM funnel chart |
| **Primary grain** | `month` × `channel` × `country` × `segment` |
| **Sources** | `metric_funnel_rates` (`int_campaign_spend` + `fct_lead_journey`) |
| **Streamlit** | CRM tab — funnel chart + rate tables (`lead_to_funnel_rate` row) |
| **Rationale** | Connects paid volume to CRM capture |

**Related sub-metrics in `metric_funnel_rates`:**

| Column | Formula |
|--------|---------|
| `call_rate` | `calls / leads` |
| `demo_rate` | `demos / calls` |
| `proposal_rate` | `proposals / demos` |
| `win_rate` | `wins / proposals` |
| `loss_rate` | `losses / proposals` (losses = terminal `lost` after proposal) |

---

### 3. Win Rate

| Attribute | Spec |
|-----------|------|
| **Category** | Conversion (CRM) |
| **Definition (as-built)** | **Wins ÷ proposals** among leads that reached proposal |
| **Formula** | `wins / proposals` — open pipeline excluded (no proposal yet) |
| **Primary grain** | `month` × `channel` × `country` × `segment` |
| **Sources** | `metric_funnel_rates`, `metric_win_rate` |
| **Dimension splits** | `channel`, `country`, `segment` |
| **Streamlit** | CRM tab — rate comparison tables |
| **Rationale** | Sales effectiveness; Meta shows ~2 wins vs hundreds on Google despite high lead volume; DE/AT/CH friction visible here |

---

### 4. Time to Activation

| Attribute | Spec |
|-----------|------|
| **Category** | Conversion (CRM) |
| **Definition (assignment)** | Days from **`won` stage** to **`contract_start_date`** |
| **As-built** | **No dedicated metrics model.** Fields available on `fct_lead_journey`: `won_at`, `contract_start_date`. Computable as `date_diff('day', won_at, contract_start_date)`. |
| **UI substitute** | `metric_funnel_stage_latency` — avg days from lead creation to call / demo / proposal, grouped by `outcome` (win, loss, open) |
| **Streamlit** | CRM tab expander “Supporting metrics” — latency bar chart |
| **Rationale** | Assignment metric latent in mart; stage latency supports funnel velocity stories (demo SLA, market friction) |

---

### 5. Retention

| Attribute | Spec |
|-----------|------|
| **Category** | Retention (Product) |
| **As-built primary** | **`metric_seat_utilization`** — `seats_active / contracted seats`, grain client × day; buckets for contract length and seat count |
| **Supporting** | **`metric_feature_adoption_rate`** — distinct adopting users / distinct login users per month × feature |
| **Not implemented** | `metric_wau_retention` (week-over-week login retention) — not in current codebase or Streamlit |
| **Sources** | `int_product_events`, `dim_clients` |
| **Dimension splits** | `segment`, `market`, `has_analytics_addon`, `contract_length_bucket`, `seats_bucket`, `feature_name` |
| **Streamlit** | Product tab |
| **Rationale** | Utilization + feature adoption proxy engagement; analytics addon lift visible in utilization by addon chart |

---

## Domain: Paid Ads

**Base fact grain:** `provider` × `campaign_id` × `date` (`raw.ads_campaign_daily` → `int_campaign_spend`)

### Volume & delivery KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| Impressions | campaign × day | `SUM(impressions)` | Computable from `int_campaign_spend`; not charted |
| Clicks | campaign × day | `SUM(clicks)` | Used in CRM funnel (via `metric_funnel_rates`) |
| Spend | campaign × day | `SUM(spend)` | Ads tab |
| CTR | campaign × day | `clicks / impressions` | Ads tab (7-day rolling) |
| CPC | campaign × day | `spend / clicks` | Computable; not charted |
| CPM | campaign × day | `spend / impressions × 1000` | Computable; not charted |

### Efficiency KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| Spend share by channel | filtered period | `channel spend / total` | Ads tab |
| Spend share by country | filtered period | `country spend / total` | Via spend-by-country chart |
| CAC | campaign × month | `metric_cac` | Ads tab |

### Cross-domain (Ads + CRM)

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| Lead → funnel rate | month × channel × country × segment | `leads / clicks` | CRM tab |
| CAC | campaign × month | spend ÷ won clients | Ads tab |
| CPL | month × channel | `spend / leads` | Computable from funnel rates; not separate chart |
| Cost per funnel entry | month × channel | `spend / calls` | Computable; not separate chart |

---

## Domain: CRM (Pipeline)

**Base grains:** lead (`fct_lead_journey`), stage pivot (`int_funnel_events`), client (`dim_clients`)

### Volume KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| New leads | month | `COUNT(lead_id)` | Funnel chart (`leads` stage) |
| Funnel entries (calls) | month | Leads with `call_at` | Funnel chart |
| Open pipeline | lead | `outcome = 'open'` | In latency chart |
| Won clients | month | Terminal `won` | Funnel chart + CAC denominator |
| Lost after proposal | month | `losses` in `metric_funnel_rates` | Rate tables |

### Conversion KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| Lead → funnel rate | month | `leads / clicks` | CRM rate tables |
| Stage conversion rates | month | `call_rate` … `win_rate` | CRM rate tables |
| Win rate | month | `wins / proposals` | CRM rate tables |
| Meta drop-off | month | Strong `demo_rate` (~37%) but very low `proposal_rate` (~7%) and `win_rate` (~2% of proposals → **2 total wins**) | Visible in rate tables |

### Velocity KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| Lead → call / demo / proposal days | lead | `lead_to_*_days` on journey / latency metric | CRM expander |
| Call → demo cycle time | lead | `call_to_demo_days` on `int_funnel_events` | Mart only |
| **Demo SLA breach** | lead | `demo_sla_breached` on `int_funnel_events` | Mart only (story #5) |
| Sales cycle length | won client | `won_at - created_at` | Computable from `fct_lead_journey`; not charted |
| Time to activation | won client | `contract_start_date - won_at` | Mart only; not charted |

### Deal quality KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| Avg contracted seats | month | `AVG(seats)` | Computable from `dim_clients`; not charted |
| Avg contract length | month | `AVG(contract_length_months)` | Used in utilization buckets |
| Analytics attach rate | month | `% has_analytics_addon` | Product filter + utilization-by-addon chart |
| Enterprise win share | month | Enterprise wins / all wins | Computable; not charted |

---

## Domain: Product (Usage)

**Base grain:** event (`int_product_events`); population = won clients only

### Engagement KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| DAU / WAU / MAU | day/week/month | Distinct `user_id` with `login` | Computable; not charted |
| Logins per client | week | login events / clients | Embedded in generator; not charted |
| Feature adoption rate | month × feature | `metric_feature_adoption_rate` | Product tab |
| WAU retention | week cohort | Active W and W+1 / active W | **Not implemented** |

### Utilization KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| Seat utilization | client × day | `metric_seat_utilization` | Product tab (7-day rolling) |
| Utilization by segment / contract / seats / addon | client × day | Same metric, grouped | Product tab |
| Under-utilized clients | week | utilization < 50% | Computable; not charted |
| Zero-usage clients | week | no login in 7 days | Story #6 in data; not charted |

### Activation & retention KPIs

| KPI | Grain | Formula | In app |
|-----|-------|---------|--------|
| Time to activation | client | `contract_start - won_at` | Mart only |
| Time to first feature adoption | client | first `feature_adopted` - contract_start | Computable; not charted |
| 30-day activation rate | win cohort | login + feature in first 30d | Story #6 in generator; not charted |
| Usage decay slope | client × tenure | login drop after day 30 | Story #6 in generator; visible via utilization trends |
| Analytics addon utilization lift | month × segment | avg util (addon=yes) vs no | Product tab (utilization by addon) |

---

## Cross-domain funnel (full journey)

Built from `metric_funnel_rates` + CRM funnel chart.

| Stage | Metric | In app |
|-------|--------|--------|
| Awareness | Clicks (proxy for ad engagement) | CRM funnel |
| Interest | CRM leads | CRM funnel |
| Qualification | Calls | CRM funnel |
| Evaluation | Demos, proposals | CRM funnel |
| Close | Wins, win rate | CRM funnel + rate tables |
| Onboard | Time to activation | Mart only |
| Retain | Seat utilization, feature adoption | Product tab |

**Funnel chain (CRM tab):**

```text
Ad clicks → CRM leads → Calls → Demos → Proposals → Wins
```

Step rates in rate tables compare each stage to the prior stage volume.

---

## Streamlit mapping

| Dashboard tab | Primary KPIs | Core assignment metrics |
|---------------|--------------|-------------------------|
| **Ads** | Spend, CTR (rolling), spend share, CAC by channel (with wins + avg seats table) | CAC |
| **CRM** | Full funnel chart, step conversion tables, stage latency | Lead → funnel rate, win rate; stage latency (supports activation story) |
| **Product** | Seat utilization (segment, contract, seats, addon), feature adoption | Seat utilization (retention #5) |

**Global filters:** date range, `channel`, `country`.  
**CRM filters:** `segment`, funnel stage visibility.  
**Product filters:** analytics addon (All/Yes/No).

---

## Embedded story → KPI mapping

| Story | KPIs to inspect |
|-------|-----------------|
| LinkedIn = Enterprise, Google = SMB | CAC, win rate, avg seats (mart), spend by channel |
| Meta underperforms on close | High CTR/leads but `proposal_rate`, `win_rate` by channel (2 wins total in current warehouse) |
| DE/AT/CH vs UK friction | Win rate, `lead_to_proposal_days` by country/outcome |
| Analytics addon retention | Seat utilization + feature adoption by `has_analytics_addon` × segment |
| Demo SLA (14 days) | `demo_sla_breached`, call→demo latency by outcome |
| Usage → churn | Low utilization trends, addon lift; generator embeds decay cohort |

---

## Acceptance criteria

- [x] Core metrics in `metrics/` with definition and grain in `schema.yml`.
- [x] Domain KPIs computable from marts without reading raw tables.
- [x] Dimension splits documented for ads, CRM, and product.
- [x] Streamlit Ads / CRM / Product tabs expose implemented KPIs and assignment metrics (with noted gaps: WAU retention, dedicated time-to-activation chart).
