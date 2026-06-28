"""Metric definition widgets."""

from __future__ import annotations

import streamlit as st

FUNNEL_STAGE_LABELS = [
  "Ad clicks",
  "CRM leads",
  "Calls",
  "Demos",
  "Proposals",
  "Wins",
]

METRIC_DEFS = {
  "cac": "Ad spend ÷ won clients, grain campaign × month. Wins attributed via lead UTMs. Compare channel CAC with avg seats — LinkedIn’s higher CAC can fit Enterprise deals; Meta’s reflects ~2 wins on ~$230k spend.",
  "lead_to_funnel_rate": "CRM leads created ÷ ad clicks.",
  "call_rate": "Leads reaching call stage ÷ CRM leads created.",
  "demo_rate": "Leads reaching demo ÷ leads with call.",
  "proposal_rate": "Leads reaching proposal ÷ leads with demo.",
  "win_rate": "Won deals ÷ leads reaching proposal.",
  "loss_rate": "Lost deals after proposal ÷ leads reaching proposal.",
  "funnel_stage_latency": (
    "Avg days from lead creation to call, demo, and proposal, "
    "grouped by outcome (win, loss, open pipeline)."
  ),
  "seat_utilization": "seats_active / contracted seats, daily avg per client; charts use 7-day rolling mean.",
  "feature_adoption_rate": (
    "Distinct users with a feature_adopted event in month ÷ distinct users with login in month, "
    "by feature_name."
  ),
}

FUNNEL_METRIC_KEYS = [
  "lead_to_funnel_rate",
  "call_rate",
  "demo_rate",
  "proposal_rate",
  "win_rate",
  "loss_rate",
]


def render_definition(key: str) -> None:
  if key in METRIC_DEFS:
    st.caption(f"**Definition:** {METRIC_DEFS[key]}")


def render_funnel_definitions() -> None:
  with st.expander("Metric definitions", expanded=True):
    for key in FUNNEL_METRIC_KEYS:
      label = key.replace("_", " ").replace("to funnel rate", "→ funnel").title()
      st.caption(f"**{label}:** {METRIC_DEFS[key]}")
