from trade_coordinator import get_coin_owner, release_coin

coin = "LINK"

before = get_coin_owner(coin)
print(f"{coin} owner before Aggressive release: {before}")

released = release_coin(coin, "aggressive")
print(f"Aggressive release result: {released}")

after = get_coin_owner(coin)
print(f"{coin} owner after Aggressive release: {after}")
