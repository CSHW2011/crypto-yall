from trade_coordinator import get_coin_owner, claim_coin

coin = "BTC"

before = get_coin_owner(coin)
print(f"BTC owner before Intraday claim attempt: {before}")

claimed = claim_coin(coin, "intraday")
print(f"Intraday claim result: {claimed}")

after = get_coin_owner(coin)
print(f"BTC owner after Intraday claim attempt: {after}")
