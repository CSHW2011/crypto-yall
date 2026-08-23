import datetime as dt

from hyperliquid_executor import load_trading_state, save_trading_state


def main() -> None:
    """
    Register the existing BTC Testnet long as Daily-owned for protector testing.

    This script does not place or close any Hyperliquid orders.
    """
    state = load_trading_state()

    owned_coins = set(state.get("owned_coins", []))
    owned_coins.add("BTC")
    state["owned_coins"] = sorted(owned_coins)

    history = state.get("history", [])
    history.append(
        {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "ticker": "BTC-USD",
            "hl_coin": "BTC",
            "action": "open_long",
            "side": "long",
            "status": "filled",
            "reason": "Manual Testnet protector seed",
        }
    )

    state["history"] = history[-500:]

    save_trading_state(state)

    print("Seed complete")
    print(f"Owned coins = {state['owned_coins']}")
    print(f"History entries = {len(state['history'])}")


if __name__ == "__main__":
    main()
