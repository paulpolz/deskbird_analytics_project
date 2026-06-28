"""Reusable filter widgets."""

from __future__ import annotations

from datetime import date

import streamlit as st


def render_global_filters() -> dict:
  with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Date range", value=(date(2025, 1, 1), date.today()))
    channel = st.multiselect("Channel", ["google", "linkedin", "meta"], default=["google", "linkedin", "meta"])
    country = st.multiselect("Country", ["DE", "AT", "CH", "UK", "US"], default=["DE", "AT", "CH", "UK", "US"])
  start, end = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (date(2025, 1, 1), date(2025, 3, 31))
  return {"start": start, "end": end, "channel": channel, "country": country}


def render_crm_filters() -> dict:
  from app.views.metrics import FUNNEL_STAGE_LABELS

  with st.sidebar:
    st.header("CRM funnel")
    segment = st.multiselect("Segment", ["SMB", "Enterprise"], default=["SMB", "Enterprise"])
    stages = st.multiselect(
      "Funnel stages",
      FUNNEL_STAGE_LABELS,
      default=FUNNEL_STAGE_LABELS,
      help="Toggle stages shown in the funnel chart.",
    )
  return {"segment": segment, "stages": stages}


def render_product_filters() -> dict:
  with st.sidebar:
    has_analytics = st.selectbox("Analytics addon", ["All", "Yes", "No"])
  addon = None if has_analytics == "All" else has_analytics == "Yes"
  return {"has_analytics_addon": addon}
