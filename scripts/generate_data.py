"""Faker service: generate deterministic raw tables into DuckDB."""

from __future__ import annotations

import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import config as cfg  # noqa: E402


class DataGenerator:
  """Generates all raw tables with embedded growth stories."""

  def __init__(self) -> None:
    random.seed(cfg.RANDOM_SEED)
    self.campaigns: list[dict] = []
    self.leads: list[dict] = []
    self.funnel_events: list[dict] = []
    self.wins: list[dict] = []
    self.product_events: list[dict] = []
    self._event_seq = 0
    self._funnel_seq = 0

  def run(self) -> None:
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    self._build_campaigns()
    self._build_leads()
    self._build_funnel()
    self._build_wins()
    self._build_product_events()
    self._validate()
    self._load_to_duckdb()

  # --- campaign & ads ---

  def _rand_time(self) -> time:
    return time(random.randint(8, 18), random.randint(0, 59), random.randint(0, 59))

  def _build_campaigns(self) -> None:
    for i, spec in enumerate(cfg.CAMPAIGN_ROSTER):
      cid = f"{spec['provider']}_{spec['country']}_{i+1:03d}"
      self.campaigns.append({
        "provider": spec["provider"],
        "campaign_id": cid,
        "campaign_name": f"{spec['provider'].title()} {spec['country']}",
        "channel": spec["provider"],
        "country": spec["country"],
      })

  def _lead_segment(self) -> str:
    segments = list(cfg.LEAD_SEGMENT_WEIGHTS)
    weights = list(cfg.LEAD_SEGMENT_WEIGHTS.values())
    return random.choices(segments, weights=weights, k=1)[0]

  def _ads_daily_rows(self) -> list[dict]:
    rows = []
    day = cfg.START_DATE
    while day <= cfg.END_DATE:
      for c in self.campaigns:
        knobs = cfg.ADS_KNOBS[c["provider"]]
        spend = round(random.uniform(*knobs["daily_spend"]), 2)
        cpc = random.uniform(*knobs["cpc"])
        clicks = max(1, int(spend / cpc))
        ctr = random.uniform(*knobs["ctr"])
        impressions = max(clicks, int(clicks / ctr))
        rows.append({
          "provider": c["provider"],
          "campaign_id": c["campaign_id"],
          "campaign_name": c["campaign_name"],
          "channel": c["channel"],
          "country": c["country"],
          "date": day,
          "impressions": impressions,
          "clicks": clicks,
          "spend": spend,
        })
      day += timedelta(days=1)
    return rows

  # --- leads ---

  def _build_leads(self) -> None:
    lead_id = 1
    day = cfg.START_DATE
    while day <= cfg.END_DATE:
      for c in self.campaigns:
        base = int(3 * cfg.LEAD_VOLUME[c["provider"]] * random.uniform(0.7, 1.3))
        for _ in range(base):
          created = datetime.combine(day, self._rand_time())
          self.leads.append({
            "lead_id": f"L{lead_id:05d}",
            "utm_source": c["provider"],
            "utm_campaign": c["campaign_id"],
            "channel": c["provider"],
            "country": c["country"],
            "created_at": created,
            "segment": self._lead_segment(),
          })
          lead_id += 1
      day += timedelta(days=2)  # every other day to keep volume manageable

  # --- funnel ---

  def _build_funnel(self) -> None:
    for lead in self.leads:
      provider = lead["channel"]
      country = lead["country"]
      rates = cfg.FUNNEL_RATES[provider]
      friction = cfg.MARKET_FRICTION.get(country, 1.0)

      if random.random() > rates["call"]:
        continue  # never enters funnel

      ts = lead["created_at"] + timedelta(days=random.randint(0, 3))
      stages_entered = ["call"]
      self._add_funnel_event(lead["lead_id"], "call", ts)

      # story #5: slow call→demo correlates with loss
      demo_delay = random.randint(3, 20) if random.random() < 0.25 else random.randint(1, 10)
      if demo_delay > cfg.DEMO_SLA_DAYS and random.random() < 0.75:
        # likely lost after stalled demo
        self._add_funnel_event(lead["lead_id"], "lost", ts + timedelta(days=demo_delay + 2))
        continue

      if random.random() > rates["demo"]:
        if random.random() < 0.5:
          self._add_funnel_event(lead["lead_id"], "lost", ts + timedelta(days=demo_delay))
        continue

      ts += timedelta(days=demo_delay)
      self._add_funnel_event(lead["lead_id"], "demo", ts)
      stages_entered.append("demo")

      # meta story #2: heavy drop after demo
      if provider == "meta" and random.random() > rates["proposal"]:
        self._add_funnel_event(lead["lead_id"], "lost", ts + timedelta(days=random.randint(2, 7)))
        continue

      proposal_delay = int(random.randint(3, 10) * friction)
      if random.random() > rates["proposal"]:
        if random.random() < 0.4:
          self._add_funnel_event(lead["lead_id"], "lost", ts + timedelta(days=proposal_delay))
        continue

      ts += timedelta(days=proposal_delay)
      self._add_funnel_event(lead["lead_id"], "proposal", ts)

      if random.random() < rates["open"]:
        continue  # open pipeline

      close_delay = int(random.randint(5, 20) * friction)
      ts += timedelta(days=close_delay)

      # market friction lowers win rate in DE/AT/CH
      win_prob = rates["won"]
      if country in ("DE", "AT", "CH"):
        win_prob *= 0.75
      elif country == "UK":
        win_prob *= 1.1

      if random.random() < win_prob:
        self._add_funnel_event(lead["lead_id"], "won", ts)
      else:
        self._add_funnel_event(lead["lead_id"], "lost", ts)

  def _add_funnel_event(self, lead_id: str, stage: str, entered_at: datetime) -> None:
    self._funnel_seq += 1
    self.funnel_events.append({
      "funnel_event_id": f"FE{self._funnel_seq:06d}",
      "lead_id": lead_id,
      "stage": stage,
      "entered_at": entered_at,
    })

  # --- wins ---

  def _build_wins(self) -> None:
    won_leads = {e["lead_id"] for e in self.funnel_events if e["stage"] == "won"}
    client_id = 1
    for lead in self.leads:
      if lead["lead_id"] not in won_leads:
        continue
      segment = lead["segment"]
      lo, hi = cfg.SEAT_RANGES[segment]
      seats = random.randint(lo, hi)
      won_evt = next(e for e in self.funnel_events if e["lead_id"] == lead["lead_id"] and e["stage"] == "won")
      contract_start = (won_evt["entered_at"] + timedelta(days=random.randint(5, 25))).date()
      contract_months = random.randint(12, 24) if segment == cfg.SEGMENT_SMB else random.randint(24, 36)
      contract_end = contract_start + timedelta(days=contract_months * 30)

      attach_rate = cfg.ANALYTICS_ATTACH_SMB if segment == cfg.SEGMENT_SMB else cfg.ANALYTICS_ATTACH_ENTERPRISE
      services = []
      if random.random() < attach_rate:
        services.append("analytics")
      if random.random() < 0.3:
        services.append(random.choice([f for f in cfg.PRODUCT_FEATURES if f != "analytics"]))

      self.wins.append({
        "client_id": f"C{client_id:04d}",
        "lead_id": lead["lead_id"],
        "contract_start_date": contract_start,
        "contract_end_date": contract_end,
        "contract_length_months": contract_months,
        "seats": seats,
        "additional_services": ",".join(services) if services else "",
        "market": lead["country"],
        "segment": segment,
        "channel": lead["channel"],
        "has_analytics": "analytics" in services,
      })
      client_id += 1

  # --- product events ---

  def _client_users(self, client_id: str, seats: int) -> list[str]:
    n = max(5, min(int(seats * 0.12), 35))
    return [f"U_{client_id}_{i:03d}" for i in range(1, n + 1)]

  def _build_product_events(self) -> None:
    for win in self.wins:
      start = win["contract_start_date"]
      end = min(win["contract_end_date"], cfg.END_DATE)
      seats = win["seats"]
      has_analytics = win["has_analytics"]
      segment = win["segment"]
      users = self._client_users(win["client_id"], seats)

      # story #6: low-engagement cohort decays faster
      low_engagement = random.random() < 0.20
      base_logins = 2 if low_engagement else (4 if has_analytics and segment == cfg.SEGMENT_SMB else 3)
      user_adopted: dict[str, set[str]] = {user_id: set() for user_id in users}

      week = start
      while week <= end:
        week_dt = datetime.combine(week, self._rand_time())
        tenure_days = (week - start).days
        active_share = 0.55 if low_engagement and tenure_days > 30 else 0.75
        if has_analytics and segment == cfg.SEGMENT_SMB:
          active_share = min(0.95, active_share + 0.12)
        active_users = random.sample(
          users,
          k=max(1, int(len(users) * active_share)),
        )

        skip_prob = 0.22
        if low_engagement:
          skip_prob = 0.40 if tenure_days > 30 else 0.28
        if has_analytics and segment == cfg.SEGMENT_SMB:
          skip_prob *= 0.55

        for user_id in active_users:
          if random.random() < skip_prob:
            continue
          login_count = base_logins
          if low_engagement and tenure_days > 30:
            login_count = max(1, int(base_logins * 0.35))
          if has_analytics and segment == cfg.SEGMENT_SMB:
            login_count = max(1, int(login_count * 1.25))
          for _ in range(login_count):
            self._add_product_event(win["client_id"], user_id, "login", week_dt)

          if not low_engagement:
            adopt_prob = 0.10 if tenure_days <= 60 else 0.05
            if has_analytics:
              adopt_prob *= 1.25
            if random.random() < adopt_prob:
              remaining = [f for f in cfg.PRODUCT_FEATURES if f not in user_adopted[user_id]]
              if remaining:
                feat = random.choice(remaining)
                user_adopted[user_id].add(feat)
                self._add_product_event(
                  win["client_id"], user_id, "feature_adopted", week_dt, feature_name=feat,
                )

        util = random.uniform(0.4, 0.85)
        if has_analytics and segment == cfg.SEGMENT_SMB:
          util = min(0.95, util + 0.15)
        if low_engagement:
          util *= 0.5 if tenure_days > 30 else 0.7

        seats_active = max(1, int(seats * util))
        self._add_product_event(
          win["client_id"], users[0], "seat_snapshot", week_dt,
          seats_active=seats_active,
        )

        week += timedelta(days=7)

  def _add_product_event(
    self, client_id: str, user_id: str, event_type: str, event_at: datetime,
    seats_active: int | None = None, feature_name: str | None = None,
  ) -> None:
    self._event_seq += 1
    row = {
      "event_id": f"E{self._event_seq:07d}",
      "client_id": client_id,
      "user_id": user_id,
      "event_type": event_type,
      "event_at": event_at,
      "seats_active": seats_active,
      "feature_name": feature_name,
    }
    self.product_events.append(row)

  # --- validation & load ---

  def _validate(self) -> None:
    lead_ids = {l["lead_id"] for l in self.leads}
    funnel_leads = {e["lead_id"] for e in self.funnel_events}
    assert funnel_leads <= lead_ids
    won_leads = {e["lead_id"] for e in self.funnel_events if e["stage"] == "won"}
    win_leads = {w["lead_id"] for w in self.wins}
    assert win_leads == won_leads
    win_clients = {w["client_id"] for w in self.wins}
    prod_clients = {e["client_id"] for e in self.product_events}
    assert prod_clients <= win_clients
    campaign_keys = {(c["provider"], c["campaign_id"], c["country"]) for c in self.campaigns}
    for lead in self.leads:
      key = (lead["utm_source"], lead["utm_campaign"], lead["country"])
      assert key in campaign_keys or any(
        c["provider"] == lead["utm_source"] and c["campaign_id"] == lead["utm_campaign"]
        for c in self.campaigns
      )

  def _load_to_duckdb(self) -> None:
    ads = pd.DataFrame(self._ads_daily_rows())
    leads = pd.DataFrame(self.leads)[
      ["lead_id", "utm_source", "utm_campaign", "channel", "country", "created_at", "segment"]
    ]
    funnel = pd.DataFrame(self.funnel_events)
    wins = pd.DataFrame(self.wins)[
      ["client_id", "lead_id", "contract_start_date", "contract_end_date",
       "contract_length_months", "seats", "additional_services", "market"]
    ]
    product = pd.DataFrame(self.product_events)

    con = duckdb.connect(str(cfg.WAREHOUSE_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for name, df in [
      ("ads_campaign_daily", ads),
      ("crm_leads", leads),
      ("crm_opportunity_funnel", funnel),
      ("crm_wins", wins),
      ("product_events", product),
    ]:
      con.execute(f"DROP TABLE IF EXISTS raw.{name}")
      con.execute(f"CREATE TABLE raw.{name} AS SELECT * FROM df")
    con.close()
    print(f"Loaded {len(ads)} ads, {len(leads)} leads, {len(funnel)} funnel, "
          f"{len(wins)} wins, {len(product)} product events → {cfg.WAREHOUSE_PATH}")


def main() -> None:
  DataGenerator().run()


if __name__ == "__main__":
  main()
