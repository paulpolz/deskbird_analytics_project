"""DuckDB connector — reads marts/metrics only."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config import config as cfg  # noqa: E402


class DuckDBConnector:
  """Parameterized queries against the warehouse."""

  def __init__(self, path: Path | None = None) -> None:
    self.path = str(path or cfg.WAREHOUSE_PATH)

  @st.cache_resource
  def _connection(_self) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(_self.path, read_only=True)

  def run_query(self, sql: str, params: list | dict | None = None) -> pd.DataFrame:
    con = self._connection()
    return con.execute(sql, params or {}).df()

  def table_exists(self, schema: str, table: str) -> bool:
    df = self.run_query(
      "SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
      [schema, table],
    )
    return df["n"].iloc[0] > 0
