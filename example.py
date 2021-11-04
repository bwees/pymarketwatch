# pymarketwatch example
# Author: bwees, based on code from https://github.com/kevindong/MarketWatch_API/

from pymarketwatch import MarketWatch

with open("creds.txt", "r") as f:
	creds = f.read().splitlines()
	for cred in creds:
		if cred.startswith("email"):
			email = cred.split("=")[1]
		if cred.startswith("password"):
			password = cred.split("=")[1]
		if cred.startswith("game"):
			game = cred.split("=")[1]


api = MarketWatch(email, password, game, True)
# api.buy("AAPL", 100)

print(api.get_pending_orders())
print(api.get_positions())