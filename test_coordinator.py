from trade_coordinator import get_coin_owner, release_coin

coin = "SOL"

before = get_coin_owner(coin)
print(f"{coin} owner before release: {before}")

released = release_coin(coin, "intraday")
print(f"Intraday release result: {released}")

after = get_coin_owner(coin)
print(f"{coin} owner after release: {after}")
