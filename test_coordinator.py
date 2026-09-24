from trade_coordinator import get_coin_owner, claim_coin

coin = "LINK"

before = get_coin_owner(coin)
print(f"{coin} owner before Aggressive claim attempt: {before}")

claimed = claim_coin(coin, "aggressive")
print(f"Aggressive claim result: {claimed}")

after = get_coin_owner(coin)
print(f"{coin} owner after Aggressive claim attempt: {after}")
