"""CRM tab — funnel chart and rate comparison tables."""

from __future__ import annotations

import streamlit as st

from app.connectors.duckdb import DuckDBConnector
from app.queries.funnel_rates import funnel_rates_from
from app.views.charts import format_rate_table, plot_funnel, plot_stage_latency
from app.views.metrics import FUNNEL_STAGE_LABELS, render_definition, render_funnel_definitions

FUNNEL_STAGES = list(zip(FUNNEL_STAGE_LABELS, ["clicks", "leads", "calls", "demos", "proposals", "wins"]))

RATE_COLS = [
  ("lead_to_funnel_rate", "leads", "clicks"),
  ("call_rate", "calls", "leads"),
  ("demo_rate", "demos", "calls"),
  ("proposal_rate", "proposals", "demos"),
  ("win_rate", "wins", "proposals"),
  ("loss_rate", "losses", "proposals"),
]


def _where(filters: dict, crm_filters: dict) -> str:
  ch = ",".join(f"'{c}'" for c in filters["channel"])
  co = ",".join(f"'{c}'" for c in filters["country"])
  seg = ",".join(f"'{s}'" for s in crm_filters["segment"])
  return (
    f"month BETWEEN '{filters['start']}' AND '{filters['end']}'"
    f" AND channel IN ({ch}) AND country IN ({co}) AND segment IN ({seg})"
  )


def _totals_query(db: DuckDBConnector, w: str) -> str:
  cols = ", ".join(f"SUM({c}) AS {c}" for _, c in FUNNEL_STAGES)
  return f"SELECT {cols} FROM {funnel_rates_from(db)} WHERE {w}"


def _rates_by_query(db: DuckDBConnector, w: str, split: str) -> str:
  rate_exprs = ",\n           ".join(
    f"SUM({num})::DOUBLE / NULLIF(SUM({den}), 0) AS {name}" for name, num, den in RATE_COLS
  )
  return f"""
    SELECT {split},
           {rate_exprs}
    FROM {funnel_rates_from(db)}
    WHERE {w}
    GROUP BY 1
    ORDER BY 1
  """


def _selected_stages(crm_filters: dict) -> list[tuple[str, str]]:
  selected = set(crm_filters.get("stages", FUNNEL_STAGE_LABELS))
  return [(label, col) for label, col in FUNNEL_STAGES if label in selected]


def _latency_query(ch: str, co: str, seg: str, split: str | None = None) -> str:
  split_select = f", {split}" if split else ""
  group_by = f"outcome, stage{split_select}"
  return f"""
    SELECT {group_by}, AVG(stage_latency_days) AS avg_days, COUNT(*) AS leads
    FROM (
      SELECT outcome, 'lead_to_call' AS stage, lead_to_call_days AS stage_latency_days{split_select}
      FROM metrics.metric_funnel_stage_latency
      WHERE lead_to_call_days IS NOT NULL
        AND channel IN ({ch}) AND country IN ({co}) AND segment IN ({seg})
      UNION ALL
      SELECT outcome, 'lead_to_demo' AS stage, lead_to_demo_days AS stage_latency_days{split_select}
      FROM metrics.metric_funnel_stage_latency
      WHERE lead_to_demo_days IS NOT NULL
        AND channel IN ({ch}) AND country IN ({co}) AND segment IN ({seg})
      UNION ALL
      SELECT outcome, 'lead_to_proposal' AS stage, lead_to_proposal_days AS stage_latency_days{split_select}
      FROM metrics.metric_funnel_stage_latency
      WHERE lead_to_proposal_days IS NOT NULL
        AND channel IN ({ch}) AND country IN ({co}) AND segment IN ({seg})
    )
    GROUP BY {group_by}
    ORDER BY {group_by}
  """


def render(db: DuckDBConnector, filters: dict, crm_filters: dict) -> None:
  st.subheader("CRM Funnel")
  render_funnel_definitions()
  st.caption(
    "End-to-end conversion from ad click through CRM stages. "
    "Rates compare each step to the prior stage volume."
  )

  w = _where(filters, crm_filters)
  totals = db.run_query(_totals_query(db, w))

  if totals.empty:
    st.info("No funnel data for the selected filters.")
    return

  visible = _selected_stages(crm_filters)
  if not visible:
    st.warning("Select at least one funnel stage in the sidebar.")
    return

  row = totals.iloc[0]
  stages = [label for label, _ in visible]
  values = [int(row[col]) for _, col in visible]

  st.plotly_chart(
    plot_funnel(stages, values, "Total Funnel (filtered period)"),
    use_container_width=True,
  )

  st.markdown("#### Step conversion rates by dimension")
  for split, label in [("channel", "Channel"), ("country", "Country"), ("segment", "Segment")]:
    rates = db.run_query(_rates_by_query(db, w, split))
    if not rates.empty:
      st.markdown(f"**{label}**")
      st.dataframe(format_rate_table(rates, split), use_container_width=True, hide_index=True)

  with st.expander("Supporting metrics"):
    render_definition("funnel_stage_latency")
    ch = ",".join(f"'{c}'" for c in filters["channel"])
    co = ",".join(f"'{c}'" for c in filters["country"])
    seg = ",".join(f"'{s}'" for s in crm_filters["segment"])

    latency_caption = (
      "Open = leads still in pipeline. Each stage average includes only leads that reached that stage."
    )
    for split, label in [
      (None, "Funnel Stage Latency by Outcome"),
      ("country", "Funnel Stage Latency by Country"),
      ("segment", "Funnel Stage Latency by Segment"),
    ]:
      latency = db.run_query(_latency_query(ch, co, seg, split))
      if latency.empty:
        continue
      st.plotly_chart(
        plot_stage_latency(latency, x=split or "outcome", title=label),
        use_container_width=True,
      )
    st.caption(latency_caption)
