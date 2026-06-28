"""Ads tab — acquisition KPIs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.connectors.duckdb import DuckDBConnector
from app.views.charts import plot_bar, plot_cac_bar, plot_line, rolling_ctr
from app.views.metrics import render_definition


def _where(filters: dict, extra: str = "") -> str:
  ch = ",".join(f"'{c}'" for c in filters["channel"])
  co = ",".join(f"'{c}'" for c in filters["country"])
  clause = (
    f"channel IN ({ch}) AND country IN ({co})"
    f" AND date BETWEEN '{filters['start']}' AND '{filters['end']}'"
  )
  if extra:
    clause += f" AND {extra}"
  return clause


def _delivery_query(w: str, split: str) -> str:
  return f"""
    SELECT date, {split},
           SUM(impressions) impressions, SUM(clicks) clicks,
           SUM(spend) spend, SUM(clicks)::DOUBLE / NULLIF(SUM(impressions), 0) ctr
    FROM intermediate.int_campaign_spend
    WHERE {w}
    GROUP BY date, {split}
    ORDER BY 1
  """


def _cac_where(filters: dict) -> str:
  ch = ",".join(f"'{c}'" for c in filters["channel"])
  co = ",".join(f"'{c}'" for c in filters["country"])
  return (
    f"channel IN ({ch}) AND country IN ({co})"
    f" AND month BETWEEN '{filters['start']}' AND '{filters['end']}'"
  )


def _cac_query(w: str, split: str) -> str:
  return f"""
    SELECT {split},
           SUM(total_spend) spend, SUM(won_clients) wins,
           SUM(total_spend) / NULLIF(SUM(won_clients), 0) AS cac
    FROM metrics.metric_cac
    WHERE {w}
    GROUP BY {split}
    ORDER BY cac DESC NULLS LAST
  """


def _wins_by_channel_segment_query(filters: dict) -> str:
  ch = ",".join(f"'{c}'" for c in filters["channel"])
  co = ",".join(f"'{c}'" for c in filters["country"])
  return f"""
    SELECT channel, segment, COUNT(DISTINCT client_id) AS wins
    FROM marts.fct_lead_journey
    WHERE terminal_stage = 'won'
      AND channel IN ({ch}) AND country IN ({co})
      AND won_at BETWEEN '{filters['start']}' AND '{filters['end']}'
    GROUP BY 1, 2
    ORDER BY 1, 2
  """


def _cac_channel_detail_query(w: str, start, end) -> str:
  return f"""
    WITH cac AS (
      SELECT channel,
             SUM(total_spend) spend,
             SUM(won_clients) wins,
             SUM(total_spend) / NULLIF(SUM(won_clients), 0) AS cac
      FROM metrics.metric_cac
      WHERE {w}
      GROUP BY 1
    ),
    seats AS (
      SELECT channel, ROUND(AVG(seats), 0) AS avg_seats
      FROM marts.dim_clients
      WHERE contract_start_date BETWEEN '{start}' AND '{end}'
      GROUP BY 1
    )
    SELECT c.channel, c.spend, c.wins, c.cac, s.avg_seats
    FROM cac c
    LEFT JOIN seats s USING (channel)
    ORDER BY c.cac DESC NULLS FIRST
  """


def render(db: DuckDBConnector, filters: dict) -> None:
  st.subheader("Paid Ads")
  render_definition("cac")

  w = _where(filters)

  delivery = db.run_query(_delivery_query(w, "channel"))
  if not delivery.empty:
    c1, c2 = st.columns(2)
    c1.plotly_chart(plot_bar(delivery, "date", "spend", "channel", "Daily Spend by Channel"), use_container_width=True)
    c2.plotly_chart(
      plot_line(rolling_ctr(delivery, "channel"), "date", "ctr", "channel", "CTR by Channel (7-Day Rolling)", y_as_percent=True),
      use_container_width=True,
    )

    by_country = db.run_query(_delivery_query(w, "country"))
    c3, c4 = st.columns(2)
    c3.plotly_chart(plot_bar(by_country, "date", "spend", "country", "Daily Spend by Country"), use_container_width=True)
    c4.plotly_chart(
      plot_line(rolling_ctr(by_country, "country"), "date", "ctr", "country", "CTR by Country (7-Day Rolling)", y_as_percent=True),
      use_container_width=True,
    )

  cac_w = _cac_where(filters)
  cac_by_country = db.run_query(_cac_query(cac_w, "country"))
  if not cac_by_country.empty:
    st.plotly_chart(plot_bar(cac_by_country, "country", "cac", title="CAC by Country"), use_container_width=True)
    
    cac_by_channel = db.run_query(_cac_channel_detail_query(cac_w, filters["start"], filters["end"]))
    if not cac_by_channel.empty:
      st.plotly_chart(
        plot_cac_bar(cac_by_channel, "channel", title="CAC by Channel"),
        use_container_width=True,
      )
      display = cac_by_channel.copy()
      display["spend"] = display["spend"].map("${:,.0f}".format)
      display["cac"] = display["cac"].apply(lambda v: f"${v:,.0f}" if pd.notna(v) else "—")
      display["wins"] = display["wins"].astype(int)
      display["avg_seats"] = display["avg_seats"].apply(lambda v: f"{int(v):,}" if pd.notna(v) else "—")
      display = display.rename(columns={
        "channel": "Channel",
        "spend": "Spend",
        "wins": "Wins",
        "cac": "CAC",
        "avg_seats": "Avg seats",
      })
      st.dataframe(display, use_container_width=True, hide_index=True)

  wins_by_segment = db.run_query(_wins_by_channel_segment_query(filters))
  if not wins_by_segment.empty:
    st.plotly_chart(
      plot_bar(
        wins_by_segment,
        "channel",
        "wins",
        color="segment",
        title="Wins by Channel",
        barmode="group",
      ),
      use_container_width=True,
    )
