"""
Shared trade coordinator for Crypto Y'all.

Tracks which strategy owns each Hyperliquid coin so Daily,
Intraday, and Aggressive cannot manage the same exchange
position at the same time.
"""

import json
import os

import requests


COORDINATOR_FILENAME = "coordinator_state.json"
VALID_STRATEGIES = {"daily", "intraday", "aggressive"}


def load_coordinator_state() -> dict:
    """Load the shared coordinator state from GitHub Gist."""

    gist_token = os.environ.get("GIST_TOKEN")
    gist_id = os.environ.get("COORDINATOR_GIST_ID")

    if not gist_token or not gist_id:
        raise RuntimeError(
            "Missing GIST_TOKEN or COORDINATOR_GIST_ID"
        )

    response = requests.get(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"token {gist_token}"},
        timeout=15,
    )
    response.raise_for_status()

    files = response.json().get("files", {})

    if COORDINATOR_FILENAME not in files:
        raise RuntimeError(
            f"{COORDINATOR_FILENAME} not found in coordinator Gist"
        )

    return json.loads(
        files[COORDINATOR_FILENAME]["content"]
    )


def save_coordinator_state(state: dict) -> None:
    """Save the shared coordinator state to GitHub Gist."""

    gist_token = os.environ.get("GIST_TOKEN")
    gist_id = os.environ.get("COORDINATOR_GIST_ID")

    if not gist_token or not gist_id:
        raise RuntimeError(
            "Missing GIST_TOKEN or COORDINATOR_GIST_ID"
        )

    response = requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"token {gist_token}"},
        json={
            "files": {
                COORDINATOR_FILENAME: {
                    "content": json.dumps(state, indent=2)
                }
            }
        },
        timeout=15,
    )
    response.raise_for_status()


def get_coin_owner(coin: str):
    """Return the strategy that currently owns a coin, or None."""

    coin = coin.upper()
    state = load_coordinator_state()

    return state.get("coin_owners", {}).get(coin)


def can_manage_coin(coin: str, strategy: str) -> bool:
    """
    A strategy may manage a coin if the coin is unowned
    or already owned by that strategy.
    """

    coin = coin.upper()
    strategy = strategy.lower()

    if strategy not in VALID_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")

    owner = get_coin_owner(coin)

    return owner is None or owner == strategy


def claim_coin(coin: str, strategy: str) -> bool:
    """
    Claim an unowned coin for a strategy.

    Returns True if the claim succeeds or the strategy
    already owns the coin.

    Returns False if another strategy owns the coin.
    """

    coin = coin.upper()
    strategy = strategy.lower()

    if strategy not in VALID_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")

    state = load_coordinator_state()
    owners = state.setdefault("coin_owners", {})

    current_owner = owners.get(coin)

    if current_owner not in (None, strategy):
        return False

    owners[coin] = strategy
    save_coordinator_state(state)

    return True


def release_coin(coin: str, strategy: str) -> bool:
    """
    Release a coin only if the requesting strategy owns it.

    Returns True if released.
    Returns False if another strategy owns it.
    """

    coin = coin.upper()
    strategy = strategy.lower()

    if strategy not in VALID_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")

    state = load_coordinator_state()
    owners = state.setdefault("coin_owners", {})

    if owners.get(coin) != strategy:
        return False

    owners[coin] = None
    save_coordinator_state(state)

    return True
