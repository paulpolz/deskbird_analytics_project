"""Product tab — retention KPIs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.connectors.duckdb import DuckDBConnector
from app.views.charts import plot_line, rolling_mean
from app.views.metrics import render_definition

_BUCKET_ORDER = {
  "segment": ["SMB", "Enterprise"],
  "contract_length_bucket": ["12-18 mo", "19-24 mo", "25-36 mo"],
  "seats_bucket": ["<100", "100-199", "200-399", "400+"],
  "feature_name": ["analytics", "scheduling", "integrations", "reporting"],
}


def _order_buckets(df: pd.DataFrame, col: str, date_col: str = "day") -> pd.DataFrame:
  out = df.copy()
  out[col] = pd.Categorical(out[col], categories=_BUCKET_ORDER[col], ordered=True)
  return out.sort_values([date_col, col])


def _util_query(seg: str, addon_clause: str, split_col: str | None = None) -> str:
  split_select = f", {split_col}" if split_col else ""
  split_group = f", {split_col}" if split_col else ""
  return f"""
    SELECT day{split_select}, AVG(avg_seat_utilization) utilization
    FROM metrics.metric_seat_utilization
    WHERE segment IN ({seg}) {addon_clause}
    GROUP BY day{split_group}
    ORDER BY day
  """


def _adoption_query(seg: str, addon_clause: str, split_col: str) -> str:
  return f"""
    WITH bucket_logins AS (
      SELECT DISTINCT month, {split_col}, contract_length_bucket, seats_bucket, login_users
      FROM metrics.metric_feature_adoption_rate
      WHERE segment IN ({seg}) {addon_clause}
    ),
    login_totals AS (
      SELECT month, {split_col}, SUM(login_users) AS login_users
      FROM bucket_logins
      GROUP BY 1, 2
    ),
    adopts AS (
      SELECT month, {split_col}, feature_name, SUM(adopt_users) AS adopt_users
      FROM metrics.metric_feature_adoption_rate
      WHERE segment IN ({seg}) {addon_clause}
      GROUP BY 1, 2, 3
    )
    SELECT
      a.month,
      a.{split_col},
      a.feature_name,
      a.adopt_users::DOUBLE / NULLIF(l.login_users, 0) AS adoption_rate
    FROM adopts a
    INNER JOIN login_totals l
      ON a.month = l.month AND a.{split_col} = l.{split_col}
    ORDER BY 1, 2, 3
  """


def render(db: DuckDBConnector, filters: dict, product_filters: dict) -> None:
  st.subheader("Product Usage")
  render_definition("seat_utilization")

  seg = "'SMB', 'Enterprise'"
  addon_clause = ""
  if product_filters["has_analytics_addon"] is not None:
    addon_clause = f"AND has_analytics_addon = {str(product_filters['has_analytics_addon']).lower()}"

  util = db.run_query(_util_query(seg, addon_clause, "segment"))
  if not util.empty:
    st.plotly_chart(
      plot_line(
        rolling_mean(util, "segment", "utilization"),
        "day",
        "utilization",
        "segment",
        "Seat Utilization by Segment (7-Day Rolling)",
        y_as_percent=True,
      ),
      use_container_width=True,
    )

  c1, c2 = st.columns(2)
  by_contract = db.run_query(_util_query(seg, addon_clause, "contract_length_bucket"))
  if not by_contract.empty:
    c1.plotly_chart(
      plot_line(
        rolling_mean(_order_buckets(by_contract, "contract_length_bucket"), "contract_length_bucket", "utilization"),
        "day",
        "utilization",
        "contract_length_bucket",
        "Utilization by Contract Length (7-Day Rolling)",
        y_as_percent=True,
      ),
      use_container_width=True,
    )

  by_seats = db.run_query(_util_query(seg, addon_clause, "seats_bucket"))
  if not by_seats.empty:
    c2.plotly_chart(
      plot_line(
        rolling_mean(_order_buckets(by_seats, "seats_bucket"), "seats_bucket", "utilization"),
        "day",
        "utilization",
        "seats_bucket",
        "Utilization by Contracted Seats (7-Day Rolling)",
        y_as_percent=True,
      ),
      use_container_width=True,
    )

  by_addon = db.run_query(_util_query(seg, "", "has_analytics_addon"))
  if not by_addon.empty:
    st.plotly_chart(
      plot_line(
        rolling_mean(by_addon, "has_analytics_addon", "utilization"),
        "day",
        "utilization",
        "has_analytics_addon",
        "Utilization by Analytics Addon (7-Day Rolling)",
        y_as_percent=True,
      ),
      use_container_width=True,
    )

  st.subheader("Feature Adoption")
  render_definition("feature_adoption_rate")

  by_segment = db.run_query(_adoption_query(seg, addon_clause, "segment"))
  if not by_segment.empty:
    segment_df = _order_buckets(by_segment, "segment", "month")
    segment_df = _order_buckets(segment_df, "feature_name", "month")
    st.plotly_chart(
      plot_line(
        segment_df,
        "month",
        "adoption_rate",
        "feature_name",
        "Feature Adoption Rate by Segment",
        y_as_percent=True,
        facet_col="segment",
      ),
      use_container_width=True,
    )

  c3, c4 = st.columns(2)
  by_contract_adopt = db.run_query(_adoption_query(seg, addon_clause, "contract_length_bucket"))
  if not by_contract_adopt.empty:
    contract_df = _order_buckets(by_contract_adopt, "contract_length_bucket", "month")
    contract_df = _order_buckets(contract_df, "feature_name", "month")
    c3.plotly_chart(
      plot_line(
        contract_df,
        "month",
        "adoption_rate",
        "feature_name",
        "Feature Adoption by Contract Length",
        y_as_percent=True,
        facet_col="contract_length_bucket",
      ),
      use_container_width=True,
    )

  by_seats_adopt = db.run_query(_adoption_query(seg, addon_clause, "seats_bucket"))
  if not by_seats_adopt.empty:
    seats_df = _order_buckets(by_seats_adopt, "seats_bucket", "month")
    seats_df = _order_buckets(seats_df, "feature_name", "month")
    c4.plotly_chart(
      plot_line(
        seats_df,
        "month",
        "adoption_rate",
        "feature_name",
        "Feature Adoption by Contracted Seats",
        y_as_percent=True,
        facet_col="seats_bucket",
      ),
      use_container_width=True,
    )
