"""Plotly chart helpers."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Matches Streamlit's default Plotly palette (static export cannot use theme placeholders).
COLOR_SEQUENCE = [
  "#0068c9",
  "#83c9ff",
  "#ff2b2b",
  "#ffabab",
  "#29b09d",
  "#7defa1",
  "#ff8700",
  "#ffd16a",
  "#6d3fc0",
  "#d5dae5",
]

CHART_FONT = "Berlin Type, Arial, sans-serif"


def apply_chart_style(fig: go.Figure, *, for_slides: bool = False) -> go.Figure:
  """Berlin Type + larger legend/hover fonts for slide exports."""
  base = 22 if for_slides else 13
  legend = 28 if for_slides else 15
  hover = 22 if for_slides else 14
  title = 28 if for_slides else 18
  axis_title = (base + 2) if for_slides else (base + 1)
  fig.update_layout(
    font=dict(family=CHART_FONT, size=base),
    title_font=dict(family=CHART_FONT, size=title),
    legend=dict(font=dict(family=CHART_FONT, size=legend)),
    hoverlabel=dict(font_size=hover, font_family=CHART_FONT),
  )
  fig.update_xaxes(tickfont=dict(size=base, family=CHART_FONT), title_font=dict(size=axis_title, family=CHART_FONT))
  fig.update_yaxes(tickfont=dict(size=base, family=CHART_FONT), title_font=dict(size=axis_title, family=CHART_FONT))
  fig.update_traces(textfont=dict(size=base, family=CHART_FONT))
  fig.for_each_annotation(lambda a: a.update(font=dict(size=base, family=CHART_FONT)))
  return fig


def _prepare_percent_df(df: pd.DataFrame, y: str) -> pd.DataFrame:
  out = df.copy()
  out[y] = (out[y] * 100).round(2)
  return out


def _style_percent_y(fig: go.Figure) -> go.Figure:
  fig.update_yaxes(tickformat=".2f", ticksuffix="%")
  return fig


def rolling_ctr(df: pd.DataFrame, group_col: str, window: int = 7) -> pd.DataFrame:
  parts = []
  for _, group in df.groupby(group_col, sort=False):
    rolled = group.sort_values("date").copy()
    rolled["ctr"] = (
      rolled["clicks"].rolling(window, min_periods=1).sum()
      / rolled["impressions"].rolling(window, min_periods=1).sum()
    )
    parts.append(rolled)
  return pd.concat(parts).sort_values("date")


def rolling_mean(
  df: pd.DataFrame,
  group_col: str,
  value_col: str,
  date_col: str = "day",
  window: int = 7,
) -> pd.DataFrame:
  parts = []
  for _, group in df.groupby(group_col, sort=False):
    rolled = group.sort_values(date_col).copy()
    rolled[value_col] = rolled[value_col].rolling(window, min_periods=1).mean()
    parts.append(rolled)
  return pd.concat(parts).sort_values(date_col)


def plot_cac_bar(df: pd.DataFrame, x: str, title: str = "") -> go.Figure:
  """CAC bars; channels with zero wins show a stub + spend label instead of null."""
  plot_df = df.copy().sort_values(x)
  has_wins = plot_df["wins"].fillna(0) > 0
  fig = go.Figure()

  if has_wins.any():
    won = plot_df[has_wins]
    fig.add_trace(
      go.Bar(
        x=won[x],
        y=won["cac"],
        name="CAC",
        marker_color=COLOR_SEQUENCE[0],
        text=[f"${v:,.0f}<br>({int(w)} wins)" for v, w in zip(won["cac"], won["wins"])],
        textposition="outside",
        hovertemplate="%{x}<br>CAC: $%{y:,.0f}<br>Spend: $%{customdata[0]:,.0f}<br>Wins: %{customdata[1]}<extra></extra>",
        customdata=list(zip(won["spend"], won["wins"])),
      )
    )

  no_wins = plot_df[~has_wins]
  if not no_wins.empty:
    ymax = plot_df.loc[has_wins, "cac"].max() if has_wins.any() else no_wins["spend"].max()
    stub = ymax * 0.04 if has_wins.any() else 1
    fig.add_trace(
      go.Bar(
        x=no_wins[x],
        y=[stub] * len(no_wins),
        name="No wins",
        marker_color="#D3D3D3",
        text=[f"No wins<br>${s:,.0f} spend" for s in no_wins["spend"]],
        textposition="outside",
        hovertemplate="%{x}<br>CAC: undefined<br>Spend: $%{customdata[0]:,.0f}<br>Wins: 0<extra></extra>",
        customdata=list(zip(no_wins["spend"], [0] * len(no_wins))),
      )
    )
    fig.update_yaxes(range=[0, ymax * 1.2])

  fig.update_layout(title=title, yaxis_title="CAC ($)", showlegend=False, barmode="overlay")
  return fig


def plot_bar(
  df,
  x: str,
  y: str,
  color: str | None = None,
  title: str = "",
  y_as_percent: bool = False,
  barmode: str | None = None,
) -> go.Figure:
  if y_as_percent:
    df = _prepare_percent_df(df, y)
  kwargs: dict = {"x": x, "y": y, "title": title, "color_discrete_sequence": COLOR_SEQUENCE}
  if color:
    kwargs["color"] = color
  if barmode:
    kwargs["barmode"] = barmode
  fig = px.bar(df, **kwargs)
  if y_as_percent:
    _style_percent_y(fig)
  return fig


def plot_line(
  df,
  x: str,
  y: str,
  color: str | None = None,
  title: str = "",
  y_as_percent: bool = False,
  facet_col: str | None = None,
) -> go.Figure:
  if y_as_percent:
    df = _prepare_percent_df(df, y)
  kwargs: dict = {"x": x, "y": y, "title": title, "color_discrete_sequence": COLOR_SEQUENCE}
  if color:
    kwargs["color"] = color
  if facet_col:
    kwargs["facet_col"] = facet_col
    kwargs["facet_col_wrap"] = 2
  fig = px.line(df, **kwargs)
  if y_as_percent:
    _style_percent_y(fig)
  return fig


def plot_stage_latency(
  df: pd.DataFrame,
  x: str = "outcome",
  title: str = "",
) -> go.Figure:
  labels = {
    "lead_to_call": "Lead → Call",
    "lead_to_demo": "Lead → Demo",
    "lead_to_proposal": "Lead → Proposal",
  }
  x_labels = {
    "outcome": "Outcome",
    "country": "Country",
    "segment": "Segment",
  }
  plot_df = df.copy()
  plot_df["outcome"] = pd.Categorical(
    plot_df["outcome"].str.title(),
    categories=["Win", "Loss", "Open"],
    ordered=True,
  )
  plot_df["stage"] = pd.Categorical(
    plot_df["stage"].map(labels),
    categories=["Lead → Call", "Lead → Demo", "Lead → Proposal"],
    ordered=True,
  )
  sort_cols = [x, "outcome", "stage"] if x != "outcome" else ["outcome", "stage"]
  kwargs: dict = {
    "x": x,
    "y": "avg_days",
    "color": "stage",
    "barmode": "group",
    "title": title,
    "labels": {x: x_labels.get(x, x.title()), "avg_days": "Avg days", "stage": "Stage"},
    "category_orders": {"outcome": ["Win", "Loss", "Open"]},
    "color_discrete_sequence": COLOR_SEQUENCE,
  }
  if x != "outcome":
    kwargs["facet_col"] = "outcome"
    kwargs["facet_col_wrap"] = 3
  fig = px.bar(plot_df.sort_values(sort_cols), **kwargs)
  fig.update_layout(yaxis_title="Avg days")
  return fig


def plot_funnel(stages: list[str], values: list[int | float], title: str = "") -> go.Figure:
  fig = go.Figure(
    go.Funnel(
      y=stages,
      x=values,
      textinfo="value+percent initial",
      textposition="inside",
    )
  )
  fig.update_layout(title=title, margin=dict(l=160, r=40, t=60, b=40))
  return fig


def format_rate_table(df: pd.DataFrame, dim: str) -> pd.DataFrame:
  rate_cols = [
    "lead_to_funnel_rate",
    "call_rate",
    "demo_rate",
    "proposal_rate",
    "win_rate",
    "loss_rate",
  ]
  labels = {
    "lead_to_funnel_rate": "Lead → Funnel",
    "call_rate": "Call",
    "demo_rate": "Demo",
    "proposal_rate": "Proposal",
    "win_rate": "Win",
    "loss_rate": "Loss",
  }
  out = df.rename(columns={dim: "Dimension", **labels})
  for col in labels.values():
    if col in out.columns:
      out[col] = (out[col] * 100).round(1).astype(str) + "%"
  return out[[c for c in ["Dimension", *labels.values()] if c in out.columns]]


def plot_metric_cards(metrics: list[tuple[str, str]]) -> None:
  import streamlit as st
  cols = st.columns(len(metrics))
  for col, (label, value) in zip(cols, metrics):
    col.metric(label, value)
