from trade_coordinator import get_coin_owner, release_coin

coin = "BTC"

before = get_coin_owner(coin)
print(f"{coin} owner before Daily release: {before}")

released = release_coin(coin, "daily")
print(f"Daily release result: {released}")

after = get_coin_owner(coin)
print(f"{coin} owner after Daily release: {after}")
