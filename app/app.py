"""Streamlit entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.connectors.duckdb import DuckDBConnector
from app.tabs import ads, crm, product
from app.views.filters import render_crm_filters, render_global_filters, render_product_filters


def main() -> None:
  st.set_page_config(page_title="Deskbird Growth Dashboard", layout="wide")
  st.title("Deskbird Growth Analytics")
  st.caption("Conversions = CRM wins, attributed to campaigns via lead UTMs (not ad platform data).")

  db = DuckDBConnector()
  filters = render_global_filters()

  tabs = st.tabs(["Ads", "CRM", "Product"])
  with tabs[0]:
    ads.render(db, filters)
  with tabs[1]:
    crm_filters = render_crm_filters()
    crm.render(db, filters, crm_filters)
  with tabs[2]:
    product_filters = render_product_filters()
    product.render(db, filters, product_filters)


if __name__ == "__main__":
  main()
