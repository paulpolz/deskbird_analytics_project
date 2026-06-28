"""Funnel rates source — metrics view with inline fallback for stale warehouses."""

from __future__ import annotations

from app.connectors.duckdb import DuckDBConnector

FUNNEL_RATES_INLINE = """
WITH ad_clicks AS (
    SELECT
        month,
        channel,
        country,
        SUM(clicks) AS clicks
    FROM intermediate.int_campaign_spend
    GROUP BY 1, 2, 3
),
lead_stages AS (
    SELECT
        DATE_TRUNC('month', created_at) AS month,
        channel,
        country,
        segment,
        COUNT(DISTINCT lead_id) AS leads,
        COUNT(DISTINCT CASE WHEN call_at IS NOT NULL THEN lead_id END) AS calls,
        COUNT(DISTINCT CASE WHEN demo_at IS NOT NULL THEN lead_id END) AS demos,
        COUNT(DISTINCT CASE WHEN proposal_at IS NOT NULL THEN lead_id END) AS proposals,
        COUNT(DISTINCT CASE WHEN terminal_stage = 'won' THEN lead_id END) AS wins,
        COUNT(DISTINCT CASE WHEN terminal_stage = 'lost' AND proposal_at IS NOT NULL THEN lead_id END) AS losses
    FROM marts.fct_lead_journey
    GROUP BY 1, 2, 3, 4
)
SELECT
    l.month,
    l.channel,
    l.country,
    l.segment,
    COALESCE(a.clicks, 0) AS clicks,
    l.leads,
    l.calls,
    l.demos,
    l.proposals,
    l.wins,
    l.losses
FROM lead_stages l
LEFT JOIN ad_clicks a
    ON l.month = a.month
    AND l.channel = a.channel
    AND l.country = a.country
"""


def funnel_rates_from(db: DuckDBConnector) -> str:
  if db.table_exists("metrics", "metric_funnel_rates"):
    return "metrics.metric_funnel_rates"
  return f"({FUNNEL_RATES_INLINE})"
