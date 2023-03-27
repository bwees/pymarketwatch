# pymarketwatch
A Python libary to interact with the MarketWatch Stock Market Game
Based on code from https://github.com/kevindong/MarketWatch_API/


‼️ **NOTE: Unfortunately Marketwatch has decided to change their login system once again. There is a fork available at https://github.com/antoinebou12/marketwatch that is under active development.**

### Example
```
from pymarketwatch import MarketWatch

api = MarketWatch("email", "password", "game-name-from-url", True)
api.buy("AAPL", 100)

print(api.get_pending_orders())
print(api.get_positions())

```
