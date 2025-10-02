#!/usr/bin/env python3
import argparse
import os
import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry
import yaml  # PyYAML

DEFAULT_ZILLOW_ZORI_CITY_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zori/City_zori_uc_sfrcondomfr_sm_month.csv"
)

def _session_with_retries(total=5, backoff=0.3):
    retries = Retry(
        total=total,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def download_file(url: str, dest_path: Path, chunk_size: int = 1 << 20) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with _session_with_retries() as s:
        with s.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            tmp = dest_path.with_suffix(dest_path.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
            os.replace(tmp, dest_path)

def load_config(cfg_path: Path | None) -> dict:
    """Load YAML config. Missing file -> {}."""
    if cfg_path is None:
        cfg_path = Path("config.yaml")
    if not cfg_path.exists():
        return {}
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        return data

def resolve_url(args_url: str | None, cfg: dict) -> str:
    """
    Priority:
      1) --url flag
      2) config.yaml -> data_sources.zillow_zori_city_url
      3) DEFAULT_ZILLOW_ZORI_CITY_URL
    """
    if args_url:
        return args_url
    url = (cfg.get("data_sources") or {}).get("zillow_zori_city_url")
    return url or DEFAULT_ZILLOW_ZORI_CITY_URL

def main():
    parser = argparse.ArgumentParser(description="Download Zillow ZORI city CSV to data/raw/")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/raw/zori_city.csv"),
        help="Output file path (default: data/raw/zori_city.csv)",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Override URL (otherwise read from config.yaml, then fallback to built-in default).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config YAML (default: config.yaml).",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    url = resolve_url(args.url, cfg)

    t0 = time.time()
    try:
        download_file(url, args.out)
    except requests.HTTPError as e:
        print(f"[error] HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"[error] Network error: {e}", file=sys.stderr)
        sys.exit(2)

    size = args.out.stat().st_size if args.out.exists() else 0
    dt = time.time() - t0
    print(f"[ok] Saved {size:,} bytes to {args.out} in {dt:.2f}s")

if __name__ == "__main__":
    main()
