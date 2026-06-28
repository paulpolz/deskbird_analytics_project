#!/usr/bin/env python3
"""Export Plotly charts and Mermaid diagrams for the slide deck.

Mirrors Streamlit tab queries and chart helpers (app/tabs/*, app/views/charts.py).
Run after: python run.py all
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.queries.funnel_rates import FUNNEL_RATES_INLINE  # noqa: E402
from app.views.charts import (  # noqa: E402
  COLOR_SEQUENCE,
  apply_chart_style,
  plot_bar,
  plot_cac_bar,
  plot_line,
  plot_stage_latency,
  rolling_mean,
)
from config import config as cfg  # noqa: E402

ASSETS = ROOT / "docs" / "slides" / "assets"
DIAGRAMS = ROOT / "docs" / "slides" / "diagrams"
IMG = dict(width=1280, height=720, scale=2)

CHANNELS = ["google", "linkedin", "meta"]
COUNTRIES = ["DE", "AT", "CH", "UK", "US"]
SEGMENTS = ["SMB", "Enterprise"]

RATE_COLS = [
  ("lead_to_funnel_rate", "leads", "clicks"),
  ("call_rate", "calls", "leads"),
  ("demo_rate", "demos", "calls"),
  ("proposal_rate", "proposals", "demos"),
  ("win_rate", "wins", "proposals"),
  ("loss_rate", "losses", "proposals"),
]

_BUCKET_ORDER = {
  "segment": ["SMB", "Enterprise"],
  "contract_length_bucket": ["12-18 mo", "19-24 mo", "25-36 mo"],
  "seats_bucket": ["<100", "100-199", "200-399", "400+"],
}


class Warehouse:
  def __init__(self, path: Path | None = None) -> None:
    self.path = str(path or cfg.WAREHOUSE_PATH)
    self._con = duckdb.connect(self.path, read_only=True)

  def run(self, sql: str) -> pd.DataFrame:
    return self._con.execute(sql).df()

  def funnel_rates_from(self) -> str:
    df = self.run(
      "SELECT COUNT(*) AS n FROM information_schema.tables "
      "WHERE table_schema = 'metrics' AND table_name = 'metric_funnel_rates'"
    )
    if df["n"].iloc[0] > 0:
      return "metrics.metric_funnel_rates"
    return f"({FUNNEL_RATES_INLINE})"


def _filters() -> dict:
  return {
    "start": cfg.START_DATE,
    "end": cfg.END_DATE,
    "channel": CHANNELS,
    "country": COUNTRIES,
  }


def _cac_where(filters: dict) -> str:
  ch = ",".join(f"'{c}'" for c in filters["channel"])
  co = ",".join(f"'{c}'" for c in filters["country"])
  return (
    f"channel IN ({ch}) AND country IN ({co})"
    f" AND month BETWEEN '{filters['start']}' AND '{filters['end']}'"
  )


def _crm_where(filters: dict) -> str:
  ch = ",".join(f"'{c}'" for c in filters["channel"])
  co = ",".join(f"'{c}'" for c in filters["country"])
  seg = ",".join(f"'{s}'" for s in SEGMENTS)
  return (
    f"month BETWEEN '{filters['start']}' AND '{filters['end']}'"
    f" AND channel IN ({ch}) AND country IN ({co}) AND segment IN ({seg})"
  )


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


def _save(fig: go.Figure, name: str) -> None:
  ASSETS.mkdir(parents=True, exist_ok=True)
  path = ASSETS / name
  fig.update_layout(template="plotly", paper_bgcolor="white", plot_bgcolor="white")
  apply_chart_style(fig, for_slides=True)
  fig.write_image(str(path), **IMG)
  print(f"  wrote {path.relative_to(ROOT)}")


def _rates_by_query(db: Warehouse, w: str, split: str) -> str:
  rate_exprs = ",\n           ".join(
    f"SUM({num})::DOUBLE / NULLIF(SUM({den}), 0) AS {name}" for name, num, den in RATE_COLS
  )
  return f"""
    SELECT {split},
           {rate_exprs}
    FROM {db.funnel_rates_from()}
    WHERE {w}
    GROUP BY 1
    ORDER BY 1
  """


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


def _plot_stage_rates_by_channel(rates: pd.DataFrame, title: str) -> go.Figure:
  cols = ["demo_rate", "proposal_rate", "win_rate"]
  labels = {"demo_rate": "Demo rate", "proposal_rate": "Proposal rate", "win_rate": "Win rate"}
  long = rates.melt(id_vars=["channel"], value_vars=cols, var_name="metric", value_name="rate")
  long["metric"] = long["metric"].map(labels)
  long["rate"] = (long["rate"] * 100).round(1)
  fig = px.bar(
    long,
    x="channel",
    y="rate",
    color="metric",
    barmode="group",
    title=title,
    color_discrete_sequence=COLOR_SEQUENCE,
  )
  fig.update_yaxes(tickformat=".1f", ticksuffix="%", title="Rate")
  return fig


def _plot_win_rate_bar(rates: pd.DataFrame, dim: str, title: str) -> go.Figure:
  plot_df = rates[[dim, "win_rate"]].copy()
  plot_df["win_rate"] = (plot_df["win_rate"] * 100).round(1)
  fig = px.bar(
    plot_df,
    x=dim,
    y="win_rate",
    title=title,
    text="win_rate",
    color_discrete_sequence=COLOR_SEQUENCE,
  )
  fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
  fig.update_yaxes(tickformat=".1f", ticksuffix="%", title="Win rate")
  return fig


def _util_bar_by_bucket(db: Warehouse, seg: str, addon_clause: str, bucket: str, title: str) -> go.Figure:
  df = db.run(_util_query(seg, addon_clause, bucket))
  if df.empty:
    raise ValueError(f"No utilization data for {bucket}")
  df = _order_buckets(df, bucket)
  summary = df.groupby(bucket, observed=True)["utilization"].mean().reset_index()
  summary["utilization"] = (summary["utilization"] * 100).round(1)
  fig = px.bar(
    summary,
    x=bucket,
    y="utilization",
    title=title,
    text="utilization",
    color_discrete_sequence=COLOR_SEQUENCE,
  )
  fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
  fig.update_yaxes(tickformat=".1f", ticksuffix="%", title="Avg seat utilization")
  return fig


def export_charts(db: Warehouse) -> None:
  pio.templates.default = "plotly"
  filters = _filters()
  cac_w = _cac_where(filters)
  crm_w = _crm_where(filters)
  ch = ",".join(f"'{c}'" for c in CHANNELS)
  co = ",".join(f"'{c}'" for c in COUNTRIES)
  seg = ",".join(f"'{s}'" for s in SEGMENTS)
  seg_sql = "'SMB', 'Enterprise'"

  # Insight 1 — CAC by channel (ads.py)
  cac_detail = db.run(f"""
    WITH cac AS (
      SELECT channel, SUM(total_spend) spend, SUM(won_clients) wins,
             SUM(total_spend) / NULLIF(SUM(won_clients), 0) AS cac
      FROM metrics.metric_cac WHERE {cac_w} GROUP BY 1
    ),
    seats AS (
      SELECT channel, ROUND(AVG(seats), 0) AS avg_seats
      FROM marts.dim_clients
      WHERE contract_start_date BETWEEN '{filters['start']}' AND '{filters['end']}'
      GROUP BY 1
    )
    SELECT c.channel, c.spend, c.wins, c.cac, s.avg_seats
    FROM cac c LEFT JOIN seats s USING (channel)
    ORDER BY c.cac DESC NULLS FIRST
  """)
  _save(plot_cac_bar(cac_detail, "channel", "CAC by Channel"), "insight01_cac_by_channel.png")

  wins_seg = db.run(f"""
    SELECT channel, segment, COUNT(DISTINCT client_id) AS wins
    FROM marts.fct_lead_journey
    WHERE terminal_stage = 'won'
      AND channel IN ({ch}) AND country IN ({co})
      AND won_at BETWEEN '{filters['start']}' AND '{filters['end']}'
    GROUP BY 1, 2 ORDER BY 1, 2
  """)
  _save(
    plot_bar(wins_seg, "channel", "wins", color="segment", title="Wins by Channel", barmode="group"),
    "insight01_wins_by_segment.png",
  )

  # Insight 2 — Meta funnel gap (crm.py rates by channel)
  rates_ch = db.run(_rates_by_query(db, crm_w, "channel"))
  _save(
    _plot_stage_rates_by_channel(rates_ch, "Demo / Proposal / Win Rate by Channel"),
    "insight02_stage_rates_by_channel.png",
  )

  # Insight 3 — DACH vs UK/US
  rates_co = db.run(_rates_by_query(db, crm_w, "country"))
  _save(_plot_win_rate_bar(rates_co, "country", "Win Rate by Country"), "insight03_win_rate_by_country.png")

  latency_co = db.run(_latency_query(ch, co, seg, "country"))
  _save(
    plot_stage_latency(latency_co, x="country", title="Funnel Stage Latency by Country"),
    "insight03_latency_by_country.png",
  )

  # Insight 4 — Enterprise vs SMB
  rates_seg = db.run(_rates_by_query(db, crm_w, "segment"))
  _save(_plot_win_rate_bar(rates_seg, "segment", "Win Rate by Segment"), "insight04_win_rate_by_segment.png")

  # Insight 5 — Analytics addon (product.py)
  by_addon = db.run(_util_query(seg_sql, "", "has_analytics_addon"))
  by_addon = by_addon.copy()
  by_addon["has_analytics_addon"] = by_addon["has_analytics_addon"].map({True: "With addon", False: "No addon"})
  _save(
    plot_line(
      rolling_mean(by_addon, "has_analytics_addon", "utilization"),
      "day",
      "utilization",
      "has_analytics_addon",
      "Utilization by Analytics Addon (7-Day Rolling)",
      y_as_percent=True,
    ),
    "insight05_util_by_addon.png",
  )

  for label, clause, fname in [
    ("With addon", "AND has_analytics_addon = true", "insight05_util_smb_addon_yes.png"),
    ("No addon", "AND has_analytics_addon = false", "insight05_util_smb_addon_no.png"),
  ]:
    _save(
      _util_bar_by_bucket(
        db,
        "'SMB'",
        clause,
        "seats_bucket",
        f"SMB Utilization by Seats — {label}",
      ),
      fname,
    )

  # Insight 6 — contract length + segment
  by_contract = db.run(_util_query(seg_sql, "", "contract_length_bucket"))
  _save(
    plot_line(
      rolling_mean(_order_buckets(by_contract, "contract_length_bucket"), "contract_length_bucket", "utilization"),
      "day",
      "utilization",
      "contract_length_bucket",
      "Utilization by Contract Length (7-Day Rolling)",
      y_as_percent=True,
    ),
    "insight06_util_by_contract.png",
  )

  by_segment = db.run(_util_query(seg_sql, "", "segment"))
  _save(
    plot_line(
      rolling_mean(by_segment, "segment", "utilization"),
      "day",
      "utilization",
      "segment",
      "Seat Utilization by Segment (7-Day Rolling)",
      y_as_percent=True,
    ),
    "insight06_util_by_segment.png",
  )


def _export_diagram_fallbacks(names: list[str]) -> None:
  """Simple box diagrams when mermaid-cli is unavailable."""
  from PIL import Image, ImageDraw, ImageFont

  font_paths = [
    Path.home() / "Library/Fonts/BerlinType-Regular.otf",
    Path.home() / "Library/Fonts/BerlinTypeOffice-Regular.ttf",
  ]
  bold_paths = [
    Path.home() / "Library/Fonts/BerlinType-Bold.otf",
    Path.home() / "Library/Fonts/BerlinTypeOffice-Bold.ttf",
  ]

  def _load_font(paths: list[Path], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in paths:
      if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()

  font = _load_font(font_paths, 18)
  title_font = _load_font(bold_paths, 24)

  def _save_img(img: Image.Image, name: str) -> None:
    path = ASSETS / name
    img.save(path, "PNG")
    print(f"  wrote {path.relative_to(ROOT)}")

  def _draw_box(draw, x, y, w, h, title, lines, fill="#0068c9", text="#ffffff"):
    draw.rectangle([x, y, x + w, y + h], outline="#1a1a1a", fill=fill, width=2)
    draw.text((x + 8, y + 6), title, fill=text, font=title_font)
    ty = y + 28
    line_color = text if text != "#ffffff" else "#f0f4ff"
    for line in lines:
      draw.text((x + 8, ty), line, fill=line_color, font=font)
      ty += 20

  if "raw_schema" in names:
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)
    draw.text((480, 20), "Raw data model (5 tables)", fill="#1a1a1a", font=title_font)
    _draw_box(draw, 40, 80, 360, 100, "ads_campaign_daily", ["provider · campaign · date", "impressions · clicks · spend"], "#0068c9")
    _draw_box(draw, 460, 80, 360, 100, "crm_leads", ["lead_id · UTMs · segment", "country · created_at"], "#ff2b2b")
    _draw_box(draw, 880, 80, 360, 100, "crm_opportunity_funnel", ["lead_id · stage", "entered_at"], "#29b09d")
    _draw_box(draw, 250, 280, 360, 100, "crm_wins", ["client_id · lead_id", "contract · seats · addon"], "#ff8700")
    _draw_box(draw, 670, 280, 360, 100, "product_events", ["client_id · event_type", "seats_active · feature"], "#6d3fc0")
    draw.text((200, 450), "ads → leads (provider+campaign+country)", fill="#444", font=font)
    draw.text((200, 470), "lead_id → funnel / wins", fill="#444", font=font)
    draw.text((200, 490), "client_id → product events", fill="#444", font=font)
    _save_img(img, "raw_schema.png")

  if "dbt_layers" in names:
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)
    draw.text((540, 20), "dbt layer flow", fill="#1a1a1a", font=title_font)
    layers = [
      (60, 60, "raw", ["5 source tables in DuckDB"], "#83c9ff", "#1a1a1a"),
      (60, 150, "staging (5)", ["stg_ads · stg_crm_leads · stg_crm_funnel", "stg_crm_wins · stg_product_events"], "#29b09d", "#ffffff"),
      (60, 260, "intermediate (4)", ["int_campaign_spend · int_funnel_events", "int_lead_attribution · int_product_events"], "#7defa1", "#1a1a1a"),
      (60, 370, "marts (4)", ["dim_campaigns · dim_clients · dim_date", "fct_lead_journey"], "#ff8700", "#ffffff"),
      (60, 480, "metrics (6)", ["metric_cac · metric_funnel_rates · metric_win_rate", "metric_funnel_stage_latency · metric_seat_utilization", "metric_feature_adoption_rate"], "#0068c9", "#ffffff"),
    ]
    for x, y, title, lines, fill, text in layers:
      _draw_box(draw, x, y, 1160, 80 if len(lines) < 3 else 100, title, lines, fill, text)
    _save_img(img, "dbt_layers.png")


def export_diagrams() -> None:
  ASSETS.mkdir(parents=True, exist_ok=True)
  failed: list[str] = []
  for mmd in sorted(DIAGRAMS.glob("*.mmd")):
    out = ASSETS / f"{mmd.stem}.png"
    config = DIAGRAMS / "mermaid-config.json"
    cmd = [
      "npx", "--yes", "@mermaid-js/mermaid-cli", "-i", str(mmd), "-o", str(out),
      "-b", "white", "-t", "default", "-c", str(config),
    ]
    print(f"$ {' '.join(cmd)}")
    try:
      subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True)
      print(f"  wrote {out.relative_to(ROOT)}")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
      print(f"  skip {mmd.name}: mermaid-cli unavailable ({exc})")
      failed.append(mmd.stem)

  if failed:
    print("  generating diagram fallbacks with PIL…")
    _export_diagram_fallbacks(failed)


def main() -> None:
  if not cfg.WAREHOUSE_PATH.exists():
    print(f"Warehouse not found: {cfg.WAREHOUSE_PATH}. Run: python run.py all")
    sys.exit(1)

  print("Exporting chart PNGs…")
  db = Warehouse()
  export_charts(db)

  print("Exporting diagram PNGs…")
  export_diagrams()

  print("Done. Build deck: make deck  (or cd docs/slides && npm run build)")


if __name__ == "__main__":
  main()
