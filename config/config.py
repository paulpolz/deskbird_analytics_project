"""Central configuration for all pipeline services."""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
WAREHOUSE_PATH = DATA_DIR / "warehouse.duckdb"

# Reproducibility
RANDOM_SEED = 42
FAKER_SEED = 42

# Time window
START_DATE = date(2025, 1, 1)
END_DATE = date.today()

# Dimensions
COUNTRIES = ["DE", "AT", "CH", "UK", "US"]
PROVIDERS = ["google", "linkedin", "meta"]
CHANNELS = PROVIDERS  # 1:1 mapping
FUNNEL_STAGES = ["call", "demo", "proposal", "won", "lost"]
TERMINAL_STAGES = {"won", "lost"}

# Segment
SEAT_SEGMENT_THRESHOLD = 200
SEGMENT_SMB = "SMB"
SEGMENT_ENTERPRISE = "Enterprise"

# Demo SLA (story #5)
DEMO_SLA_DAYS = 14

# Analytics addon attach rates (story #4)
ANALYTICS_ATTACH_SMB = 0.40
ANALYTICS_ATTACH_ENTERPRISE = 0.15

# Campaign roster: provider × country (no segment — business type lives on CRM leads)
CAMPAIGN_ROSTER = [
    {"provider": provider, "country": country}
    for provider in PROVIDERS
    for country in COUNTRIES
]

# Lead business-type mix (independent of acquisition channel)
LEAD_SEGMENT_WEIGHTS = {SEGMENT_SMB: 0.6, SEGMENT_ENTERPRISE: 0.4}

# Story knobs — ads delivery
ADS_KNOBS = {
    "google": {"daily_spend": (80, 200), "ctr": (0.025, 0.045), "cpc": (1.5, 3.0)},
    "linkedin": {"daily_spend": (300, 600), "ctr": (0.008, 0.018), "cpc": (8.0, 15.0)},
    "meta": {"daily_spend": (50, 120), "ctr": (0.03, 0.06), "cpc": (0.8, 2.0)},
}

# Story knobs — lead volume multiplier per provider
LEAD_VOLUME = {"google": 1.0, "linkedin": 0.35, "meta": 1.8}

# Story knobs — funnel conversion rates by provider
FUNNEL_RATES = {
    "google": {"call": 0.55, "demo": 0.70, "proposal": 0.55, "won": 0.45, "open": 0.15},
    "linkedin": {"call": 0.45, "demo": 0.65, "proposal": 0.60, "won": 0.50, "open": 0.20},
    "meta": {"call": 0.60, "demo": 0.40, "proposal": 0.25, "won": 0.05, "open": 0.10},
}

# Market friction: proposal stage delay multiplier (story #3)
MARKET_FRICTION = {"DE": 1.4, "AT": 1.3, "CH": 1.35, "UK": 0.85, "US": 1.0}

# Seat ranges by segment
SEAT_RANGES = {
    SEGMENT_SMB: (20, 180),
    SEGMENT_ENTERPRISE: (200, 800),
}

# Product features
PRODUCT_FEATURES = ["analytics", "scheduling", "integrations", "reporting"]

# dbt vars mirror (subset needed in SQL)
DBT_VARS = {
    "seat_segment_threshold": SEAT_SEGMENT_THRESHOLD,
    "demo_sla_days": DEMO_SLA_DAYS,
}

# Python interpreter for venv
PYTHON_BIN = "python3.11"
