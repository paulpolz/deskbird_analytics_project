#!/usr/bin/env python3
"""Centralized pipeline runner."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import config as cfg  # noqa: E402

VENV = ROOT / ".venv"
VENV_PY = VENV / "bin" / "python"
VENV_PIP = VENV / "bin" / "pip"


def _run(cmd: list[str], cwd: Path | None = None) -> None:
  print(f"$ {' '.join(cmd)}")
  subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def setup() -> None:
  if not VENV.exists():
    _run([cfg.PYTHON_BIN, "-m", "venv", str(VENV)])
  _run([str(VENV_PIP), "install", "-r", "requirements.txt"])
  print("Setup complete.")


def _py() -> str:
  return str(VENV_PY) if VENV_PY.exists() else sys.executable


def generate() -> None:
  _run([_py(), "scripts/generate_data.py"])


def _dbt_env() -> dict:
  return {
    **os.environ,
    "DBT_PROFILES_DIR": str(ROOT / "dbt_deskbird"),
    "WAREHOUSE_PATH": str(cfg.WAREHOUSE_PATH.resolve()),
  }


def dbt() -> None:
  dbt_dir = ROOT / "dbt_deskbird"
  dbt_bin = str(VENV / "bin" / "dbt") if (VENV / "bin" / "dbt").exists() else "dbt"
  for cmd in [[dbt_bin, "run"], [dbt_bin, "test"]]:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=dbt_dir, check=True, env=_dbt_env())


def app() -> None:
  _run([_py(), "-m", "streamlit", "run", "app/app.py"])


def slides() -> None:
  _run([_py(), "scripts/export_slide_assets.py"])


def deck() -> None:
  slides()
  _run([_py(), "scripts/build_deck.py"])


def all_steps() -> None:
  if not VENV.exists():
    setup()
  generate()
  dbt()
  print("Pipeline built. Launch dashboard with: python run.py app")
  

def main() -> None:
  parser = argparse.ArgumentParser(description="Deskbird Growth Pipeline runner")
  parser.add_argument(
    "command",
    choices=["setup", "generate", "dbt", "app", "slides", "deck", "all"],
  )
  args = parser.parse_args()
  {
    "setup": setup,
    "generate": generate,
    "dbt": dbt,
    "app": app,
    "slides": slides,
    "deck": deck,
    "all": all_steps,
  }[args.command]()


if __name__ == "__main__":
  main()
