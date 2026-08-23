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


def calculate_chandelier_stop(
    df: pd.DataFrame,
    entry_time: pd.Timestamp,
    is_long: bool,
    atr_mult: float,
) -> tuple[float, float, float] | None:
    """
    Calculate the current Chandelier stop for a Daily-owned position.

    Returns:
        (stop_level, current_price, current_atr)
    """
    if df.empty:
        return None

    features = build_hourly_features(df)

    if entry_time is not None:
        features = features[features.index >= entry_time]

    if features.empty:
        return None

    current = features.iloc[-1]
    current_price = float(current["Close"])
    current_atr = float(current["ATR"])

    if np.isnan(current_atr) or current_atr <= 0:
        return None

    if is_long:
        highest_since = float(features["High"].max())
        stop_level = highest_since - atr_mult * current_atr
    else:
        lowest_since = float(features["Low"].min())
        stop_level = lowest_since + atr_mult * current_atr

    return stop_level, current_price, current_atr


def detect_fresh_reversal(df: pd.DataFrame) -> str | None:
    """
    Detect a fresh hourly oscillator reversal confirmation.

    Returns:
        "long"  when oscillator crosses up through OSC_LOWER
        "short" when oscillator crosses down through OSC_UPPER
        None    otherwise
    """
    if df.empty:
        return None

    features = build_hourly_features(df)

    if len(features) < 2:
        return None

    prev_osc = float(features["Osc"].iloc[-2])
    curr_osc = float(features["Osc"].iloc[-1])

    if prev_osc <= OSC_LOWER < curr_osc:
        return "long"

    if prev_osc >= OSC_UPPER > curr_osc:
        return "short"

    return None

def get_protector_state(state: dict) -> dict:
    """
    Return the persistent Daily protector state.

    Each ticker may store:
        pending_reversal: "long", "short", or None
        protective_exit_at: UTC timestamp or None
        stopped_from: "long", "short", or None
    """
    protector = state.setdefault("daily_protector", {})

    for ticker in PROTECTED_TICKERS:
        protector.setdefault(
            ticker,
            {
                "pending_reversal": None,
                "protective_exit_at": None,
                "stopped_from": None,
            },
        )

    return protector

