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
