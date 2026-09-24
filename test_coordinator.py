from trade_coordinator import get_coin_owner, claim_coin

coin = "SOL"

before = get_coin_owner(coin)
print(f"{coin} owner before Daily claim attempt: {before}")

claimed = claim_coin(coin, "daily")
print(f"Daily claim result: {claimed}")

after = get_coin_owner(coin)
print(f"{coin} owner after Daily claim attempt: {after}")
