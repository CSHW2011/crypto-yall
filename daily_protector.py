"""
daily_protector.py

Hourly protective layer for Daily-owned BTC/ETH positions.

Purpose:
- Protect Daily positions with a 3x ATR Chandelier exit.
- Never interfere with Intraday or Aggressive ownership.
- Close a Daily position immediately when its protective stop is breached.
- After a protective exit, allow an opposite-direction entry only after
  a fresh hourly oscillator confirmation.
"""

import os
import sys
import datetime as dt

import numpy as np
import pandas as pd

from intraday_data_loader import fetch_all_intraday
from indicators import two_pole_oscillator, average_true_range
from hyperliquid_executor import (
    HL_TICKER_MAP,
    get_client,
    get_open_positions,
    get_mid_price,
    load_trading_state,
    save_trading_state,
)

from backtester import get_asset_profile


PROTECTED_TICKERS = {"BTC-USD", "ETH-USD"}

OSC_UPPER = 0.5
OSC_LOWER = -0.5
ATR_PERIOD = 14
BW_CUTOFF_1H = 0.1
SMA_PERIOD_1H = 20
LOOKBACK_HOURS = 1000
def build_hourly_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add hourly oscillator and ATR features used by the Daily protector.
    """
    out = df.copy()

    osc_raw = two_pole_oscillator(
        out["Close"],
        cutoff=BW_CUTOFF_1H,
        sma_period=SMA_PERIOD_1H,
    )

    zscore_window = 100
    osc_mean = osc_raw.rolling(zscore_window, min_periods=20).mean()
    osc_std = osc_raw.rolling(zscore_window, min_periods=20).std()

    osc = (osc_raw - osc_mean) / osc_std.replace(0, np.nan)
    osc = osc.fillna(0)

    atr = average_true_range(
        out["High"],
        out["Low"],
        out["Close"],
        period=ATR_PERIOD,
    )

    out["Osc"] = osc
    out["ATR"] = atr

    return out
  def find_entry_timestamp(state: dict, ticker: str) -> pd.Timestamp | None:
    """
    Find the most recent successful open trade for this ticker in Daily history.
    """
    history = state.get("history", [])

    for item in reversed(history):
        if item.get("ticker") != ticker:
            continue
        if item.get("status") != "filled":
            continue
        if item.get("action") not in ("open_long", "open_short"):
            continue

        ts = item.get("timestamp")
        if not ts:
            continue

        try:
            return pd.to_datetime(ts, utc=True)
        except Exception:
            continue

    return None