def mark_protective_exit(
    protector_state: dict,
    ticker: str,
    stopped_from: str,
) -> None:
    """
    Record that a Daily position was protectively exited and that the
    opposite direction is now waiting for fresh hourly confirmation.
    """
    ticker_state = protector_state[ticker]

    ticker_state["stopped_from"] = stopped_from
    ticker_state["protective_exit_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    if stopped_from == "long":
        ticker_state["pending_reversal"] = "short"
    elif stopped_from == "short":
        ticker_state["pending_reversal"] = "long"
    else:
        ticker_state["pending_reversal"] = None

def clear_pending_reversal(
    protector_state: dict,
    ticker: str,
) -> None:
    """
    Clear protector reversal state after a confirmed reversal is completed
    or when the pending reversal should be cancelled.
    """
    ticker_state = protector_state[ticker]

    ticker_state["pending_reversal"] = None
    ticker_state["protective_exit_at"] = None
    ticker_state["stopped_from"] = None

def chandelier_stop_breached(
    df: pd.DataFrame,
    entry_time: pd.Timestamp,
    is_long: bool,
    atr_mult: float,
) -> tuple[bool, float, float, float] | None:
    """
    Check whether the current hourly close has breached the Chandelier stop.

    Returns:
        (breached, stop_level, current_price, current_atr)
    """
    result = calculate_chandelier_stop(
        df=df,
        entry_time=entry_time,
        is_long=is_long,
        atr_mult=atr_mult,
    )

    if result is None:
        return None

    stop_level, current_price, current_atr = result

    if is_long:
        breached = current_price <= stop_level
    else:
        breached = current_price >= stop_level

    return breached, stop_level, current_price, current_atr

def evaluate_live_position(
    ticker: str,
    position: dict,
    df: pd.DataFrame,
    state: dict,
) -> dict:
    """
    Evaluate one Daily-owned live position.

    Returns an action dict with:
        action: "hold" or "protective_exit"
        side: "long" or "short"
        stop_level
        current_price
        current_atr
        reason
    """
    size = float(position["size"])
    is_long = size > 0
    side = "long" if is_long else "short"

    entry_time = find_entry_timestamp(state, ticker)
    if entry_time is None:
        return {
            "action": "hold",
            "side": side,
            "reason": "No Daily entry timestamp found",
        }

    profile = get_asset_profile(ticker)
    atr_mult = float(profile.get("atr_mult", 3.0))

    result = chandelier_stop_breached(
        df=df,
        entry_time=entry_time,
        is_long=is_long,
        atr_mult=atr_mult,
    )

    if result is None:
        return {
            "action": "hold",
            "side": side,
            "reason": "Insufficient hourly ATR data",
        }

    breached, stop_level, current_price, current_atr = result

    if not breached:
        return {
            "action": "hold",
            "side": side,
            "stop_level": stop_level,
            "current_price": current_price,
            "current_atr": current_atr,
            "reason": "Chandelier stop intact",
        }

    return {
        "action": "protective_exit",
        "side": side,
        "stop_level": stop_level,
        "current_price": current_price,
        "current_atr": current_atr,
        "reason": f"{side} Chandelier stop breached",
    }

def evaluate_pending_reversal(
    ticker: str,
    df: pd.DataFrame,
    protector_state: dict,
) -> dict:
    """
    Check whether a stopped-out Daily position has received a fresh
    hourly confirmation for the opposite direction.
    """
    ticker_state = protector_state[ticker]
    pending = ticker_state.get("pending_reversal")

    if pending not in ("long", "short"):
        return {
            "action": "none",
            "reason": "No pending reversal",
        }

    fresh = detect_fresh_reversal(df)

    if fresh != pending:
        return {
            "action": "wait",
            "pending_reversal": pending,
            "fresh_signal": fresh,
            "reason": "Waiting for fresh hourly confirmation",
        }

    return {
        "action": "confirmed_reversal",
        "side": pending,
        "reason": f"Fresh hourly {pending} reversal confirmed",
    }

def build_reversal_trade_intent(
    ticker: str,
    side: str,
) -> dict:
    """
    Build an order intent for a confirmed Daily protective reversal.

    This function does not execute the order.
    """
    if ticker not in PROTECTED_TICKERS:
        raise ValueError(f"Ticker not protected by Daily protector: {ticker}")

    if side not in ("long", "short"):
        raise ValueError(f"Invalid reversal side: {side}")

    hl_coin = HL_TICKER_MAP[ticker]

    return {
        "ticker": ticker,
        "hl_coin": hl_coin,
        "action": "open_long" if side == "long" else "open_short",
        "side": side,
        "reason": f"Confirmed hourly protective reversal to {side}",
    }

def build_protective_exit_intent(
    ticker: str,
    side: str,
    stop_level: float,
    current_price: float,
    current_atr: float,
) -> dict:
    """
    Build a close intent for a Daily position whose Chandelier stop was breached.

    This function does not execute the close.
    """
    if ticker not in PROTECTED_TICKERS:
        raise ValueError(f"Ticker not protected by Daily protector: {ticker}")

    if side not in ("long", "short"):
        raise ValueError(f"Invalid position side: {side}")

    hl_coin = HL_TICKER_MAP[ticker]

    return {
        "ticker": ticker,
        "hl_coin": hl_coin,
        "action": "close",
        "side": side,
        "stop_level": stop_level,
        "current_price": current_price,
        "current_atr": current_atr,
        "reason": f"{side} 3x ATR Chandelier stop breached",
    }

def run_dry_check() -> list[dict]:
    """
    Evaluate Daily-owned BTC/ETH positions and pending reversals.

    Dry-run only:
    - does not close positions
    - does not open positions
    - returns the actions the protector would take
    """
    state = load_trading_state()
    protector_state = get_protector_state(state)

    info, exchange, address = get_client()
    open_positions = get_open_positions(info, address)

    daily_owned = set(state.get("owned_coins", []))
    protected_owned = {
        coin: position
        for coin, position in open_positions.items()
        if coin in daily_owned
        and coin in {HL_TICKER_MAP[t] for t in PROTECTED_TICKERS}
    }

    hourly_data = fetch_all_intraday(
        tickers=list(PROTECTED_TICKERS),
        interval="1h",
        lookback_hours=LOOKBACK_HOURS,
    )

    actions = []

    for ticker in PROTECTED_TICKERS:
        hl_coin = HL_TICKER_MAP[ticker]
        df = hourly_data.get(ticker, pd.DataFrame())

        if hl_coin in protected_owned:
            decision = evaluate_live_position(
                ticker=ticker,
                position=protected_owned[hl_coin],
                df=df,
                state=state,
            )

            if decision.get("action") == "protective_exit":
                actions.append(
                    build_protective_exit_intent(
                        ticker=ticker,
                        side=decision["side"],
                        stop_level=decision["stop_level"],
                        current_price=decision["current_price"],
                        current_atr=decision["current_atr"],
                    )
                )
            else:
                actions.append(
                    {
                        "ticker": ticker,
                        "action": "hold",
                        "reason": decision.get("reason", "No protective action"),
                    }
                )

            continue

        reversal = evaluate_pending_reversal(
            ticker=ticker,
            df=df,
            protector_state=protector_state,
        )

        if reversal.get("action") == "confirmed_reversal":
            actions.append(
                build_reversal_trade_intent(
                    ticker=ticker,
                    side=reversal["side"],
                )
            )
        else:
            actions.append(
                {
                    "ticker": ticker,
                    "action": reversal.get("action", "none"),
                    "reason": reversal.get("reason", "No pending reversal"),
                }
            )

    return actions

def main() -> None:
    """
    Run the Daily protector in dry-run mode and print intended actions.
    """
    print(f"Daily protector dry run started at {dt.datetime.now(dt.timezone.utc).isoformat()}")

    actions = run_dry_check()

    for action in actions:
        print(action)

    print("Daily protector dry run complete")


if __name__ == "__main__":
    main()
